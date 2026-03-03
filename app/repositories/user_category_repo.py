import uuid

from app.dto import UserCategoryDto
from app.supabase_client import supabase
from app.supabase_async import run_sync


class UserCategoryRepository:
    def __init__(self, client=supabase):
        self._client = client

    async def assign(self, user_id: uuid.UUID, topic_id: uuid.UUID) -> UserCategoryDto:
        def _get():
            r = (
                self._client.table("user_categories")
                .select("*")
                .eq("user_id", str(user_id))
                .eq("topic_id", str(topic_id))
                .execute()
            )
            if r.data and len(r.data) > 0:
                return UserCategoryDto.from_row(r.data[0])
            return None

        existing = await run_sync(_get)
        if existing:
            return existing

        def _create():
            r = self._client.table("user_categories").insert({"user_id": str(user_id), "topic_id": str(topic_id)}).execute()
            return UserCategoryDto.from_row(r.data[0])

        return await run_sync(_create)

    async def unassign(self, user_id: uuid.UUID, topic_id: uuid.UUID) -> None:
        def _delete():
            self._client.table("user_categories").delete().eq("user_id", str(user_id)).eq("topic_id", str(topic_id)).execute()

        await run_sync(_delete)

    async def get_user_topics(self, user_id: uuid.UUID) -> list[UserCategoryDto]:
        def _list():
            r = self._client.table("user_categories").select("*, topic:topics(*)").eq("user_id", str(user_id)).execute()
            return [UserCategoryDto.from_row(row) for row in (r.data or [])]

        return await run_sync(_list)
