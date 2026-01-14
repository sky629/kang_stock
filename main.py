"""라오어 무한매수법 자동매매 시스템 - 메인 진입점"""

import asyncio
import logging
import signal
import sys

from app.common.config import settings
from app.common.database import async_session
from app.common.utils import get_kst_now
from app.notifications.telegram import NotificationService
from app.trading.external_api.kiwoom import KiwoomRestAPI
from app.trading.services.scheduler import create_scheduler
from app.trading.services.trading import TradingService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def startup() -> None:
    """시작 시 초기화"""
    logger.info("=" * 50)
    logger.info("🚀 라오어 무한매수법 자동매매 시스템 시작")
    logger.info("=" * 50)
    logger.info(f"시작 시간: {get_kst_now()}")
    logger.info(f"대상 종목: {settings.trading_symbol}")
    logger.info(f"투자금: {settings.total_investment:,}원")
    logger.info(f"분할 횟수: {settings.num_splits}회")
    logger.info(f"목표 수익률: {(float(settings.profit_target) - 1) * 100:.1f}%")
    logger.info(f"긴급매도 모드: {settings.emergency_sell_mode}")
    logger.info(f"모의투자 모드: {settings.kiwoom_is_mock}")
    logger.info("=" * 50)

    # 포지션 초기화
    async with async_session() as session:
        api = KiwoomRestAPI()
        notifier = NotificationService()
        service = TradingService(session, api, notifier)

        try:
            position = await service.initialize_position()
            await notifier.send_startup(position)
            logger.info(f"포지션 초기화 완료: {position.symbol_name}")
        except Exception as e:
            logger.error(f"포지션 초기화 실패: {e}")
            await notifier.send_error(f"시작 실패: {e}")
            raise


async def main() -> None:
    """메인 함수"""
    # 초기화
    await startup()

    # 스케줄러 생성 및 시작
    scheduler = create_scheduler()
    scheduler.start()

    # 종료 시그널 핸들러
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("종료 시그널 수신")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    logger.info("스케줄러 실행 중... (Ctrl+C로 종료)")

    # 무한 대기
    try:
        await stop_event.wait()
    finally:
        scheduler.shutdown()
        logger.info("스케줄러 종료됨")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("프로그램 종료")
    except Exception as e:
        logger.error(f"예기치 않은 오류: {e}")
        sys.exit(1)
