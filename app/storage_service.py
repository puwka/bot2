"""Загрузка файлов в Supabase Storage."""
import asyncio
import uuid

from app.config import settings
from app.supabase_client import supabase
from app.supabase_async import run_sync

# Исключения при сетевых/SSL ошибках — повторяем загрузку
_RETRY_EXCEPTIONS = ("SSL", "Connect", "Timeout", "EOF", "protocol", "UNEXPECTED_EOF")
_MAX_UPLOAD_ATTEMPTS = 3
_RETRY_DELAY_SEC = 2


def _upload_sync(path: str, data: bytes, content_type: str) -> str:
    bucket = settings.STORAGE_BUCKET
    supabase.storage.from_(bucket).upload(path, data, {"content-type": content_type})
    return supabase.storage.from_(bucket).get_public_url(path)


def _should_retry(e: BaseException) -> bool:
    msg = str(e).lower()
    name = type(e).__name__.lower()
    return any(x.lower() in msg or x.lower() in name for x in _RETRY_EXCEPTIONS)


async def upload_video(data: bytes, content_type: str = "video/mp4") -> str:
    """Загружает видео в Storage и возвращает публичный URL. При сетевых/SSL ошибках — до 3 попыток."""
    ext = "mp4" if "mp4" in content_type else "webm" if "webm" in content_type else "mp4"
    path = f"uploads/{uuid.uuid4()}.{ext}"
    last_error: BaseException | None = None
    for attempt in range(_MAX_UPLOAD_ATTEMPTS):
        try:
            return await run_sync(lambda: _upload_sync(path, data, content_type))
        except Exception as e:
            last_error = e
            if attempt < _MAX_UPLOAD_ATTEMPTS - 1 and _should_retry(e):
                await asyncio.sleep(_RETRY_DELAY_SEC)
                continue
            raise
    assert last_error is not None
    raise last_error
