from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized configuration for InsightSentinel AI.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Postgres
    postgres_db: str = "insightsentinel"
    postgres_user: str = "insightsentinel"
    postgres_password: str = "insightsentinel_pass"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    log_level: str = "INFO"

    # SQLAlchemy
    sqlalchemy_echo: bool = False

    # Scheduler
    enable_scheduler: bool = True
    scheduler_interval_minutes: int = 10

    @property
    def postgres_dsn(self) -> str:
        # SQLAlchemy DSN (psycopg3)
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
