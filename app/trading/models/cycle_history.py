"""CycleHistory 모델 - 사이클 히스토리 (과거 기록)"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid_utils import uuid7

from app.common.database import Base


class CycleHistory(Base):
    """사이클 히스토리 (과거 기록)"""

    __tablename__ = "cycle_histories"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    cycle_number: Mapped[int]
    start_investment: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    end_proceeds: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    profit: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    profit_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    total_trades: Mapped[int]  # 해당 사이클의 총 매수 횟수
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime] = mapped_column(default=func.now())

    @classmethod
    def create_from_position(
        cls,
        symbol: str,
        cycle_number: int,
        start_investment: Decimal,
        end_proceeds: Decimal,
        total_trades: int,
        started_at: datetime,
    ) -> "CycleHistory":
        """Position 정보로부터 CycleHistory 생성"""
        profit = end_proceeds - start_investment
        profit_rate = profit / start_investment if start_investment > 0 else Decimal("0")

        return cls(
            symbol=symbol,
            cycle_number=cycle_number,
            start_investment=start_investment,
            end_proceeds=end_proceeds,
            profit=profit,
            profit_rate=profit_rate,
            total_trades=total_trades,
            started_at=started_at,
        )
