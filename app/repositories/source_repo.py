from app.dto import SourceDto
from app.supabase_client import supabase
from app.supabase_async import run_sync


def _source_placeholder_url(platform: str) -> str:
    """URL для источника, если в таблице sources колонка url NOT NULL (placeholder)."""
    return f"https://{platform}.local"


class SourceRepository:
    def __init__(self, client=supabase):
        self._client = client

    async def get_or_create(self, platform: str) -> SourceDto:
        def _get():
            r = self._client.table("sources").select("*").eq("platform", platform).execute()
            if r.data and len(r.data) > 0:
                return SourceDto.from_row(r.data[0])
            return None

        existing = await run_sync(_get)
        if existing:
            return existing

        def _create():
            payload = {"platform": platform}
            # Колонка url в sources может быть NOT NULL — передаём placeholder
            payload["url"] = _source_placeholder_url(platform)
            r = self._client.table("sources").insert(payload).execute()
            return SourceDto.from_row(r.data[0])

        return await run_sync(_create)
