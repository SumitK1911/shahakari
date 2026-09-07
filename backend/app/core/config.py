from functools import lru_cache

from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Sahakari Management System"
    environment: str = "local"
    secret_key: str = Field(min_length=16)
    access_token_expire_minutes: int = 60
    database_url: str
    sync_database_url: str
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[AnyHttpUrl] | list[str] = ["http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.environment.lower() not in {"local", "development", "dev", "test"}:
            if self.secret_key.startswith("change-me") or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be changed to a strong value outside local development")
            if not self.cors_origins:
                raise ValueError("CORS_ORIGINS must list the approved HTTPS application origins in production")
            if any(str(origin).startswith("http://localhost") or str(origin).startswith("http://127.0.0.1") for origin in self.cors_origins):
                raise ValueError("Localhost CORS origins are not allowed outside local development")
        return self

    @property
    def is_local_environment(self) -> bool:
        return self.environment.lower() in {"local", "development", "dev", "test"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
