"""Mock API 클라이언트 - 테스트용"""

from decimal import Decimal

from app.trading.external_api.base import (
    BalanceInfo,
    HoldingInfo,
    OrderResult,
    PriceInfo,
    StockAPIBase,
)


class MockStockAPI(StockAPIBase):
    """테스트용 Mock API 클라이언트"""

    def __init__(self):
        self._holdings: dict[str, HoldingInfo] = {}
        self._orders: list[OrderResult] = []
        self._balance = Decimal("10000000")  # 1000만원
        self._order_counter = 0

        # Mock 가격 데이터
        self._prices: dict[str, Decimal] = {
            "133690": Decimal("167750"),  # TIGER 미국나스닥100
        }

    async def get_token(self) -> str:
        """Mock 토큰 발급"""
        return "mock_token_12345"

    async def get_price(self, symbol: str) -> PriceInfo:
        """Mock 현재가 조회"""
        price = self._prices.get(symbol, Decimal("100000"))

        return PriceInfo(
            symbol=symbol,
            symbol_name=self._get_symbol_name(symbol),
            current_price=price,
            prev_close=price * Decimal("0.99"),
            change_rate=Decimal("1.01"),
        )

    async def get_balance(self) -> BalanceInfo:
        """Mock 잔고 조회"""
        return BalanceInfo(
            total_deposit=self._balance,
            available_amount=self._balance,
        )

    async def get_holdings(self) -> list[HoldingInfo]:
        """Mock 보유 종목 조회"""
        return list(self._holdings.values())

    async def buy(self, symbol: str, quantity: int, price: Decimal) -> OrderResult:
        """Mock 매수 주문"""
        self._order_counter += 1
        order_id = f"MOCK_BUY_{self._order_counter}"

        # 잔고 차감
        total_amount = price * Decimal(quantity)
        self._balance -= total_amount

        # 보유 종목 업데이트
        if symbol in self._holdings:
            holding = self._holdings[symbol]
            # 평단가 재계산
            total_cost = holding.avg_price * Decimal(holding.quantity) + total_amount
            new_quantity = holding.quantity + quantity
            self._holdings[symbol] = HoldingInfo(
                symbol=symbol,
                symbol_name=holding.symbol_name,
                quantity=new_quantity,
                avg_price=total_cost / Decimal(new_quantity),
                current_price=price,
                profit_rate=Decimal("0"),
            )
        else:
            self._holdings[symbol] = HoldingInfo(
                symbol=symbol,
                symbol_name=self._get_symbol_name(symbol),
                quantity=quantity,
                avg_price=price,
                current_price=price,
                profit_rate=Decimal("0"),
            )

        return OrderResult(
            order_id=order_id,
            symbol=symbol,
            order_type="BUY",
            quantity=quantity,
            price=price,
            status="FILLED",  # Mock은 즉시 체결
        )

    async def sell(self, symbol: str, quantity: int, price: Decimal) -> OrderResult:
        """Mock 매도 주문"""
        self._order_counter += 1
        order_id = f"MOCK_SELL_{self._order_counter}"

        # 잔고 추가
        total_amount = price * Decimal(quantity)
        self._balance += total_amount

        # 보유 종목 업데이트
        if symbol in self._holdings:
            holding = self._holdings[symbol]
            new_quantity = holding.quantity - quantity
            if new_quantity <= 0:
                del self._holdings[symbol]
            else:
                self._holdings[symbol] = HoldingInfo(
                    symbol=symbol,
                    symbol_name=holding.symbol_name,
                    quantity=new_quantity,
                    avg_price=holding.avg_price,
                    current_price=price,
                    profit_rate=Decimal("0"),
                )

        return OrderResult(
            order_id=order_id,
            symbol=symbol,
            order_type="SELL",
            quantity=quantity,
            price=price,
            status="FILLED",
        )

    async def get_pending_orders(self) -> list[OrderResult]:
        """Mock 미체결 주문 조회"""
        return [o for o in self._orders if o.status == "PENDING"]

    async def cancel_order(self, order_id: str, symbol: str = "", quantity: int = 0) -> bool:
        """Mock 주문 취소"""
        for order in self._orders:
            if order.order_id == order_id:
                order.status = "CANCELLED"
                return True
        return False

    def set_price(self, symbol: str, price: Decimal) -> None:
        """테스트용: 가격 설정"""
        self._prices[symbol] = price

    def set_balance(self, balance: Decimal) -> None:
        """테스트용: 잔고 설정"""
        self._balance = balance

    def _get_symbol_name(self, symbol: str) -> str:
        """종목명 반환"""
        names = {
            "133690": "TIGER미국나스닥100",
            "379800": "KODEX미국S&P500TR",
        }
        return names.get(symbol, f"종목{symbol}")
