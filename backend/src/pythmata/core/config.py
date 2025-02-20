from functools import lru_cache
from pathlib import Path
from typing import Optional, Dict, Any

import toml
from pythmata.utils.logger import get_logger
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


logger = get_logger(__name__)


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
        logger.info("[Settings] Initializing application settings")
        
        # Log initial kwargs
        logger.debug(f"[Settings] Initial kwargs: {kwargs}")
        
        # If all required settings are provided, skip TOML loading
        required_settings = [
            "server",
            "database",
            "redis",
            "rabbitmq",
            "security",
            "process",
        ]
        
        if all(key in kwargs for key in required_settings):
            logger.info("[Settings] All required settings provided in kwargs, skipping TOML loading")
            try:
                super().__init__(**kwargs)
                logger.info("[Settings] Settings initialized successfully from kwargs")
                return
            except Exception as e:
                logger.error(f"[Settings] Validation error with provided kwargs: {str(e)}")
                raise

        # Load config from TOML file if specified
        config_file = kwargs.pop("config_file", None)
        if not config_file:
            # Try to find config file in standard locations
            locations = [
                Path("config/development.toml"),  # Local development
                Path("/app/config/development.toml"),  # Docker
            ]
            logger.info("[Settings] Searching for config file in standard locations")
            for loc in locations:
                logger.debug(f"[Settings] Checking location: {loc}")
                if loc.exists():
                    config_file = loc
                    logger.info(f"[Settings] Found config file at: {loc}")
                    break
            if not config_file:
                logger.warning("[Settings] No config file found in standard locations")

        config: Dict[str, Any] = {}
        if config_file and config_file.exists():
            logger.info(f"[Settings] Loading configuration from: {config_file}")
            try:
                config = toml.load(config_file)
                logger.debug(f"[Settings] Loaded raw config data: {config}")
                kwargs.update(config)
                logger.info("[Settings] Successfully merged TOML config with kwargs")
            except Exception as e:
                logger.error(f"[Settings] Error loading TOML file: {str(e)}")
                raise

        logger.debug(f"[Settings] Final configuration before validation: {kwargs}")
        try:
            super().__init__(**kwargs)
            logger.info("[Settings] Settings initialized and validated successfully")
        except Exception as e:
            logger.error(f"[Settings] Settings validation failed: {str(e)}")
            logger.error("[Settings] Missing or invalid configuration. Ensure all required settings are provided.")
            raise


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
