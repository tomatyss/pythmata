"""Error handling utilities."""

import functools
from typing import Any, Callable, Dict

from pythmata.core.config import Settings
from pythmata.core.database import get_db
from pythmata.core.engine.instance import ProcessInstanceManager
from pythmata.core.state import StateManager
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


def handle_process_errors(func: Callable):
    """Decorator for standardized process error handling.

    Provides consistent error handling for process-related operations,
    including cleanup and error logging.

    Args:
        func: The async function to wrap

    Returns:
        Wrapped function with standardized error handling
    """

    @functools.wraps(func)
    async def wrapper(data: Dict[str, Any], *args: Any, **kwargs: Any) -> Any:
        instance_id = data.get("instance_id")
        try:
            return await func(data, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)

            # Attempt cleanup if we have an instance ID
            if instance_id:
                try:
                    logger.info(
                        "[ErrorCleanup] Attempting to initialize services for cleanup"
                    )
                    settings = Settings()
                    state_manager = StateManager(settings)
                    logger.info("[ErrorCleanup] State manager initialized for cleanup")
                    await state_manager.connect()

                    async with get_db().session() as session:
                        instance_manager = ProcessInstanceManager(
                            session, None, state_manager
                        )
                        await instance_manager.handle_error(instance_id, e)
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup: {cleanup_error}")

            # Re-raise to ensure proper error handling at higher levels
            raise

    return wrapper
