"""Connection management utilities."""

import functools
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Protocol, TypeVar, runtime_checkable

logger = logging.getLogger(__name__)

T = TypeVar("T")


@runtime_checkable
class Connectable(Protocol):
    """Protocol for objects that can be connected/disconnected."""

    @property
    def is_connected(self) -> bool: ...

    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...


def ensure_connected(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to ensure a connection is established before executing a function.

    This decorator should be used on methods of classes that implement the
    Connectable protocol (i.e., have connect/disconnect methods and is_connected property).

    Args:
        func: Async function to wrap

    Returns:
        Wrapped function that ensures connection before execution

    Example:
        @ensure_connected
        async def my_method(self):
            # This will only run if connected
            ...
    """

    @functools.wraps(func)
    async def wrapper(self: Connectable, *args: Any, **kwargs: Any) -> Any:
        if not self.is_connected:
            await self.connect()
        try:
            return await func(self, *args, **kwargs)
        except Exception as e:
            # If the error is due to connection issues, attempt to reconnect
            if isinstance(e, ConnectionError) or "connection" in str(e).lower():
                logger.warning(
                    f"Connection error in {func.__name__}, attempting to reconnect"
                )
                await self.disconnect()
                await self.connect()
                return await func(self, *args, **kwargs)
            raise

    return wrapper


class ConnectionError(Exception):
    """Exception raised for connection-related errors."""

    pass


class ConnectionManager(ABC):
    """Base class for managing service connections.

    This class provides a common interface and basic functionality for
    managing connections to external services (databases, message queues, etc.).

    Subclasses must implement:
    - _do_connect(): Establish the actual connection
    - _do_disconnect(): Close the actual connection
    """

    def __init__(self):
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._is_connected

    async def connect(self) -> None:
        """Establish connection if not already connected.

        Raises:
            ConnectionError: If connection fails
        """
        if self.is_connected:
            logger.debug("Already connected")
            return

        try:
            await self._do_connect()
            self._is_connected = True
            logger.info("Successfully connected")
        except Exception as e:
            self._is_connected = False
            error_msg = f"Failed to connect: {str(e)}"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e

    async def disconnect(self) -> None:
        """Close connection if currently connected.

        Raises:
            ConnectionError: If disconnection fails
        """
        if not self.is_connected:
            logger.debug("Already disconnected")
            return

        try:
            await self._do_disconnect()
            self._is_connected = False
            logger.info("Successfully disconnected")
        except Exception as e:
            error_msg = f"Failed to disconnect: {str(e)}"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e

    @abstractmethod
    async def _do_connect(self) -> None:
        """Implement actual connection logic.

        This method should be implemented by subclasses to perform
        the actual connection to their specific service.

        Raises:
            Exception: If connection fails
        """
        pass

    @abstractmethod
    async def _do_disconnect(self) -> None:
        """Implement actual disconnection logic.

        This method should be implemented by subclasses to perform
        the actual disconnection from their specific service.

        Raises:
            Exception: If disconnection fails
        """
        pass

    async def __aenter__(self) -> "ConnectionManager":
        """Async context manager entry.

        Returns:
            Self for use in context manager
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit.

        Ensures disconnection even if an error occurred.
        """
        await self.disconnect()
