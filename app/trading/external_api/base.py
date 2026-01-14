"""증권사 API 추상 인터페이스"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PriceInfo:
    """현재가 정보"""

    symbol: str
    symbol_name: str
    current_price: Decimal
    prev_close: Decimal
    change_rate: Decimal


@dataclass
class OrderResult:
    """주문 결과"""

    order_id: str
    symbol: str
    order_type: str  # "BUY" | "SELL"
    quantity: int
    price: Decimal
    status: str  # "PENDING" | "FILLED" | "CANCELLED"


@dataclass
class BalanceInfo:
    """계좌 잔고 정보"""

    total_deposit: Decimal  # 예수금 총액
    available_amount: Decimal  # 주문 가능 금액


@dataclass
class HoldingInfo:
    """보유 종목 정보"""

    symbol: str
    symbol_name: str
    quantity: int
    avg_price: Decimal
    current_price: Decimal
    profit_rate: Decimal


class StockAPIBase(ABC):
    """증권사 API 추상 인터페이스 - API 교체 시 이 인터페이스만 구현"""

    @abstractmethod
    async def get_token(self) -> str:
        """인증 토큰 발급"""
        pass

    @abstractmethod
    async def get_price(self, symbol: str) -> PriceInfo:
        """현재가 조회"""
        pass

    @abstractmethod
    async def get_balance(self) -> BalanceInfo:
        """계좌 잔고 조회"""
        pass

    @abstractmethod
    async def get_holdings(self) -> list[HoldingInfo]:
        """보유 종목 조회"""
        pass

    @abstractmethod
    async def buy(self, symbol: str, quantity: int, price: Decimal) -> OrderResult:
        """지정가 매수 주문"""
        pass

    @abstractmethod
    async def sell(self, symbol: str, quantity: int, price: Decimal) -> OrderResult:
        """지정가 매도 주문"""
        pass

    @abstractmethod
    async def get_pending_orders(self) -> list[OrderResult]:
        """미체결 주문 조회"""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str = "", quantity: int = 0) -> bool:
        """주문 취소
        
        Args:
            order_id: 원주문번호
            symbol: 종목코드
            quantity: 취소수량 (0 = 전량 취소)
        """
        pass
