import uuid

from app.dto import VideoResultDto
from app.supabase_client import supabase
from app.supabase_async import run_sync


class ResultRepository:
    def __init__(self, client=supabase):
        self._client = client

    async def url_exists(self, url: str) -> bool:
        def _check():
            r = self._client.table("video_results").select("id", count="exact").eq("url", url).execute()
            return (r.count or 0) > 0

        return await run_sync(_check)

    async def create(
        self,
        distribution_id: uuid.UUID,
        url: str,
        platform: str | None = None,
    ) -> VideoResultDto:
        def _create():
            payload = {
                "distribution_id": str(distribution_id),
                "url": url,
                "platform": platform,
            }
            r = self._client.table("video_results").insert(payload).execute()
            return VideoResultDto.from_row(r.data[0])

        return await run_sync(_create)

    async def count_all(self) -> int:
        def _count():
            r = self._client.table("video_results").select("id", count="exact").execute()
            return r.count or 0

        return await run_sync(_count)

    async def count_by_distribution(self, distribution_id: uuid.UUID) -> int:
        def _count():
            r = (
                self._client.table("video_results")
                .select("id", count="exact")
                .eq("distribution_id", str(distribution_id))
                .execute()
            )
            return r.count or 0

        return await run_sync(_count)
