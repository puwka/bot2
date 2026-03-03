"""Plain DTOs for Supabase responses (no SQLAlchemy)."""
from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass
from typing import Any


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    UPLOADER = "UPLOADER"
    DISTRIBUTOR = "DISTRIBUTOR"


def _uuid(v: Any) -> uuid.UUID | None:
    if v is None:
        return None
    return uuid.UUID(str(v)) if not isinstance(v, uuid.UUID) else v


def _int(v: Any) -> int | None:
    if v is None:
        return None
    return int(v)


@dataclass
class UserDto:
    id: uuid.UUID
    telegram_id: int
    username: str | None
    full_name: str | None
    role: UserRole
    is_active: bool
    performer_code: int | None = None  # код исполнителя для content_code (1–99), у загрузчиков
    distributor_code: int | None = None  # код дистрибьютора для content_code (1–99), у дистрибьюторов

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> UserDto:
        return cls(
            id=_uuid(row["id"]),
            telegram_id=int(row["telegram_id"]),
            username=row.get("username"),
            full_name=row.get("full_name"),
            role=UserRole(row["role"]),
            is_active=row.get("is_active", True),
            performer_code=_int(row.get("performer_code")),
            distributor_code=_int(row.get("distributor_code")),
        )


@dataclass
class TopicDto:
    id: uuid.UUID
    name: str
    drive_folder_id: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> TopicDto:
        name = row.get("keyword") or row.get("title") or row.get("name") or ""
        return cls(
            id=_uuid(row["id"]),
            name=name,
            drive_folder_id=row.get("drive_folder_id"),
        )


@dataclass
class SourceDto:
    id: uuid.UUID
    platform: str
    name: str | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> SourceDto:
        return cls(
            id=_uuid(row["id"]),
            platform=row["platform"],
            name=row.get("name"),
        )


@dataclass
class VideoDto:
    id: uuid.UUID
    url: str
    platform: str | None
    external_id: str | None
    description: str | None
    topic_id: uuid.UUID | None
    source_id: uuid.UUID | None
    drive_file_id: str | None = None
    content_code: str | None = None  # маркировка: исполнитель, сценарий, подтема, шаблон (см. CONTENT_CODE.md)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> VideoDto:
        return cls(
            id=_uuid(row["id"]),
            url=row.get("url") or "",
            platform=row.get("platform"),
            external_id=row.get("external_id"),
            description=row.get("description"),
            topic_id=_uuid(row.get("topic_id")),
            source_id=_uuid(row.get("source_id")),
            drive_file_id=row.get("drive_file_id"),
            content_code=row.get("content_code"),
        )


@dataclass
class UserCategoryDto:
    id: uuid.UUID
    user_id: uuid.UUID
    topic_id: uuid.UUID
    topic: TopicDto | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> UserCategoryDto:
        topic = None
        if "topic" in row and row["topic"]:
            topic = TopicDto.from_row(row["topic"]) if isinstance(row["topic"], dict) else None
        return cls(
            id=_uuid(row["id"]),
            user_id=_uuid(row["user_id"]),
            topic_id=_uuid(row["topic_id"]),
            topic=topic,
        )


@dataclass
class VideoResultDto:
    id: uuid.UUID
    distribution_id: uuid.UUID
    url: str
    platform: str | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> VideoResultDto:
        return cls(
            id=_uuid(row["id"]),
            distribution_id=_uuid(row["distribution_id"]),
            url=row["url"],
            platform=row.get("platform"),
        )


@dataclass
class VideoDistributionDto:
    id: uuid.UUID
    video_id: uuid.UUID
    user_id: uuid.UUID
    completed: bool
    assigned_at: str
    completed_at: str | None
    video: VideoDto | None = None
    user: UserDto | None = None
    results: list[VideoResultDto] | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> VideoDistributionDto:
        video = None
        v = row.get("video") or row.get("videos")
        if v and isinstance(v, dict):
            video = VideoDto.from_row(v)
        user = None
        u = row.get("user") or row.get("users")
        if u and isinstance(u, dict):
            user = UserDto.from_row(u)
        results = None
        res = row.get("results") or row.get("video_results")
        if res and isinstance(res, list):
            results = [VideoResultDto.from_row(r) for r in res if isinstance(r, dict)]
        return cls(
            id=_uuid(row["id"]),
            video_id=_uuid(row["video_id"]),
            user_id=_uuid(row["user_id"]),
            completed=row.get("completed", False),
            assigned_at=row.get("assigned_at", ""),
            completed_at=row.get("completed_at"),
            video=video,
            user=user,
            results=results,
        )


@dataclass
class ActionLogDto:
    id: uuid.UUID
    action: str
    details: dict[str, Any] | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> ActionLogDto:
        return cls(
            id=_uuid(row["id"]),
            action=row["action"],
            details=row.get("details"),
        )
