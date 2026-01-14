"""스케줄러 서비스 - APScheduler 기반 작업 스케줄링"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.common.database import async_session
from app.common.utils import is_weekday
from app.notifications.telegram import NotificationService
from app.trading.external_api.kiwoom import KiwoomRestAPI
from app.trading.services.trading import TradingService

logger = logging.getLogger(__name__)

# 실행 중 플래그 (중복 실행 방지)
_is_running = False


async def _get_trading_service() -> TradingService:
    """TradingService 인스턴스 생성"""
    session = async_session()
    api = KiwoomRestAPI()
    notifier = NotificationService()
    return TradingService(session, api, notifier)


async def job_set_sell_order():
    """매도 주문 설정 (09:00)"""
    global _is_running
    if _is_running:
        logger.warning("이전 작업 실행 중 - 스킵")
        return

    if not is_weekday():
        logger.info("주말 - 스킵")
        return

    _is_running = True
    try:
        logger.info("=== 매도 주문 설정 시작 ===")
        service = await _get_trading_service()
        await service.execute_daily_sell_order()
    except Exception as e:
        logger.error(f"매도 주문 설정 실패: {e}")
    finally:
        _is_running = False


async def job_execute_buy_order():
    """매수 주문 실행 (14:30)"""
    global _is_running
    if _is_running:
        logger.warning("이전 작업 실행 중 - 스킵")
        return

    if not is_weekday():
        logger.info("주말 - 스킵")
        return

    _is_running = True
    try:
        logger.info("=== 매수 주문 실행 시작 ===")
        service = await _get_trading_service()
        await service.execute_daily_buy_order()
    except Exception as e:
        logger.error(f"매수 주문 실행 실패: {e}")
    finally:
        _is_running = False


async def job_check_execution():
    """체결 확인 (15:40)"""
    global _is_running
    if _is_running:
        logger.warning("이전 작업 실행 중 - 스킵")
        return

    if not is_weekday():
        logger.info("주말 - 스킵")
        return

    _is_running = True
    try:
        logger.info("=== 체결 확인 시작 ===")
        service = await _get_trading_service()
        await service.check_order_execution()
    except Exception as e:
        logger.error(f"체결 확인 실패: {e}")
    finally:
        _is_running = False


def create_scheduler() -> AsyncIOScheduler:
    """스케줄러 생성 및 작업 등록"""
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

    # 매도 주문 설정 (평일 09:00)
    scheduler.add_job(
        job_set_sell_order,
        CronTrigger(hour=9, minute=0, day_of_week="mon-fri"),
        id="set_sell_order",
        name="매도 주문 설정",
        replace_existing=True,
    )

    # 매수 주문 실행 (평일 14:30)
    scheduler.add_job(
        job_execute_buy_order,
        CronTrigger(hour=14, minute=30, day_of_week="mon-fri"),
        id="execute_buy_order",
        name="매수 주문 실행",
        replace_existing=True,
    )

    # 체결 확인 (평일 15:40)
    scheduler.add_job(
        job_check_execution,
        CronTrigger(hour=15, minute=40, day_of_week="mon-fri"),
        id="check_execution",
        name="체결 확인",
        replace_existing=True,
    )

    logger.info("스케줄러 작업 등록 완료")
    logger.info("  - 09:00: 매도 주문 설정")
    logger.info("  - 14:30: 매수 주문 실행")
    logger.info("  - 15:40: 체결 확인")

    return scheduler
