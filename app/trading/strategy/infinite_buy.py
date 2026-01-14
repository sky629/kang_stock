"""라오어 무한매수법 전략 구현"""

from dataclasses import dataclass
from decimal import Decimal

from app.common.config import EmergencySellMode


@dataclass
class BuyOrder:
    """매수 주문 정보"""

    price: Decimal
    quantity: int
    is_half_amount: bool  # 0.5회분 매수 여부


@dataclass
class SellOrder:
    """매도 주문 정보"""

    price: Decimal
    quantity: int
    is_emergency: bool  # 긴급 매도 (40회 소진) 여부


class InfiniteBuyStrategy:
    """라오어 무한매수법 전략"""

    def __init__(
        self,
        total_investment: Decimal,
        num_splits: int = 40,
        profit_target: Decimal = Decimal("1.10"),
        emergency_sell_mode: EmergencySellMode = EmergencySellMode.QUARTER,
    ):
        self.total_investment = total_investment
        self.num_splits = num_splits
        self.profit_target = profit_target
        self.emergency_sell_mode = emergency_sell_mode
        self.investment_per_split = total_investment / Decimal(num_splits)

    def calculate_buy_order(
        self,
        current_price: Decimal,
        avg_price: Decimal | None,
        splits_used: int,
    ) -> BuyOrder | None:
        """
        매수 주문 계산 (시장가 매수)

        Args:
            current_price: 현재가
            avg_price: 평균 매입가 (사용 안 함)
            splits_used: 사용한 분할 횟수

        Returns:
            BuyOrder or None (매수 불필요/불가)
        """
        if splits_used >= self.num_splits:
            return None  # 40회 소진

        # 현재가 기준 1회분 수량 계산 → 시장가 매수
        quantity = int(self.investment_per_split / current_price)
        if quantity <= 0:
            return None

        return BuyOrder(
            price=current_price,  # 참고용 (시장가이므로 실제 체결가는 다를 수 있음)
            quantity=quantity,
            is_half_amount=False,
        )

    def calculate_sell_price(self, avg_price: Decimal) -> Decimal:
        """
        매도 목표가 계산

        Args:
            avg_price: 평균 매입가

        Returns:
            목표 매도가 (평단가 * profit_target)
        """
        return avg_price * self.profit_target

    def should_sell(self, current_price: Decimal, avg_price: Decimal) -> bool:
        """
        매도 조건 확인

        Args:
            current_price: 현재가
            avg_price: 평균 매입가

        Returns:
            True if 목표 수익률 도달
        """
        target_price = self.calculate_sell_price(avg_price)
        return current_price >= target_price

    def calculate_emergency_sell(self, total_quantity: int) -> SellOrder | None:
        """
        40회 소진 시 긴급 매도 계산 (쿼터 손절)

        Args:
            total_quantity: 총 보유 수량

        Returns:
            SellOrder (1/4 매도) or None (wait 모드일 경우)
        """
        if self.emergency_sell_mode == EmergencySellMode.WAIT:
            return None

        # quarter 모드: 1/4 매도
        sell_quantity = total_quantity // 4
        if sell_quantity <= 0:
            return None

        return SellOrder(
            price=Decimal("0"),  # 시장가로 매도
            quantity=sell_quantity,
            is_emergency=True,
        )

    def reset_with_proceeds(self, sell_proceeds: Decimal) -> "InfiniteBuyStrategy":
        """
        사이클 리셋: 매도 대금을 새 투자금으로 설정

        Args:
            sell_proceeds: 매도 대금

        Returns:
            새로운 전략 인스턴스
        """
        return InfiniteBuyStrategy(
            total_investment=sell_proceeds,
            num_splits=self.num_splits,
            profit_target=self.profit_target,
            emergency_sell_mode=self.emergency_sell_mode,
        )

    def validate_investment(self, current_price: Decimal) -> tuple[bool, str]:
        """
        최소 자본금 검증

        Args:
            current_price: 현재가

        Returns:
            (valid, message)
        """
        min_required = current_price * Decimal(self.num_splits)
        if self.total_investment < min_required:
            return False, (
                f"최소 자본금 미달: 필요 {min_required:,.0f}원, "
                f"현재 {self.total_investment:,.0f}원"
            )
        return True, "OK"
