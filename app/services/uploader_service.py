import uuid

from postgrest.exceptions import APIError

from app.config import settings
from app.repositories.video_repo import VideoRepository
from app.repositories.source_repo import SourceRepository
from app.repositories.topic_repo import TopicRepository
from app.repositories.action_log_repo import ActionLogRepository
from app.repositories.user_repo import UserRepository
from app.supabase_async import run_sync
from app.utils.platform_detector import detect_platform


class UploaderService:
    def __init__(self):
        self.video_repo = VideoRepository()
        self.source_repo = SourceRepository()
        self.topic_repo = TopicRepository()
        self.log_repo = ActionLogRepository()
        self.user_repo = UserRepository()

    async def upload_video_only(
        self,
        file_bytes: bytes,
        content_type: str,
        topic_id: uuid.UUID,
        file_name: str | None = None,
    ) -> tuple[str, str | None]:
        """Загружает файл в папку категории на Яндекс.Диске. Возвращает (url, file_path для БД). file_name — имя файла на диске (например код A3#0042.mp4)."""
        if not (settings.YANDEX_DISK_TOKEN or "").strip():
            raise ValueError(
                "Яндекс.Диск не настроен (YANDEX_DISK_TOKEN). Видео загружаются только на Диск."
            )
        root_path = (settings.YANDEX_DISK_ROOT_PATH or "").strip() or "/bot_videos"
        topic = await self.topic_repo.get_by_id(topic_id)
        if not topic:
            raise ValueError("Категория не найдена")
        folder_name = (topic.name or "").strip() or f"category_{str(topic_id)[:8]}"
        from app.yandex_disk_service import get_or_create_folder_in_parent, upload_file as disk_upload_file
        folder_path = await run_sync(
            lambda: get_or_create_folder_in_parent(root_path, folder_name)
        )
        await self.topic_repo.update_drive_folder_id(topic_id, folder_path)
        file_path, link = await run_sync(
            lambda: disk_upload_file(folder_path, file_bytes, content_type, file_name=file_name)
        )
        return link, file_path

    async def add_video_file(
        self,
        file_bytes: bytes,
        content_type: str,
        topic_id: uuid.UUID,
        telegram_id: int,
        description: str | None = None,
    ):
        """Загружает файл на Диск с именем = код контента (A{код из user_id}#{номер}) и создаёт запись в videos."""
        from app.utils.content_code import user_id_to_code
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("Пользователь не найден")
        performer_code = user_id_to_code(user.id)
        next_seq = await self.video_repo.get_next_performer_sequence(user.id)
        from app.utils.content_code import build_performer_code, filename_for_code
        content_code = build_performer_code(performer_code, next_seq)
        file_name = filename_for_code(content_code, "mp4")
        url, drive_file_id = await self.upload_video_only(file_bytes, content_type, topic_id, file_name=file_name)
        source = await self.source_repo.get_or_create("uploaded")
        video = await self.video_repo.create(
            url=url,
            platform="uploaded",
            external_id=url,
            source_id=source.id,
            topic_id=topic_id,
            description=description,
            title=content_code,
            drive_file_id=drive_file_id,
            content_code=content_code,
            performer_code=performer_code,
            performer_sequence=next_seq,
            uploaded_by_user_id=user.id,
        )
        await self.log_repo.log(
            action="upload_video",
            user_id=user.id if user else None,
            telegram_id=telegram_id,
            details={"video_id": str(video.id), "url": url, "platform": "uploaded", "topic_id": str(topic_id)},
        )
        return video

    async def add_video_from_storage_url(
        self,
        storage_url: str,
        topic_id: uuid.UUID,
        telegram_id: int,
        description: str | None = None,
        drive_file_id: str | None = None,
    ):
        """Создаёт запись в videos по уже загруженному URL (Drive или Supabase)."""
        source = await self.source_repo.get_or_create("uploaded")
        video = await self.video_repo.create(
            url=storage_url,
            platform="uploaded",
            external_id=storage_url,
            source_id=source.id,
            topic_id=topic_id,
            description=description,
            title=(description or "Загружено").strip() or "Загружено",
            drive_file_id=drive_file_id,
        )
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        await self.log_repo.log(
            action="upload_video",
            user_id=user.id if user else None,
            telegram_id=telegram_id,
            details={"video_id": str(video.id), "url": storage_url, "platform": "uploaded", "topic_id": str(topic_id)},
        )
        return video

    async def add_video_by_link(
        self,
        url: str,
        topic_id: uuid.UUID,
        telegram_id: int,
        description: str | None = None,
    ):
        """Добавляет видео по ссылке (TikTok, Reels и т.д.)."""
        existing = await self.video_repo.get_by_url(url)
        if existing:
            raise ValueError("Видео с таким URL уже существует")
        info = detect_platform(url)
        source = await self.source_repo.get_or_create(info.platform)
        try:
            video = await self.video_repo.create(
                url=url,
                platform=info.platform,
                external_id=info.external_id or url,
                source_id=source.id,
                topic_id=topic_id,
                description=description,
                title=(description or url or "—").strip() or "—",
            )
        except APIError as e:
            if e.code == "42703" and ("url" in (e.message or "") or "topic_id" in (e.message or "")):
                raise ValueError(
                    "В таблице videos нет колонки url или topic_id. "
                    "Выполните в Supabase SQL Editor файл migration_videos_topic_optional.sql"
                ) from e
            raise
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        await self.log_repo.log(
            action="upload_video",
            user_id=user.id if user else None,
            telegram_id=telegram_id,
            details={"video_id": str(video.id), "url": url, "platform": info.platform, "topic_id": str(topic_id)},
        )
        return video
