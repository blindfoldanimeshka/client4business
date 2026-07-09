from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения. Секреты сюда не кладём в открытом виде -
    только через переменные окружения / .env, который не коммитится."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "local"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "sqlite:///./local.db"

    # Auth-заглушка: имена заголовков, из которых читаем контекст запроса.
    AUTH_WORKSPACE_HEADER: str = "X-Workspace-Id"
    AUTH_USER_HEADER: str = "X-User-Id"
    AUTH_ACTIONS_HEADER: str = "X-Actions"

    IDEMPOTENCY_HEADER: str = "Idempotency-Key"


@lru_cache
def get_settings() -> Settings:
    return Settings()
