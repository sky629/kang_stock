"""Position 모델 - 종목별 포지션 (현재 사이클)"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid_utils import uuid7

from app.common.database import Base


class Position(Base):
    """종목별 포지션 (현재 사이클)"""

    __tablename__ = "positions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    symbol: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    symbol_name: Mapped[str] = mapped_column(String(100))
    quantity: Mapped[int] = mapped_column(default=0)
    avg_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    splits_used: Mapped[int] = mapped_column(default=0)

    # 사이클 관리
    cycle_count: Mapped[int] = mapped_column(default=1)  # 현재 사이클 번호
    current_investment: Mapped[Decimal] = mapped_column(Numeric(15, 2))  # 현재 사이클 투자금
    initial_investment: Mapped[Decimal] = mapped_column(Numeric(15, 2))  # 최초 투자금 (기록용)

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    @property
    def total_cost(self) -> Decimal:
        """총 매입금액 (계산)"""
        if self.avg_price is None:
            return Decimal("0")
        return Decimal(self.quantity) * self.avg_price

    @property
    def investment_per_split(self) -> Decimal:
        """1회 분할 매수 금액"""
        return self.current_investment / 40  # TODO: num_splits from config

    def reset_for_new_cycle(self, sell_proceeds: Decimal) -> None:
        """새 사이클을 위한 포지션 리셋"""
        self.quantity = 0
        self.avg_price = None
        self.splits_used = 0
        self.cycle_count += 1
        self.current_investment = sell_proceeds

    def update_after_buy(self, buy_quantity: int, buy_price: Decimal) -> None:
        """매수 체결 후 포지션 업데이트"""
        if self.avg_price is None:
            # 첫 매수
            self.avg_price = buy_price
            self.quantity = buy_quantity
        else:
            # 평단가 재계산
            total_cost = self.total_cost + (Decimal(buy_quantity) * buy_price)
            self.quantity += buy_quantity
            self.avg_price = total_cost / Decimal(self.quantity)

        self.splits_used += 1
