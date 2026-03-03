from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    BOT_TOKEN: str
    WEBHOOK_HOST: str = ""
    WEBHOOK_PATH: str = "/webhook"
    WEBAPP_HOST: str = "0.0.0.0"
    WEBAPP_PORT: int = 8080
    USE_POLLING: bool = Field(default=False, description="True = polling (local dev), False = webhook")

    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str

    @field_validator("SUPABASE_URL", mode="after")
    @classmethod
    def normalize_supabase_url(cls, v: str) -> str:
        url = (v or "").strip().rstrip("/")
        if not url.startswith("https://"):
            url = "https://" + url.lstrip("/")
        return url

    RATE_LIMIT_SECONDS: int = Field(default=2, description="Min seconds between messages per user")
    LOG_LEVEL: str = "INFO"
    # Колонка названия в таблице topics: keyword, title или name (зависит от вашей схемы)
    TOPIC_NAME_COLUMN: str = Field(default="keyword", description="Column for topic name in topics table")
    # Бакет Supabase Storage (если не используете Google Drive)
    STORAGE_BUCKET: str = Field(default="videos", description="Supabase Storage bucket for uploaded videos")
    # Яндекс.Диск: OAuth-токен (обязательно для загрузки и удаления видео)
    YANDEX_DISK_TOKEN: str = Field(default="", description="OAuth token for Yandex Disk API")
    # Корневая папка на Яндекс.Диске (путь, например /bot_videos), в ней — папки категорий
    YANDEX_DISK_ROOT_PATH: str = Field(default="/bot_videos", description="Root folder path on Yandex Disk for category folders")

    @property
    def webhook_url(self) -> str:
        return f"{self.WEBHOOK_HOST.rstrip('/')}{self.WEBHOOK_PATH}"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()  # type: ignore[call-arg]
