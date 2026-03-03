from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.repositories.user_repo import UserRepository
from app.dto import UserRole


class RoleMiddleware(BaseMiddleware):
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
            user_repo = UserRepository()
            db_user = await user_repo.get_by_telegram_id(telegram_id)
            data["db_user"] = db_user
            data["user_role"] = db_user.role if db_user else None
        else:
            data["db_user"] = None
            data["user_role"] = None

        return await handler(event, data)
