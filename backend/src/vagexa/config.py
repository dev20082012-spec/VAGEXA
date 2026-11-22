from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process configuration. There is no default database URL or session secret."""

    model_config = SettingsConfigDict(env_prefix="VAGEXA_", extra="ignore")

    data_mode: Literal["synthetic", "operational"]
    database_url: str = Field(min_length=1)
    cookie_secure: bool = True
    cors_origins: str = "http://127.0.0.1:5173"
    log_level: str = "info"
    environment: str = "local"
    bootstrap_username: str | None = None
    bootstrap_password: str | None = None
    bootstrap_display_name: str = "Investigator"
    storage_dir: str = "var/storage"
    static_dir: str = ""
    require_demo: bool = False
    upload_max_bytes: int = 25_000_000
    passive_intel: bool = False

    @field_validator("database_url")
    @classmethod
    def database_url_present(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("VAGEXA_DATABASE_URL is required")
        return value

    @model_validator(mode="after")
    def insecure_cookie_only_for_synthetic(self) -> "Settings":
        if not self.cookie_secure and self.data_mode != "synthetic":
            raise ValueError("VAGEXA_COOKIE_SECURE=false is allowed only when data mode is synthetic")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
