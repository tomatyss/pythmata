import logging
import sys
from functools import wraps
from traceback import format_exc
from typing import Any, Callable

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


def log_error(logger: logging.Logger) -> Callable:
    """Decorator to log exceptions with traceback."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_details = f"Error: {str(e)}\nTraceback: {format_exc()}"
                logger.error(error_details)
                raise

        return wrapper

    return decorator
