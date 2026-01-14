"""Mock API 클라이언트 테스트"""

from decimal import Decimal

import pytest

from app.trading.external_api.mock import MockStockAPI


class TestMockStockAPI:
    """MockStockAPI 테스트"""

    @pytest.fixture
    def api(self):
        """Mock API 인스턴스"""
        return MockStockAPI()

    @pytest.mark.asyncio
    async def test_get_price(self, api):
        """현재가 조회"""
        price_info = await api.get_price("133690")

        assert price_info.symbol == "133690"
        assert price_info.symbol_name == "TIGER미국나스닥100"
        assert price_info.current_price == Decimal("167750")

    @pytest.mark.asyncio
    async def test_get_balance(self, api):
        """잔고 조회"""
        balance = await api.get_balance()

        assert balance.total_deposit == Decimal("10000000")
        assert balance.available_amount == Decimal("10000000")

    @pytest.mark.asyncio
    async def test_buy_order(self, api):
        """매수 주문"""
        result = await api.buy("133690", 2, Decimal("167750"))

        assert result.order_type == "BUY"
        assert result.quantity == 2
        assert result.status == "FILLED"

        # 잔고 차감 확인
        balance = await api.get_balance()
        expected = Decimal("10000000") - (Decimal("167750") * 2)
        assert balance.available_amount == expected

        # 보유 종목 확인
        holdings = await api.get_holdings()
        assert len(holdings) == 1
        assert holdings[0].quantity == 2

    @pytest.mark.asyncio
    async def test_sell_order(self, api):
        """매도 주문"""
        # 먼저 매수
        await api.buy("133690", 5, Decimal("160000"))

        # 일부 매도
        result = await api.sell("133690", 2, Decimal("176000"))

        assert result.order_type == "SELL"
        assert result.quantity == 2
        assert result.status == "FILLED"

        # 보유 종목 확인 (3주 남음)
        holdings = await api.get_holdings()
        assert len(holdings) == 1
        assert holdings[0].quantity == 3

    @pytest.mark.asyncio
    async def test_sell_all(self, api):
        """전량 매도"""
        # 먼저 매수
        await api.buy("133690", 5, Decimal("160000"))

        # 전량 매도
        await api.sell("133690", 5, Decimal("176000"))

        # 보유 종목 없어야 함
        holdings = await api.get_holdings()
        assert len(holdings) == 0

    @pytest.mark.asyncio
    async def test_set_price(self, api):
        """테스트용 가격 설정"""
        api.set_price("133690", Decimal("200000"))

        price_info = await api.get_price("133690")
        assert price_info.current_price == Decimal("200000")
