"""Order 모델 - 주문 기록"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from sqlalchemy import Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid_utils import uuid7

from app.common.database import Base


class OrderType(str, Enum):
    """주문 유형"""

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    """주문 상태"""

    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class Order(Base):
    """주문 기록"""

    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    order_type: Mapped[OrderType] = mapped_column(String(10))
    price: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    quantity: Mapped[int]
    filled_quantity: Mapped[int] = mapped_column(default=0)
    filled_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(String(20), default=OrderStatus.PENDING)
    kiwoom_order_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 사이클 정보
    cycle_number: Mapped[int]
    split_number: Mapped[int]  # 몇 번째 분할 매수인지

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    filled_at: Mapped[datetime | None] = mapped_column(nullable=True)

    def mark_filled(self, filled_quantity: int, filled_price: Decimal) -> None:
        """체결 완료 처리"""
        self.filled_quantity = filled_quantity
        self.filled_price = filled_price
        self.filled_at = datetime.now()

        if filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        elif filled_quantity > 0:
            self.status = OrderStatus.PARTIAL
