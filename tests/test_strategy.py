"""무한매수법 전략 테스트"""

from decimal import Decimal

import pytest

from app.common.config import EmergencySellMode
from app.trading.strategy.infinite_buy import BuyOrder, InfiniteBuyStrategy, SellOrder


class TestInfiniteBuyStrategy:
    """InfiniteBuyStrategy 테스트"""

    @pytest.fixture
    def strategy(self):
        """기본 전략 인스턴스"""
        return InfiniteBuyStrategy(
            total_investment=Decimal("10000000"),  # 1000만원
            num_splits=40,
            profit_target=Decimal("1.10"),
            emergency_sell_mode=EmergencySellMode.QUARTER,
        )

    def test_investment_per_split(self, strategy):
        """1회분 매수 금액 계산"""
        assert strategy.investment_per_split == Decimal("250000")  # 25만원

    def test_first_buy_order(self, strategy):
        """첫 매수 주문 계산"""
        order = strategy.calculate_buy_order(
            current_price=Decimal("167750"),
            avg_price=None,
            splits_used=0,
        )

        assert order is not None
        assert order.price == Decimal("167750")
        assert order.quantity == 1  # 250000 / 167750 = 1.49 -> 1주
        assert order.is_half_amount is False

    def test_buy_below_avg_price(self, strategy):
        """현재가 < 평단가: 평단가로 1회분 매수"""
        order = strategy.calculate_buy_order(
            current_price=Decimal("150000"),  # 현재가
            avg_price=Decimal("160000"),  # 평단가
            splits_used=5,
        )

        assert order is not None
        assert order.price == Decimal("160000")  # 평단가로 주문
        assert order.quantity == 1  # 250000 / 160000 = 1.56 -> 1주
        assert order.is_half_amount is False

    def test_buy_above_avg_price(self, strategy):
        """현재가 >= 평단가: +10% 가격으로 0.5회분 매수"""
        # 더 낮은 가격으로 테스트 (0.5회분으로 1주 이상 살 수 있는 가격)
        order = strategy.calculate_buy_order(
            current_price=Decimal("100000"),  # 현재가 > 평단가
            avg_price=Decimal("95000"),  # 평단가
            splits_used=5,
        )

        assert order is not None
        assert order.price == Decimal("110000")  # 100000 * 1.10
        # 0.5회분 = 125000원, 110000원에 1.13주 -> 1주
        assert order.quantity == 1
        assert order.is_half_amount is True

    def test_buy_above_avg_price_zero_quantity(self, strategy):
        """현재가 >= 평단가: 가격이 너무 높아 0주가 되는 경우"""
        order = strategy.calculate_buy_order(
            current_price=Decimal("170000"),  # 높은 가격
            avg_price=Decimal("160000"),
            splits_used=5,
        )

        # 0.5회분 = 125000원, 187000원에 0.66주 -> 0주 -> None
        assert order is None

    def test_no_buy_when_splits_exhausted(self, strategy):
        """40회 소진 시 매수 없음"""
        order = strategy.calculate_buy_order(
            current_price=Decimal("167750"),
            avg_price=Decimal("160000"),
            splits_used=40,
        )

        assert order is None

    def test_calculate_sell_price(self, strategy):
        """매도 목표가 계산"""
        sell_price = strategy.calculate_sell_price(Decimal("160000"))
        assert sell_price == Decimal("176000")  # 160000 * 1.10

    def test_should_sell(self, strategy):
        """매도 조건 확인"""
        avg_price = Decimal("160000")

        # 목표 미달
        assert strategy.should_sell(Decimal("170000"), avg_price) is False

        # 목표 도달
        assert strategy.should_sell(Decimal("176000"), avg_price) is True

        # 목표 초과
        assert strategy.should_sell(Decimal("180000"), avg_price) is True

    def test_emergency_sell_quarter_mode(self, strategy):
        """쿼터 모드: 1/4 매도"""
        sell_order = strategy.calculate_emergency_sell(total_quantity=40)

        assert sell_order is not None
        assert sell_order.quantity == 10  # 40 / 4 = 10주
        assert sell_order.is_emergency is True

    def test_emergency_sell_wait_mode(self):
        """대기 모드: 매도 없음"""
        strategy = InfiniteBuyStrategy(
            total_investment=Decimal("10000000"),
            emergency_sell_mode=EmergencySellMode.WAIT,
        )

        sell_order = strategy.calculate_emergency_sell(total_quantity=40)
        assert sell_order is None

    def test_reset_with_proceeds(self, strategy):
        """사이클 리셋"""
        new_strategy = strategy.reset_with_proceeds(Decimal("11000000"))

        assert new_strategy.total_investment == Decimal("11000000")
        assert new_strategy.investment_per_split == Decimal("275000")
        assert new_strategy.num_splits == 40
        assert new_strategy.profit_target == Decimal("1.10")

    def test_validate_investment_sufficient(self, strategy):
        """자본금 검증 - 충분"""
        valid, message = strategy.validate_investment(Decimal("167750"))

        # 필요: 167750 * 40 = 6,710,000
        # 현재: 10,000,000
        assert valid is True
        assert message == "OK"

    def test_validate_investment_insufficient(self):
        """자본금 검증 - 부족"""
        strategy = InfiniteBuyStrategy(
            total_investment=Decimal("5000000"),  # 500만원
        )

        valid, message = strategy.validate_investment(Decimal("167750"))

        # 필요: 167750 * 40 = 6,710,000 > 5,000,000
        assert valid is False
        assert "최소 자본금 미달" in message
