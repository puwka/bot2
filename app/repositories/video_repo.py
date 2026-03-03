import uuid

from postgrest.exceptions import APIError

from app.dto import VideoDto
from app.supabase_client import supabase
from app.supabase_async import run_sync


class VideoRepository:
    def __init__(self, client=supabase):
        self._client = client

    async def get_by_id(self, video_id: uuid.UUID) -> VideoDto | None:
        def _get():
            r = self._client.table("videos").select("*").eq("id", str(video_id)).execute()
            if r.data and len(r.data) > 0:
                return VideoDto.from_row(r.data[0])
            return None

        return await run_sync(_get)

    async def get_next_performer_sequence(self, user_id: uuid.UUID) -> int:
        """Следующий порядковый номер ролика для этого пользователя (счётчик привязан к user_id)."""
        def _next():
            try:
                r = (
                    self._client.table("videos")
                    .select("performer_sequence")
                    .eq("uploaded_by_user_id", str(user_id))
                    .order("performer_sequence", desc=True)
                    .limit(1)
                    .execute()
                )
                if r.data and len(r.data) > 0:
                    return int(r.data[0].get("performer_sequence") or 0) + 1
                return 1
            except APIError as e:
                if e.code == "42703":
                    from app.utils.content_code import user_id_to_code
                    code = user_id_to_code(user_id)
                    r = (
                        self._client.table("videos")
                        .select("performer_sequence")
                        .eq("performer_code", code)
                        .order("performer_sequence", desc=True)
                        .limit(1)
                        .execute()
                    )
                    if r.data and len(r.data) > 0:
                        return int(r.data[0].get("performer_sequence") or 0) + 1
                    return 1
                raise

        return await run_sync(_next)

    async def update_content_code(self, video_id: uuid.UUID, content_code: str) -> None:
        """Обновить content_code у видео (например, добавить сегмент дистрибьютора)."""
        def _update():
            try:
                self._client.table("videos").update({"content_code": content_code.strip()}).eq("id", str(video_id)).execute()
            except APIError as e:
                if e.code == "42703" and "content_code" in (e.message or ""):
                    pass
                else:
                    raise

        await run_sync(_update)

    async def create(
        self,
        url: str,
        platform: str | None = None,
        external_id: str | None = None,
        source_id: uuid.UUID | None = None,
        topic_id: uuid.UUID | None = None,
        description: str | None = None,
        title: str | None = None,
        drive_file_id: str | None = None,
        content_code: str | None = None,
        performer_code: int | None = None,
        performer_sequence: int | None = None,
        uploaded_by_user_id: uuid.UUID | None = None,
    ) -> VideoDto:
        """title: если в таблице videos колонка title NOT NULL — передайте строку (иначе подставится «—»)."""
        def _create():
            payload = {
                "url": url,
                "platform": platform,
                "external_id": external_id,
                "source_id": str(source_id) if source_id else None,
                "topic_id": str(topic_id) if topic_id else None,
                "description": description,
            }
            if title is not None:
                payload["title"] = title
            else:
                payload["title"] = "—"
            if drive_file_id is not None:
                payload["drive_file_id"] = drive_file_id
            if content_code is not None:
                payload["content_code"] = content_code.strip() or None
            if performer_code is not None:
                payload["performer_code"] = performer_code
            if performer_sequence is not None:
                payload["performer_sequence"] = performer_sequence
            if uploaded_by_user_id is not None:
                payload["uploaded_by_user_id"] = str(uploaded_by_user_id)
            try:
                r = self._client.table("videos").insert(payload).execute()
            except APIError as e:
                if e.code == "42703":
                    for key in ("content_code", "performer_code", "performer_sequence", "uploaded_by_user_id"):
                        payload.pop(key, None)
                    r = self._client.table("videos").insert(payload).execute()
                else:
                    raise
            return VideoDto.from_row(r.data[0])

        return await run_sync(_create)

    async def count_all(self) -> int:
        def _count():
            r = self._client.table("videos").select("id", count="exact").execute()
            return r.count or 0

        return await run_sync(_count)

    async def count_by_topic(self, topic_id: uuid.UUID) -> int:
        def _count():
            try:
                r = self._client.table("videos").select("id", count="exact").eq("topic_id", str(topic_id)).execute()
                return r.count or 0
            except APIError as e:
                if e.code == "42703" and "topic_id" in (e.message or ""):
                    return 0
                raise

        return await run_sync(_count)

    async def get_by_drive_file_id(self, drive_file_id: str) -> VideoDto | None:
        def _get():
            try:
                r = self._client.table("videos").select("*").eq("drive_file_id", drive_file_id).execute()
                if r.data and len(r.data) > 0:
                    return VideoDto.from_row(r.data[0])
                return None
            except APIError as e:
                if e.code == "42703" and "drive_file_id" in (e.message or ""):
                    return None
                raise

        return await run_sync(_get)

    async def get_by_url(self, url: str) -> VideoDto | None:
        def _get():
            try:
                r = self._client.table("videos").select("*").eq("url", url).execute()
                if r.data and len(r.data) > 0:
                    return VideoDto.from_row(r.data[0])
                return None
            except APIError as e:
                if e.code == "42703" and "url" in (e.message or ""):
                    return None
                raise

        return await run_sync(_get)
