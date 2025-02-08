import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from pythmata.core.config import Settings
from pythmata.models.process import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# Load test settings
def get_test_settings() -> Settings:
    """Create test settings with environment-aware configuration."""
    import os
    
    # Database configuration
    db_user = os.getenv("POSTGRES_USER", "pythmata")
    db_password = os.getenv("POSTGRES_PASSWORD", "pythmata")
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_TEST_DB", "pythmata_test")
    
    # Convert asyncpg URL to psycopg2 URL for synchronous operations
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    return Settings(
        server={"host": "localhost", "port": 8000, "debug": True},
        database={"url": db_url, "pool_size": 5, "max_overflow": 10},
        redis={"url": "redis://localhost:6379/0", "pool_size": 10},
        rabbitmq={
            "url": "amqp://guest:guest@localhost:5672/",
            "connection_attempts": 3,
            "retry_delay": 1,
        },
        security={
            "secret_key": "test-secret-key",
            "algorithm": "HS256",
            "access_token_expire_minutes": 30,
        },
        process={
            "script_timeout": 30,
            "max_instances": 100,
            "cleanup_interval": 60,
        },
    )

settings = get_test_settings()

# Override sqlalchemy.url from alembic.ini with test config
config.set_main_option("sqlalchemy.url", str(settings.database.url))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
