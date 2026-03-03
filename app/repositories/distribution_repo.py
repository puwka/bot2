import logging
import random
import uuid
from datetime import datetime, timezone

from postgrest.exceptions import APIError

from app.dto import VideoDistributionDto, VideoDto
from app.supabase_client import supabase
from app.supabase_async import run_sync

logger = logging.getLogger(__name__)


class DistributionRepository:
    def __init__(self, client=supabase):
        self._client = client

    async def get_by_id(self, dist_id: uuid.UUID) -> VideoDistributionDto | None:
        def _get():
            r = (
                self._client.table("video_distribution")
                .select("*, video:videos(*), user:users(*)")
                .eq("id", str(dist_id))
                .execute()
            )
            if r.data and len(r.data) > 0:
                return VideoDistributionDto.from_row(r.data[0])
            return None

        return await run_sync(_get)

    async def find_available_video(self, user_id: uuid.UUID) -> VideoDto | None:
        # 1) topic_ids for user
        def _topics():
            r = self._client.table("user_categories").select("topic_id").eq("user_id", str(user_id)).execute()
            return [row["topic_id"] for row in (r.data or [])]

        topic_ids_raw = await run_sync(_topics)
        topic_ids = [str(t).strip() for t in topic_ids_raw if t is not None and str(t).strip()]
        if not topic_ids:
            logger.info("find_available_video: у пользователя %s нет категорий", user_id)
            return None

        # 2) видео, которые уже выданы этому пользователю (любая выдача — в таблице UNIQUE(video_id, user_id))
        def _distributed():
            r = self._client.table("video_distribution").select("video_id").eq("user_id", str(user_id)).execute()
            return [row["video_id"] for row in (r.data or [])]

        distributed_raw = await run_sync(_distributed)
        distributed_set = {str(x).lower().strip() for x in distributed_raw if x is not None}

        # 2b) видео, которые сейчас в активной задаче у любого пользователя (чтобы не выдавать одно и то же двум аккаунтам)
        def _active_video_ids():
            r = self._client.table("video_distribution").select("video_id").eq("completed", False).execute()
            return [row["video_id"] for row in (r.data or [])]

        active_raw = await run_sync(_active_video_ids)
        active_set = {str(x).lower().strip() for x in active_raw if x is not None}

        # 3) fetch videos in these topics (limit to avoid huge response)
        def _videos():
            cols = "id,url,platform,external_id,description,topic_id,source_id,drive_file_id,content_code"
            try:
                r = self._client.table("videos").select(cols).in_("topic_id", topic_ids).limit(200).execute()
                return [VideoDto.from_row(row) for row in (r.data or [])]
            except APIError as e:
                if e.code != "42703":
                    raise
                msg = e.message or ""
                if "topic_id" in msg:
                    return []
                if "content_code" in msg:
                    try:
                        r = self._client.table("videos").select("id,url,platform,external_id,description,topic_id,source_id,drive_file_id").in_("topic_id", topic_ids).limit(200).execute()
                        for row in (r.data or []):
                            row.setdefault("content_code", None)
                        return [VideoDto.from_row(row) for row in (r.data or [])]
                    except APIError:
                        pass
                if "drive_file_id" in msg:
                    r = self._client.table("videos").select("id,url,platform,external_id,description,topic_id,source_id").in_("topic_id", topic_ids).limit(200).execute()
                    for row in (r.data or []):
                        row.setdefault("drive_file_id", None)
                        row.setdefault("content_code", None)
                    return [VideoDto.from_row(row) for row in (r.data or [])]
                raise

        candidates = await run_sync(_videos)
        # Выдаём только видео с Яндекс.Диском; не выдаём этому пользователю уже выданные; не выдаём видео, уже в активной задаче у кого-то
        available = [
            v for v in candidates
            if getattr(v, "drive_file_id", None)
            and str(v.id).lower().strip() not in distributed_set
            and str(v.id).lower().strip() not in active_set
        ]
        logger.info(
            "find_available_video: user=%s topics=%s candidates=%s distributed=%s active_elsewhere=%s available=%s",
            user_id, len(topic_ids), len(candidates), len(distributed_set), len(active_set), len(available),
        )
        if not available:
            return None
        return random.choice(available)

    async def get_availability_stats(self, user_id: uuid.UUID) -> tuple[int, int] | None:
        """Возвращает (сколько видео в категориях пользователя, сколько уже выдано этому пользователю) или None если нет категорий."""
        def _topics():
            r = self._client.table("user_categories").select("topic_id").eq("user_id", str(user_id)).execute()
            return [row["topic_id"] for row in (r.data or [])]

        topic_ids_raw = await run_sync(_topics)
        topic_ids = [str(t).strip() for t in topic_ids_raw if t is not None and str(t).strip()]
        if not topic_ids:
            return None

        def _distributed():
            r = self._client.table("video_distribution").select("video_id").eq("user_id", str(user_id)).execute()
            return r.data or []

        def _videos():
            try:
                r = self._client.table("videos").select("id,drive_file_id").in_("topic_id", topic_ids).limit(200).execute()
                return [v for v in (r.data or []) if v.get("drive_file_id")]
            except APIError as e:
                if e.code == "42703" and "drive_file_id" in (e.message or ""):
                    r = self._client.table("videos").select("id").in_("topic_id", topic_ids).limit(200).execute()
                    return r.data or []
                raise

        distributed = await run_sync(_distributed)
        candidates = await run_sync(_videos)
        return len(candidates), len(distributed)

    async def create(self, video_id: uuid.UUID, user_id: uuid.UUID) -> VideoDistributionDto:
        def _create():
            r = self._client.table("video_distribution").insert({"video_id": str(video_id), "user_id": str(user_id)}).execute()
            return VideoDistributionDto.from_row(r.data[0])

        return await run_sync(_create)

    async def mark_completed(self, dist_id: uuid.UUID) -> VideoDistributionDto | None:
        dist = await self.get_by_id(dist_id)
        if not dist or dist.completed:
            return dist

        def _update():
            self._client.table("video_distribution").update({"completed": True, "completed_at": datetime.now(timezone.utc).isoformat()}).eq("id", str(dist_id)).execute()

        await run_sync(_update)
        return await self.get_by_id(dist_id)

    async def get_active_for_user(self, user_id: uuid.UUID) -> list[VideoDistributionDto]:
        def _list():
            r = (
                self._client.table("video_distribution")
                .select("*, video:videos(*), results:video_results(*)")
                .eq("user_id", str(user_id))
                .eq("completed", False)
                .order("assigned_at", desc=True)
                .execute()
            )
            return [VideoDistributionDto.from_row(row) for row in (r.data or [])]

        return await run_sync(_list)

    async def get_most_recent_for_user(self, user_id: uuid.UUID) -> VideoDistributionDto | None:
        """Последняя выдача пользователю (любая — чтобы снова показать ссылку на видео)."""
        def _one():
            r = (
                self._client.table("video_distribution")
                .select("*, video:videos(*), results:video_results(*)")
                .eq("user_id", str(user_id))
                .order("assigned_at", desc=True)
                .limit(1)
                .execute()
            )
            if r.data and len(r.data) > 0:
                return VideoDistributionDto.from_row(r.data[0])
            return None

        return await run_sync(_one)

    async def get_unfinished_all(self) -> list[VideoDistributionDto]:
        def _list():
            r = (
                self._client.table("video_distribution")
                .select("*, video:videos(*), user:users(*)")
                .eq("completed", False)
                .order("assigned_at", desc=True)
                .execute()
            )
            return [VideoDistributionDto.from_row(row) for row in (r.data or [])]

        return await run_sync(_list)

    async def count_completed(self) -> int:
        def _count():
            r = self._client.table("video_distribution").select("id", count="exact").eq("completed", True).execute()
            return r.count or 0

        return await run_sync(_count)

    async def count_total(self) -> int:
        def _count():
            r = self._client.table("video_distribution").select("id", count="exact").execute()
            return r.count or 0

        return await run_sync(_count)

    async def count_by_user(self, user_id: uuid.UUID) -> dict[str, int]:
        def _counts():
            r_total = self._client.table("video_distribution").select("id", count="exact").eq("user_id", str(user_id)).execute()
            r_done = self._client.table("video_distribution").select("id", count="exact").eq("user_id", str(user_id)).eq("completed", True).execute()
            return {"total": r_total.count or 0, "completed": r_done.count or 0}

        return await run_sync(_counts)

    async def reassign(self, dist_id: uuid.UUID, new_user_id: uuid.UUID) -> VideoDistributionDto | None:
        dist = await self.get_by_id(dist_id)
        if not dist:
            return None

        def _update():
            self._client.table("video_distribution").update({"user_id": str(new_user_id), "completed": False, "completed_at": None}).eq("id", str(dist_id)).execute()

        await run_sync(_update)
        return await self.get_by_id(dist_id)
