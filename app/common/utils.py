"""유틸리티 모듈"""

from datetime import datetime, time
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def get_kst_now() -> datetime:
    """현재 KST 시간 반환"""
    return datetime.now(KST)


def get_kst_today() -> datetime:
    """오늘 날짜 00:00:00 KST 반환"""
    now = get_kst_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def is_market_open() -> bool:
    """정규장 운영 시간인지 확인 (09:00 ~ 15:30)"""
    now = get_kst_now()
    market_open = time(9, 0)
    market_close = time(15, 30)
    return market_open <= now.time() <= market_close


def is_weekday() -> bool:
    """평일인지 확인 (월~금)"""
    return get_kst_now().weekday() < 5


def format_currency(amount: int | float) -> str:
    """금액을 원화 형식으로 포맷"""
    return f"{int(amount):,}원"


def format_percentage(value: float) -> str:
    """퍼센트 형식으로 포맷"""
    return f"{value * 100:.2f}%"
