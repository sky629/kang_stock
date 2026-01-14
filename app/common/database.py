"""데이터베이스 연결 모듈"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.common.config import settings


class Base(DeclarativeBase):
    """모든 모델의 베이스 클래스"""

    pass


engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """데이터베이스 세션 의존성"""
    async with async_session() as session:
        yield session
