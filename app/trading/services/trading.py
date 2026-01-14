"""Trading 서비스 - 무한매수법 매매 실행"""

import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.common.utils import get_kst_now
from app.trading.external_api.base import StockAPIBase
from app.trading.models.cycle_history import CycleHistory
from app.trading.models.order import Order, OrderStatus, OrderType
from app.trading.models.position import Position
from app.trading.repository.position import PositionRepository
from app.notifications.decorators import (
    notify_on_buy,
    notify_on_sell,
    notify_on_emergency_sell,
)
from app.trading.strategy.infinite_buy import InfiniteBuyStrategy

logger = logging.getLogger(__name__)


class TradingService:
    """무한매수법 매매 서비스"""

    def __init__(
        self,
        session: AsyncSession,
        api: StockAPIBase,
        notifier: "NotificationService | None" = None,
    ):
        self.session = session
        self.api = api
        self.notifier = notifier
        self.position_repo = PositionRepository(session)

    async def _safe_notify(self, coro) -> None:
        """알림 전송 (실패해도 무시)"""
        if self.notifier is None:
            return
        try:
            await coro
        except Exception as e:
            logger.warning(f"알림 전송 실패 (무시됨): {e}")

    async def initialize_position(self) -> Position:
        """포지션 초기화 (첫 실행 시)"""
        symbol = settings.trading_symbol

        # 현재가 조회하여 종목명 가져오기
        price_info = await self.api.get_price(symbol)

        # 포지션 생성 또는 조회
        position = await self.position_repo.create_or_get(
            symbol=symbol,
            symbol_name=price_info.symbol_name,
            initial_investment=settings.total_investment,
        )

        # 최소 자본금 검증
        strategy = self._get_strategy(position)
        valid, message = strategy.validate_investment(price_info.current_price)

        if not valid:
            logger.error(message)
            await self._safe_notify(self.notifier.send_error(message))
            raise ValueError(message)

        return position

    def _get_strategy(self, position: Position) -> InfiniteBuyStrategy:
        """현재 포지션 기반 전략 인스턴스 생성"""
        return InfiniteBuyStrategy(
            total_investment=position.current_investment,
            num_splits=settings.num_splits,
            profit_target=settings.profit_target,
            emergency_sell_mode=settings.emergency_sell_mode,
        )

    @notify_on_sell
    async def execute_daily_sell_order(self) -> Order | None:
        """매도 주문 설정 (매일 09:00)"""
        symbol = settings.trading_symbol
        position = await self.position_repo.get_by_symbol(symbol)

        if position is None or position.quantity == 0 or position.avg_price is None:
            logger.info("매도할 포지션 없음")
            return None

        strategy = self._get_strategy(position)
        target_price = strategy.calculate_sell_price(position.avg_price)

        # 매도 주문
        result = await self.api.sell(symbol, position.quantity, target_price)

        order = Order(
            symbol=symbol,
            order_type=OrderType.SELL,
            price=target_price,
            quantity=position.quantity,
            cycle_number=position.cycle_count,
            split_number=0,
            kiwoom_order_id=result.order_id,
        )
        self.session.add(order)
        await self.session.commit()

        logger.info(f"매도 주문 설정: {position.quantity}주 @ {target_price:,}원")
        return order

    @notify_on_buy
    async def execute_daily_buy_order(self) -> Order | None:
        """매수 주문 실행 (매일 14:30)"""
        symbol = settings.trading_symbol
        position = await self.position_repo.get_by_symbol(symbol)

        if position is None:
            position = await self.initialize_position()

        strategy = self._get_strategy(position)

        # 40회 소진 체크
        if strategy.should_emergency_sell and position.splits_used >= settings.num_splits:
            return await self._execute_emergency_sell(position, strategy)

        # 현재가 조회
        price_info = await self.api.get_price(symbol)
        current_price = price_info.current_price

        # 목표 수익률 도달 체크
        if position.avg_price and strategy.should_sell(current_price, position.avg_price):
            logger.info("목표 수익률 도달 - 매도 대기 중")
            return None

        # 매수 주문 계산
        buy_order = strategy.calculate_buy_order(
            current_price=current_price,
            avg_price=position.avg_price,
            splits_used=position.splits_used,
        )

        if buy_order is None:
            logger.info("매수 조건 미충족")
            return None

        # 매수 주문 실행
        result = await self.api.buy(symbol, buy_order.quantity, buy_order.price)

        order = Order(
            symbol=symbol,
            order_type=OrderType.BUY,
            price=buy_order.price,
            quantity=buy_order.quantity,
            cycle_number=position.cycle_count,
            split_number=position.splits_used + 1,
            kiwoom_order_id=result.order_id,
        )
        self.session.add(order)
        await self.session.commit()

        logger.info(
            f"매수 주문: {buy_order.quantity}주 @ {buy_order.price:,}원 "
            f"({'0.5회분' if buy_order.is_half_amount else '1회분'})"
        )
        return order

    @notify_on_emergency_sell
    async def _execute_emergency_sell(
        self, position: Position, strategy: InfiniteBuyStrategy
    ) -> Order | None:
        """긴급 매도 (40회 소진 시 1/4 매도)"""
        sell_order = strategy.calculate_emergency_sell(position.quantity)

        if sell_order is None:
            logger.info("대기 모드 - 긴급 매도 없음")
            return None

        symbol = settings.trading_symbol

        price_info = await self.api.get_price(symbol)
        result = await self.api.sell(symbol, sell_order.quantity, price_info.current_price)

        order = Order(
            symbol=symbol,
            order_type=OrderType.SELL,
            price=price_info.current_price,
            quantity=sell_order.quantity,
            cycle_number=position.cycle_count,
            split_number=0,
            kiwoom_order_id=result.order_id,
        )
        self.session.add(order)
        await self.session.commit()

        logger.warning(f"긴급 매도 (쿠터 손절): {sell_order.quantity}주")
        return order

    async def check_order_execution(self) -> None:
        """체결 확인 및 포지션 업데이트 (매일 15:40)"""
        symbol = settings.trading_symbol
        position = await self.position_repo.get_by_symbol(symbol)

        if position is None:
            return

        # API에서 실제 보유 종목 조회
        holdings = await self.api.get_holdings()
        holding = next((h for h in holdings if h.symbol == symbol), None)

        if holding:
            # 매수 체결 확인
            if holding.quantity > position.quantity:
                # 새로 체결된 수량
                bought_qty = holding.quantity - position.quantity
                position.update_after_buy(bought_qty, holding.avg_price)
                await self.position_repo.update(position)

                logger.info(f"매수 체결: {bought_qty}주, 새 평단가: {position.avg_price:,}원")

                await self._safe_notify(self.notifier.send_execution(
                    "매수", bought_qty, holding.avg_price, position
                ))

            # 전량 매도 확인
            elif holding.quantity == 0 and position.quantity > 0:
                await self._complete_cycle(position)

        elif position.quantity > 0:
            # 보유 종목이 없으면 전량 매도됨
            await self._complete_cycle(position)

    async def _complete_cycle(self, position: Position) -> None:
        """사이클 완료 처리"""
        # 잔고 조회하여 매도 대금 확인
        balance = await self.api.get_balance()

        # CycleHistory 기록
        history = CycleHistory.create_from_position(
            symbol=position.symbol,
            cycle_number=position.cycle_count,
            start_investment=position.initial_investment
            if position.cycle_count == 1
            else position.current_investment,
            end_proceeds=balance.available_amount,  # 대략적인 값
            total_trades=position.splits_used,
            started_at=position.created_at,
        )
        self.session.add(history)

        # 포지션 리셋
        position.reset_for_new_cycle(balance.available_amount)
        await self.position_repo.update(position)

        logger.info(
            f"사이클 {position.cycle_count - 1} 완료! "
            f"수익률: {history.profit_rate * 100:.2f}%"
        )

        await self._safe_notify(self.notifier.send_cycle_complete(history))


# 타입 힌트를 위한 임포트 (순환 참조 방지)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.notifications.telegram import NotificationService
