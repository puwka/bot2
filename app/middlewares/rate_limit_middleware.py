import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.config import settings


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self._cache: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_id: int | None = None
        if isinstance(event, Message) and event.from_user:
            telegram_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            telegram_id = event.from_user.id

        if telegram_id:
            now = time.monotonic()
            last = self._cache.get(telegram_id, 0.0)
            if now - last < settings.RATE_LIMIT_SECONDS:
                if isinstance(event, CallbackQuery):
                    await event.answer("⏳ Слишком быстро. Подождите немного.", show_alert=True)
                return None
            self._cache[telegram_id] = now

        return await handler(event, data)
