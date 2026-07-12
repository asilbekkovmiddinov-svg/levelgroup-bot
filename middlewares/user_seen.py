import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from services.api import register_internal_user, update_internal_user_seen


logger = logging.getLogger(__name__)

class UserSeenMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            try:
                seen_result = await update_internal_user_seen(user.id)
                if seen_result.get("status_code") == 404:
                    register_result = await register_internal_user(
                        telegram_id=user.id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name,
                    )
                    if register_result.get("success"):
                        seen_result = await update_internal_user_seen(user.id)
                    else:
                        self._log_failure("registration fallback", register_result)
                if not seen_result.get("success"):
                    self._log_failure("user seen", seen_result)
            except Exception:
                logger.warning("Internal user activity update is unavailable")

        return await handler(event, data)

    @staticmethod
    def _log_failure(operation: str, result: Dict[str, Any]) -> None:
        status_code = result.get("status_code")
        if status_code == 403:
            logger.warning("Internal API key is invalid or not configured")
            return
        logger.warning("Internal %s request failed (status=%s)", operation, status_code)
