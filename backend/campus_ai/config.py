from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CAMPUS_AI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./data/campus_ai.db"
    timezone: str = "Asia/Shanghai"
    daily_fetch_hour: int = Field(default=7, ge=0, le=23)
    daily_fetch_minute: int = Field(default=0, ge=0, le=59)
    worker_poll_seconds: float = Field(default=2, gt=0)
    job_lock_timeout_seconds: int = Field(default=300, ge=30)
    job_kinds: str = ""

    api_base_url: str = ""
    api_key: str = ""
    model: str = ""
    ai_output_mode: Literal["json_schema", "json_object"] = "json_schema"

    ntfy_base_url: str = ""
    fcm_project_id: str = ""
    google_application_credentials: str = ""
    secret_key: str = ""

    @property
    def enabled_job_kinds(self) -> set[str] | None:
        values = {item.strip() for item in self.job_kinds.split(",") if item.strip()}
        return values or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
