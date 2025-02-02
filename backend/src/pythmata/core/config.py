from functools import lru_cache
from pathlib import Path
from typing import Optional

import toml
from pydantic import AmqpDsn, BaseModel, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseModel):
    host: str
    port: int
    debug: bool


class DatabaseSettings(BaseModel):
    url: PostgresDsn
    pool_size: int
    max_overflow: int


class RedisSettings(BaseModel):
    url: RedisDsn
    pool_size: int


class RabbitMQSettings(BaseModel):
    url: AmqpDsn
    connection_attempts: int
    retry_delay: int


class SecuritySettings(BaseModel):
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int


class ProcessSettings(BaseModel):
    script_timeout: int
    max_instances: int
    cleanup_interval: int


class Settings(BaseSettings):
    """Application settings loaded from TOML file."""

    config_file: Optional[Path] = None

    server: ServerSettings
    database: DatabaseSettings
    redis: RedisSettings
    rabbitmq: RabbitMQSettings
    security: SecuritySettings
    process: ProcessSettings

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    def __init__(self, **kwargs):
        # Load config from TOML file if specified
        config_file = kwargs.pop("config_file", None) or Path(
            "/app/config/development.toml"
        )
        if config_file and config_file.exists():
            config = toml.load(config_file)
            kwargs.update(config)

        super().__init__(**kwargs)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
