# Configuration Reference

## Overview

Pythmata uses a combination of TOML configuration files and environment variables for configuration. The configuration is structured into several sections:
- Server settings
- Database settings
- Redis settings
- RabbitMQ settings
- Security settings
- Process settings

## Configuration File

### Default Location
```bash
/app/config/development.toml
```

### Example Configuration (development.toml)
```toml
[server]
host = "0.0.0.0"
port = 8000
debug = true

[database]
url = "postgresql+asyncpg://pythmata:pythmata@postgres:5432/pythmata"
pool_size = 5
max_overflow = 10
connection_timeout = 30
retry_attempts = 3
retry_delay = 5

[redis]
url = "redis://redis:6379/0"
pool_size = 10
connection_timeout = 30
retry_attempts = 3
retry_delay = 5

[rabbitmq]
url = "amqp://guest:guest@rabbitmq:5672/"
connection_attempts = 5
retry_delay = 5
connection_timeout = 30

[security]
secret_key = "development_secret_key"
algorithm = "HS256"
access_token_expire_minutes = 30

[process]
script_timeout = 30
max_instances = 1000
cleanup_interval = 3600
```

## Environment Variables

Environment variables can override TOML configuration using nested delimiters:

```bash
# Server Settings
PYTHMATA_SERVER__HOST=0.0.0.0
PYTHMATA_SERVER__PORT=8000
PYTHMATA_SERVER__DEBUG=false

# Database Settings
PYTHMATA_DATABASE__URL=postgresql+asyncpg://user:pass@localhost:5432/pythmata
PYTHMATA_DATABASE__POOL_SIZE=5
PYTHMATA_DATABASE__MAX_OVERFLOW=10

# Redis Settings
PYTHMATA_REDIS__URL=redis://localhost:6379/0
PYTHMATA_REDIS__POOL_SIZE=10

# RabbitMQ Settings
PYTHMATA_RABBITMQ__URL=amqp://guest:guest@localhost:5672/
PYTHMATA_RABBITMQ__CONNECTION_ATTEMPTS=5
PYTHMATA_RABBITMQ__RETRY_DELAY=5

# Security Settings
PYTHMATA_SECURITY__SECRET_KEY=your-secret-key
PYTHMATA_SECURITY__ALGORITHM=HS256
PYTHMATA_SECURITY__ACCESS_TOKEN_EXPIRE_MINUTES=30

# Process Settings
PYTHMATA_PROCESS__SCRIPT_TIMEOUT=30
PYTHMATA_PROCESS__MAX_INSTANCES=1000
PYTHMATA_PROCESS__CLEANUP_INTERVAL=3600
```

## Configuration Models

### Server Settings
```python
class ServerSettings(BaseModel):
    host: str          # Server host address
    port: int          # Server port
    debug: bool        # Debug mode flag
```

### Connection Base Settings
```python
class ConnectionSettings(BaseModel):
    connection_timeout: int = 30  # Connection timeout in seconds
    retry_attempts: int = 3       # Number of retry attempts
    retry_delay: int = 5         # Delay between retries in seconds
```

### Database Settings
```python
class DatabaseSettings(ConnectionSettings):
    url: PostgresDsn   # PostgreSQL connection URL
    pool_size: int     # Connection pool size
    max_overflow: int  # Maximum number of overflow connections
```

### Redis Settings
```python
class RedisSettings(ConnectionSettings):
    url: RedisDsn      # Redis connection URL
    pool_size: int     # Connection pool size
```

### RabbitMQ Settings
```python
class RabbitMQSettings(ConnectionSettings):
    url: AmqpDsn       # RabbitMQ connection URL
    connection_attempts: int  # Number of connection attempts (alias for retry_attempts)
    retry_delay: int   # Delay between retries in seconds
```

### Security Settings
```python
class SecuritySettings(BaseModel):
    secret_key: str    # JWT secret key
    algorithm: str     # JWT algorithm (e.g., "HS256")
    access_token_expire_minutes: int  # Token expiration time
```

### Process Settings
```python
class ProcessSettings(BaseModel):
    script_timeout: int     # Script execution timeout in seconds
    max_instances: int      # Maximum number of process instances
    cleanup_interval: int   # Cleanup interval in seconds
```

## Loading Configuration

The configuration is loaded using Pydantic's settings management:

```python
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings

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

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

## Connection Management

### Connection Lifecycle
The application uses a unified connection management system that provides:
- Automatic connection establishment
- Connection state tracking
- Automatic reconnection on failures
- Proper resource cleanup

### Connection States
- **Disconnected**: Initial state or after explicit disconnect
- **Connecting**: During connection attempt
- **Connected**: Successfully connected
- **Failed**: Connection attempt failed
- **Reconnecting**: Attempting to reestablish connection

### Error Handling
- Connection failures trigger automatic retry attempts
- Retries follow exponential backoff strategy
- Exceeded retry attempts raise ConnectionError
- Connection state is accurately tracked

## Best Practices

### 1. Connection Management
- Configure appropriate timeouts for your environment
- Set retry attempts based on service reliability
- Use reasonable retry delays to prevent overwhelming services
- Monitor connection states and failures

### 2. Environment-Specific Configuration
- Use different TOML files for different environments (development.toml, production.toml)
- Override sensitive values using environment variables
- Never commit sensitive values to version control

### 2. Security
- Use strong secret keys in production
- Store sensitive values in environment variables
- Rotate secrets regularly
- Use appropriate connection timeouts

### 3. Performance
- Configure appropriate pool sizes based on load
- Set reasonable timeouts and retry values
- Monitor resource usage
- Adjust cleanup intervals based on needs

### 4. Development
- Use debug mode in development only
- Set shorter timeouts for development
- Use local services in development
- Enable detailed logging

## Docker Environment

When running with Docker, configure services in docker-compose.yml:

```yaml
version: '3.8'
services:
  backend:
    environment:
      - PYTHMATA_DATABASE__URL=postgresql+asyncpg://pythmata:pythmata@postgres:5432/pythmata
      - PYTHMATA_REDIS__URL=redis://redis:6379/0
      - PYTHMATA_RABBITMQ__URL=amqp://guest:guest@rabbitmq:5672/

  postgres:
    environment:
      - POSTGRES_USER=pythmata
      - POSTGRES_PASSWORD=pythmata
      - POSTGRES_DB=pythmata

  redis:
    command: redis-server

  rabbitmq:
    environment:
      - RABBITMQ_DEFAULT_USER=guest
      - RABBITMQ_DEFAULT_PASS=guest
