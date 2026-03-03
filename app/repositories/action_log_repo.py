import uuid
from typing import Any

from app.dto import ActionLogDto
from app.supabase_client import supabase
from app.supabase_async import run_sync


class ActionLogRepository:
    def __init__(self, client=supabase):
        self._client = client

    async def log(
        self,
        action: str,
        user_id: uuid.UUID | None = None,
        telegram_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> ActionLogDto:
        def _log():
            payload = {"action": action, "user_id": str(user_id) if user_id else None, "telegram_id": telegram_id, "details": details}
            r = self._client.table("action_logs").insert(payload).execute()
            return ActionLogDto.from_row(r.data[0])

        return await run_sync(_log)

    async def get_recent(self, limit: int = 50) -> list[ActionLogDto]:
        def _list():
            r = self._client.table("action_logs").select("*").order("created_at", desc=True).limit(limit).execute()
            return [ActionLogDto.from_row(row) for row in (r.data or [])]

        return await run_sync(_list)
