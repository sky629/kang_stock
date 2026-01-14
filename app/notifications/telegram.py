"""텔레그램 알림 서비스"""

import logging

from telegram import Bot

from app.common.config import settings
from app.common.utils import format_currency, format_percentage, get_kst_now
from app.trading.models.cycle_history import CycleHistory
from app.trading.models.order import Order
from app.trading.models.position import Position

logger = logging.getLogger(__name__)


class NotificationService:
    """텔레그램 알림 서비스"""

    def __init__(self):
        self.bot = Bot(token=settings.telegram_bot_token)
        self.chat_id = settings.telegram_chat_id

    async def _send(self, message: str) -> None:
        """메시지 전송"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"텔레그램 전송 실패: {e}")

    async def send_startup(self, position: Position) -> None:
        """시작 알림"""
        message = f"""
🚀 <b>무한매수법 시작</b>

📊 종목: {position.symbol_name} ({position.symbol})
💰 투자금: {format_currency(position.current_investment)}
📈 사이클: {position.cycle_count}회차
🎯 목표 수익률: {format_percentage(float(settings.profit_target) - 1)}

⏰ {get_kst_now().strftime('%Y-%m-%d %H:%M')}
"""
        await self._send(message.strip())

    async def send_buy_order(self, order: Order) -> None:
        """매수 주문 알림"""
        message = f"""
📥 <b>매수 주문</b>

종목: {order.symbol}
수량: {order.quantity}주
가격: {format_currency(order.price)}
분할: {order.split_number}/40회

⏰ {get_kst_now().strftime('%H:%M')}
"""
        await self._send(message.strip())

    async def send_sell_order(self, order: Order) -> None:
        """매도 주문 알림"""
        message = f"""
📤 <b>매도 주문 설정</b>

종목: {order.symbol}
수량: {order.quantity}주
목표가: {format_currency(order.price)}

⏰ {get_kst_now().strftime('%H:%M')}
"""
        await self._send(message.strip())

    async def send_execution(
        self,
        order_type: str,
        quantity: int,
        price: float,
        position: Position,
    ) -> None:
        """체결 알림"""
        emoji = "✅" if order_type == "매수" else "💵"
        message = f"""
{emoji} <b>{order_type} 체결</b>

수량: {quantity}주
가격: {format_currency(price)}
평단가: {format_currency(position.avg_price or 0)}
보유수량: {position.quantity}주
분할: {position.splits_used}/40회

⏰ {get_kst_now().strftime('%H:%M')}
"""
        await self._send(message.strip())

    async def send_emergency_sell(self, order: Order) -> None:
        """긴급 매도 알림"""
        message = f"""
⚠️ <b>긴급 매도 (쿼터 손절)</b>

40회 분할 소진으로 1/4 매도
수량: {order.quantity}주
가격: {format_currency(order.price)}

⏰ {get_kst_now().strftime('%H:%M')}
"""
        await self._send(message.strip())

    async def send_cycle_complete(self, history: CycleHistory) -> None:
        """사이클 완료 알림"""
        emoji = "🎉" if history.profit > 0 else "😢"
        message = f"""
{emoji} <b>사이클 {history.cycle_number} 완료!</b>

시작 투자금: {format_currency(history.start_investment)}
종료 금액: {format_currency(history.end_proceeds)}
수익금: {format_currency(history.profit)}
수익률: {format_percentage(float(history.profit_rate))}
총 매수 횟수: {history.total_trades}회

⏰ {get_kst_now().strftime('%Y-%m-%d %H:%M')}
"""
        await self._send(message.strip())

    async def send_error(self, error_message: str) -> None:
        """에러 알림"""
        message = f"""
🚨 <b>오류 발생</b>

{error_message}

⏰ {get_kst_now().strftime('%H:%M')}
"""
        await self._send(message.strip())

    async def send_daily_report(self, position: Position) -> None:
        """일일 리포트"""
        message = f"""
📋 <b>일일 리포트</b>

종목: {position.symbol_name}
보유수량: {position.quantity}주
평단가: {format_currency(position.avg_price or 0)}
투자금: {format_currency(position.current_investment)}
분할: {position.splits_used}/40회
사이클: {position.cycle_count}회차

⏰ {get_kst_now().strftime('%Y-%m-%d %H:%M')}
"""
        await self._send(message.strip())
