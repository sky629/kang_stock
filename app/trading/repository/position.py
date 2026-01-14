"""Position Repository - 포지션 데이터 접근 계층"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.trading.models.position import Position


class PositionRepository:
    """Position 데이터 접근 레포지토리"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_symbol(self, symbol: str) -> Position | None:
        """종목코드로 포지션 조회"""
        result = await self.session.execute(
            select(Position).where(Position.symbol == symbol)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, position_id: UUID) -> Position | None:
        """ID로 포지션 조회"""
        result = await self.session.execute(
            select(Position).where(Position.id == position_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Position]:
        """전체 포지션 조회"""
        result = await self.session.execute(select(Position))
        return list(result.scalars().all())

    async def create(self, position: Position) -> Position:
        """포지션 생성"""
        self.session.add(position)
        await self.session.commit()
        await self.session.refresh(position)
        return position

    async def update(self, position: Position) -> Position:
        """포지션 업데이트"""
        await self.session.commit()
        await self.session.refresh(position)
        return position

    async def create_or_get(
        self,
        symbol: str,
        symbol_name: str,
        initial_investment: Decimal,
    ) -> Position:
        """포지션이 없으면 생성, 있으면 조회"""
        position = await self.get_by_symbol(symbol)

        if position is None:
            position = Position(
                symbol=symbol,
                symbol_name=symbol_name,
                quantity=0,
                avg_price=None,
                splits_used=0,
                cycle_count=1,
                current_investment=initial_investment,
                initial_investment=initial_investment,
            )
            position = await self.create(position)

        return position
