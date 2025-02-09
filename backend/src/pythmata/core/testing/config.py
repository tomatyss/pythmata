"""Test configuration module for pythmata."""

import os
from typing import Optional

# Database configuration with environment variables and defaults
POSTGRES_USER = os.getenv("POSTGRES_USER", "pythmata")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "pythmata")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_TEST_DB = os.getenv("POSTGRES_TEST_DB", "pythmata_test")
POSTGRES_MAIN_DB = "postgres"  # For initial connection to create test db

def get_db_url(database: Optional[str] = None, for_asyncpg: bool = True) -> str:
    """Get database URL with the specified configuration.
    
    Args:
        database: Optional database name. If not provided, uses POSTGRES_TEST_DB
        for_asyncpg: If True, returns asyncpg URL format, else SQLAlchemy format
    
    Returns:
        str: Formatted database URL
    """
    db_name = database or POSTGRES_TEST_DB
    
    if for_asyncpg:
        return f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{db_name}"
    else:
        return f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{db_name}"

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# RabbitMQ configuration
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "5672")
RABBITMQ_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"
