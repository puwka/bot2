import logging
import uuid
from dataclasses import replace

from app.dto import VideoDistributionDto
from app.repositories.distribution_repo import DistributionRepository
from app.repositories.result_repo import ResultRepository
from app.repositories.user_repo import UserRepository
from app.repositories.video_repo import VideoRepository
from app.repositories.topic_repo import TopicRepository
from app.repositories.source_repo import SourceRepository
from app.repositories.action_log_repo import ActionLogRepository
from app.supabase_async import run_sync
from app.utils.platform_detector import detect_platform

logger = logging.getLogger(__name__)


class DistributorService:
    def __init__(self):
        self.dist_repo = DistributionRepository()
        self.result_repo = ResultRepository()
        self.user_repo = UserRepository()
        self.video_repo = VideoRepository()
        self.topic_repo = TopicRepository()
        self.source_repo = SourceRepository()
        self.log_repo = ActionLogRepository()

    async def _ensure_video(self, dist: VideoDistributionDto) -> VideoDistributionDto:
        """Подгружает полные данные видео из БД (включая drive_file_id для ссылки на Drive)."""
        video = await self.video_repo.get_by_id(dist.video_id)
        if video is None:
            return dist
        return replace(dist, video=video)

    async def _sync_drive_folders_to_db(self, user_id: uuid.UUID) -> None:
        """Сканирует папки категорий пользователя на Drive и создаёт записи в БД для видео, которых ещё нет."""
        def _topic_ids():
            r = self.dist_repo._client.table("user_categories").select("topic_id").eq("user_id", str(user_id)).execute()
            return [row["topic_id"] for row in (r.data or [])]

        topic_ids_raw = await run_sync(_topic_ids)
        topic_ids = [str(t).strip() for t in topic_ids_raw if t is not None and str(t).strip()]
        if not topic_ids:
            return

        from app.yandex_disk_service import get_or_create_folder_in_parent, list_video_files_in_folder

        from app.config import settings
        root_path = (settings.YANDEX_DISK_ROOT_PATH or "").strip() or "/bot_videos"
        for tid in topic_ids:
            try:
                topic = await self.topic_repo.get_by_id(uuid.UUID(tid))
            except Exception:
                continue
            if not topic:
                continue
            folder_name = (topic.name or "").strip() or f"category_{str(topic.id)[:8]}"
            folder_path = getattr(topic, "drive_folder_id", None) or ""
            # Всегда находим папку по имени категории (без учёта регистра), чтобы подхватить ручные загрузки в правильную папку
            try:
                resolved = await run_sync(lambda: get_or_create_folder_in_parent(root_path, folder_name))
                if resolved and resolved != folder_path:
                    folder_path = resolved
                    await self.topic_repo.update_drive_folder_id(topic.id, folder_path)
                elif not folder_path:
                    folder_path = resolved
                    await self.topic_repo.update_drive_folder_id(topic.id, folder_path)
            except Exception as e:
                if not folder_path:
                    logger.warning("sync get_or_create_folder %s: %s", folder_name, e)
                    continue
                # folder_path уже был — используем его
                pass
            if not folder_path:
                continue
            try:
                files = await run_sync(lambda: list_video_files_in_folder(folder_path))
            except Exception as e:
                logger.warning("list_disk_folder %s: %s", folder_path, e)
                continue
            topic_name = (topic.name or "").strip() or str(topic.id)
            logger.info("sync_drive: topic=%s folder=%s files_on_disk=%s", topic_name, folder_path, len(files))
            source = await self.source_repo.get_or_create("uploaded")
            created = 0
            for file_path, name, mime in files:
                existing = await self.video_repo.get_by_drive_file_id(file_path)
                if existing:
                    continue
                url = f"https://disk.yandex.ru/client/disk{file_path}" if file_path.startswith("/") else f"https://disk.yandex.ru/client/disk/{file_path}"
                content_code = None
                try:
                    from app.utils.content_code import parse_from_filename
                    content_code = parse_from_filename(name or "")
                except Exception:
                    pass
                try:
                    await self.video_repo.create(
                        url=url,
                        platform="uploaded",
                        external_id=file_path,
                        source_id=source.id,
                        topic_id=topic.id,
                        description=None,
                        title=name or "—",
                        drive_file_id=file_path,
                        content_code=content_code,
                    )
                    created += 1
                except Exception as e:
                    logger.warning("create_video for drive_file_id %s: %s", file_path, e)
            if created:
                logger.info("sync_drive: topic=%s добавлено в БД видео: %s", topic_name, created)

    async def get_next_video(self, telegram_id: int) -> VideoDistributionDto | None:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("Пользователь не найден")

        video = await self.dist_repo.find_available_video(user.id)
        if not video:
            await self._sync_drive_folders_to_db(user.id)
            video = await self.dist_repo.find_available_video(user.id)
        if video:
            dist = await self.dist_repo.create(video_id=video.id, user_id=user.id)
            # Добавить в код контента критерий дистрибьютора (D) — из id пользователя
            from app.utils.content_code import append_distributor, user_id_to_code
            distributor_code = user_id_to_code(user.id)
            current_code = getattr(video, "content_code", None) or ""
            new_code = append_distributor(current_code, distributor_code)
            if new_code != current_code:
                await self.video_repo.update_content_code(video.id, new_code)
            await self.log_repo.log(
                action="get_video",
                user_id=user.id,
                telegram_id=telegram_id,
                details={"video_id": str(video.id), "distribution_id": str(dist.id)},
            )
            out = await self.dist_repo.get_by_id(dist.id)
            return await self._ensure_video(out) if out else None

        return None

    async def submit_result(
        self, distribution_id: uuid.UUID, url: str, telegram_id: int
    ):
        url = url.strip()
        if await self.result_repo.url_exists(url):
            raise ValueError("Эта ссылка уже была отправлена ранее")

        dist = await self.dist_repo.get_by_id(distribution_id)
        if not dist:
            raise ValueError("Задача не найдена")

        info = detect_platform(url)
        result = await self.result_repo.create(
            distribution_id=distribution_id,
            url=url,
            platform=info.platform,
        )

        if not dist.completed:
            await self.dist_repo.mark_completed(distribution_id)

        # Удалить видео с Яндекс.Диска после отправки ссылки-результата
        drive_file_id = None
        video = await self.video_repo.get_by_id(dist.video_id)
        if video and getattr(video, "drive_file_id", None):
            drive_file_id = (video.drive_file_id or "").strip()
        if not drive_file_id and dist.video and getattr(dist.video, "drive_file_id", None):
            drive_file_id = (dist.video.drive_file_id or "").strip()
        # Путь может быть с ведущим / или без; delete_file сам добавит /
        if drive_file_id and "/" in drive_file_id:
            from app.yandex_disk_service import remove_file_from_drive
            from app.supabase_async import run_sync
            try:
                await run_sync(lambda: remove_file_from_drive(drive_file_id))
                logger.info("submit_result: файл с Яндекс.Диска удалён %s", drive_file_id)
            except Exception as e:
                logger.warning("submit_result: не удалось убрать файл с Яндекс.Диска %s: %s", drive_file_id, e)
        elif drive_file_id:
            logger.warning("submit_result: drive_file_id не похож на путь, удаление пропущено: %s", drive_file_id)
        else:
            logger.warning("submit_result: у видео video_id=%s нет drive_file_id, удаление с диска не выполнялось", dist.video_id)
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        await self.log_repo.log(
            action="submit_result",
            user_id=user.id if user else None,
            telegram_id=telegram_id,
            details={
                "distribution_id": str(distribution_id),
                "result_url": url,
                "platform": info.platform,
            },
        )
        return result

    async def get_active_tasks(self, telegram_id: int) -> list[VideoDistributionDto]:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return []
        return await self.dist_repo.get_active_for_user(user.id)
