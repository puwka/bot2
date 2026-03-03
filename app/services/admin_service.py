import uuid
from dataclasses import dataclass

from app.config import settings
from app.dto import UserRole
from app.repositories.user_repo import UserRepository
from app.repositories.topic_repo import TopicRepository
from app.repositories.video_repo import VideoRepository
from app.repositories.distribution_repo import DistributionRepository
from app.repositories.result_repo import ResultRepository
from app.repositories.user_category_repo import UserCategoryRepository
from app.repositories.action_log_repo import ActionLogRepository
from app.supabase_async import run_sync


@dataclass
class StatsData:
    total_videos: int
    total_distributed: int
    completed_tasks: int
    total_links: int
    total_users: int


class AdminService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.topic_repo = TopicRepository()
        self.video_repo = VideoRepository()
        self.dist_repo = DistributionRepository()
        self.result_repo = ResultRepository()
        self.uc_repo = UserCategoryRepository()
        self.log_repo = ActionLogRepository()

    async def create_topic(self, name: str, admin_telegram_id: int):
        from app.dto import TopicDto

        existing = await self.topic_repo.get_by_name(name)
        if existing:
            raise ValueError(f"Категория '{name}' уже существует")
        topic = await self.topic_repo.create(name)
        if (settings.YANDEX_DISK_TOKEN or "").strip():
            try:
                from app.yandex_disk_service import get_or_create_folder_in_parent
                root_path = (settings.YANDEX_DISK_ROOT_PATH or "").strip() or "/bot_videos"
                folder_name = (name or "").strip() or f"category_{str(topic.id)[:8]}"
                folder_path = await run_sync(lambda: get_or_create_folder_in_parent(root_path, folder_name))
                await self.topic_repo.update_drive_folder_id(topic.id, folder_path)
            except Exception as e:
                await self.log_repo.log(
                    action="create_topic_disk_error",
                    user_id=None,
                    telegram_id=admin_telegram_id,
                    details={"topic_id": str(topic.id), "error": str(e)},
                )
                raise ValueError(f"Категория создана, но папка на Яндекс.Диске не создана: {e}") from e
        admin = await self.user_repo.get_by_telegram_id(admin_telegram_id)
        await self.log_repo.log(
            action="create_topic",
            user_id=admin.id if admin else None,
            telegram_id=admin_telegram_id,
            details={"topic_name": name, "topic_id": str(topic.id)},
        )
        return topic

    async def create_user(
        self,
        telegram_id: int,
        role: UserRole,
        admin_telegram_id: int,
        username: str | None = None,
        full_name: str | None = None,
    ):
        existing = await self.user_repo.get_by_telegram_id(telegram_id)
        if existing:
            raise ValueError(f"Пользователь с telegram_id={telegram_id} уже существует")
        user = await self.user_repo.create(
            telegram_id=telegram_id, role=role, username=username, full_name=full_name
        )
        admin = await self.user_repo.get_by_telegram_id(admin_telegram_id)
        await self.log_repo.log(
            action="create_user",
            user_id=admin.id if admin else None,
            telegram_id=admin_telegram_id,
            details={
                "new_user_telegram_id": telegram_id,
                "role": role.value,
                "user_id": str(user.id),
            },
        )
        return user

    async def assign_role(
        self, target_telegram_id: int, role: UserRole, admin_telegram_id: int
    ):
        user = await self.user_repo.get_by_telegram_id(target_telegram_id)
        if not user:
            raise ValueError(f"Пользователь с telegram_id={target_telegram_id} не найден")
        old_role = user.role
        user = await self.user_repo.update_role(user.id, role)
        admin = await self.user_repo.get_by_telegram_id(admin_telegram_id)
        await self.log_repo.log(
            action="assign_role",
            user_id=admin.id if admin else None,
            telegram_id=admin_telegram_id,
            details={
                "target_telegram_id": target_telegram_id,
                "old_role": old_role.value,
                "new_role": role.value,
            },
        )
        return user

    async def assign_category(
        self, target_telegram_id: int, topic_id: uuid.UUID, admin_telegram_id: int
    ) -> None:
        user = await self.user_repo.get_by_telegram_id(target_telegram_id)
        if not user:
            raise ValueError(f"Пользователь с telegram_id={target_telegram_id} не найден")
        await self.uc_repo.assign(user.id, topic_id)
        admin = await self.user_repo.get_by_telegram_id(admin_telegram_id)
        await self.log_repo.log(
            action="assign_category",
            user_id=admin.id if admin else None,
            telegram_id=admin_telegram_id,
            details={
                "target_telegram_id": target_telegram_id,
                "topic_id": str(topic_id),
            },
        )

    async def get_stats(self) -> StatsData:
        total_videos = await self.video_repo.count_all()
        total_distributed = await self.dist_repo.count_total()
        completed_tasks = await self.dist_repo.count_completed()
        total_links = await self.result_repo.count_all()
        total_users = await self.user_repo.count_all()
        return StatsData(
            total_videos=total_videos,
            total_distributed=total_distributed,
            completed_tasks=completed_tasks,
            total_links=total_links,
            total_users=total_users,
        )

    async def get_user_stats(self, target_telegram_id: int) -> dict:
        user = await self.user_repo.get_by_telegram_id(target_telegram_id)
        if not user:
            raise ValueError("Пользователь не найден")
        counts = await self.dist_repo.count_by_user(user.id)
        return {
            "telegram_id": user.telegram_id,
            "username": user.username,
            "role": user.role.value,
            "total_assigned": counts["total"],
            "completed": counts["completed"],
        }

    async def get_unfinished_tasks(self):
        return await self.dist_repo.get_unfinished_all()

    async def reassign_distribution(
        self, dist_id: uuid.UUID, new_telegram_id: int, admin_telegram_id: int
    ) -> None:
        new_user = await self.user_repo.get_by_telegram_id(new_telegram_id)
        if not new_user:
            raise ValueError("Целевой пользователь не найден")
        dist = await self.dist_repo.reassign(dist_id, new_user.id)
        if not dist:
            raise ValueError("Задача не найдена")
        admin = await self.user_repo.get_by_telegram_id(admin_telegram_id)
        await self.log_repo.log(
            action="reassign_distribution",
            user_id=admin.id if admin else None,
            telegram_id=admin_telegram_id,
            details={
                "distribution_id": str(dist_id),
                "new_user_telegram_id": new_telegram_id,
            },
        )

    async def list_users(self):
        return await self.user_repo.list_all()

    async def list_topics(self):
        return await self.topic_repo.list_all()

    async def get_category_stats(self) -> list[dict]:
        topics = await self.topic_repo.list_all()
        result = []
        for topic in topics:
            count = await self.video_repo.count_by_topic(topic.id)
            result.append({"topic_name": topic.name, "topic_id": str(topic.id), "video_count": count})
        return result
