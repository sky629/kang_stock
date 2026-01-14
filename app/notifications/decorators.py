"""알림 데코레이터"""

import functools
import logging
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def notify_on_buy(func: Callable[..., T]) -> Callable[..., T]:
    """매수 주문 성공 시 알림"""
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            result = await func(self, *args, **kwargs)
            if result and self.notifier:
                try:
                    await self.notifier.send_buy_order(result)
                except Exception as e:
                    logger.warning(f"매수 알림 실패 (무시됨): {e}")
            return result
        except Exception as e:
            if self.notifier:
                try:
                    await self.notifier.send_error(f"매수 주문 실패: {e}")
                except Exception:
                    pass
            raise
    return wrapper


def notify_on_sell(func: Callable[..., T]) -> Callable[..., T]:
    """매도 주문 성공 시 알림"""
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            result = await func(self, *args, **kwargs)
            if result and self.notifier:
                try:
                    await self.notifier.send_sell_order(result)
                except Exception as e:
                    logger.warning(f"매도 알림 실패 (무시됨): {e}")
            return result
        except Exception as e:
            if self.notifier:
                try:
                    await self.notifier.send_error(f"매도 주문 실패: {e}")
                except Exception:
                    pass
            raise
    return wrapper


def notify_on_emergency_sell(func: Callable[..., T]) -> Callable[..., T]:
    """긴급 매도 성공 시 알림"""
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            result = await func(self, *args, **kwargs)
            if result and self.notifier:
                try:
                    await self.notifier.send_emergency_sell(result)
                except Exception as e:
                    logger.warning(f"긴급매도 알림 실패 (무시됨): {e}")
            return result
        except Exception as e:
            if self.notifier:
                try:
                    await self.notifier.send_error(f"긴급 매도 실패: {e}")
                except Exception:
                    pass
            raise
    return wrapper
