from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/ai_recruitment_email_assistant"
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_agent_enabled: bool = False
    gemini_timeout_seconds: float = Field(default=20.0, ge=1.0, le=120.0)
    gemini_max_retries: int = Field(default=1, ge=0, le=5)
    gemini_agent_max_steps: int = Field(default=2, ge=1, le=3)
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672//"
    redis_url: str = "redis://localhost:6379/0"
    review_lock_ttl_seconds: int = Field(default=120, ge=30, le=3600)
    review_progress_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    outbox_batch_size: int = Field(default=50, ge=1, le=500)
    outbox_poll_interval_seconds: float = Field(default=1.0, ge=0.1, le=60.0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def gemini_api_key_value(self) -> str | None:
        if self.gemini_api_key is None:
            return None

        value = self.gemini_api_key.get_secret_value().strip()
        return value or None

    @property
    def gemini_is_configured(self) -> bool:
        return self.gemini_agent_enabled and self.gemini_api_key_value is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()
