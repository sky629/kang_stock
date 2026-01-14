"""설정 관리 모듈"""

from decimal import Decimal
from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class EmergencySellMode(str, Enum):
    """40회 소진 시 처리 모드"""

    QUARTER = "quarter"  # 1/4 매도 후 매수 계속
    WAIT = "wait"  # 목표 수익률 도달까지 대기


class Settings(BaseSettings):
    """애플리케이션 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # 키움 REST API
    kiwoom_app_key: str
    kiwoom_app_secret: str
    kiwoom_account_no: str
    kiwoom_is_mock: bool = True

    # Database
    database_url: str

    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str

    # Trading
    trading_symbol: str = "133690"
    total_investment: Decimal = Decimal("10000000")
    num_splits: int = 40
    profit_target: Decimal = Decimal("1.10")  # 1.10 = +10%
    emergency_sell_mode: EmergencySellMode = EmergencySellMode.QUARTER

    @property
    def investment_per_split(self) -> Decimal:
        """1회 분할 매수 금액"""
        return self.total_investment / self.num_splits

    @property
    def kiwoom_base_url(self) -> str:
        """키움 REST API 기본 URL"""
        if self.kiwoom_is_mock:
            return "https://mockapi.kiwoom.com"
        return "https://api.kiwoom.com"


settings = Settings()
