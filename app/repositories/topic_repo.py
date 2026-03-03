import uuid

from app.config import settings
from app.dto import TopicDto
from app.supabase_client import supabase
from app.supabase_async import run_sync


def _topic_col() -> str:
    return settings.TOPIC_NAME_COLUMN


class TopicRepository:
    def __init__(self, client=supabase):
        self._client = client

    async def get_by_id(self, topic_id: uuid.UUID) -> TopicDto | None:
        def _get():
            r = self._client.table("topics").select("*").eq("id", str(topic_id)).execute()
            if r.data and len(r.data) > 0:
                return TopicDto.from_row(r.data[0])
            return None

        return await run_sync(_get)

    async def get_by_name(self, name: str) -> TopicDto | None:
        def _get():
            col = _topic_col()
            r = self._client.table("topics").select("*").eq(col, name).execute()
            if r.data and len(r.data) > 0:
                return TopicDto.from_row(r.data[0])
            return None

        return await run_sync(_get)

    async def create(self, name: str) -> TopicDto:
        def _create():
            col = _topic_col()
            r = self._client.table("topics").insert({col: name}).execute()
            return TopicDto.from_row(r.data[0])

        return await run_sync(_create)

    async def update_drive_folder_id(self, topic_id: uuid.UUID, drive_folder_id: str) -> None:
        def _update():
            self._client.table("topics").update({"drive_folder_id": drive_folder_id}).eq("id", str(topic_id)).execute()

        await run_sync(_update)

    async def list_all(self) -> list[TopicDto]:
        def _list():
            col = _topic_col()
            r = self._client.table("topics").select("*").order(col).execute()
            return [TopicDto.from_row(row) for row in (r.data or [])]

        return await run_sync(_list)
