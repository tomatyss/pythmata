"""Application lifecycle management utilities."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from pythmata.core.config import Settings
from pythmata.core.database import get_db, init_db
from pythmata.core.engine.events.timer_scheduler import TimerScheduler
from pythmata.core.events import EventBus
from pythmata.core.services import get_service_task_registry
from pythmata.core.state import StateManager
from pythmata.core.utils.event_handlers import register_event_handlers
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


async def discover_and_load_plugins() -> None:
    """Discover and load plugins from the plugin directory."""
    plugin_dir = os.environ.get("PYTHMATA_PLUGIN_DIR", "/app/plugins")
    if os.path.isdir(plugin_dir):
        from pythmata.core.plugin import discover_plugins

        logger.info(f"Discovering plugins from {plugin_dir}")
        discover_plugins(plugin_dir)
    else:
        logger.info(
            f"Plugin directory not found: {plugin_dir}, skipping plugin discovery"
        )


async def initialize_timer_scheduler(
    state_manager: StateManager, event_bus: EventBus
) -> TimerScheduler:
    """Initialize and start the timer scheduler.

    Args:
        state_manager: The state manager
        event_bus: The event bus

    Returns:
        The initialized timer scheduler
    """
    timer_scheduler = TimerScheduler(state_manager, event_bus)

    # Recover timer state from previous run if needed
    await timer_scheduler.recover_from_crash()
    logger.info("Timer state recovered from previous run")

    # Start the timer scheduler
    await timer_scheduler.start()
    logger.info("Timer scheduler started")

    return timer_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    services = []
    try:
        # Initialize services
        settings = Settings()
        app.state.event_bus = EventBus(settings)
        services.append(app.state.event_bus)

        app.state.state_manager = StateManager(settings)
        services.append(app.state.state_manager)

        # Discover plugins
        await discover_and_load_plugins()

        # Initialize database
        logger.info("Initializing database...")
        init_db(settings)
        db = get_db()
        services.append(db)

        # Connect all services
        logger.info("Connecting to database...")
        await db.connect()
        logger.info("Database connected successfully")

        logger.info("Connecting to event bus...")
        await app.state.event_bus.connect()
        logger.info("Event bus connected successfully")

        logger.info("Connecting to state manager...")
        await app.state.state_manager.connect()
        logger.info("State manager connected successfully")

        # Register event handlers
        await register_event_handlers(app.state.event_bus)

        # Initialize timer scheduler
        app.state.timer_scheduler = await initialize_timer_scheduler(
            app.state.state_manager, app.state.event_bus
        )

        # Log registered service tasks
        registry = get_service_task_registry()
        tasks = registry.list_tasks()
        logger.info(f"Registered service tasks: {[task['name'] for task in tasks]}")

        yield
    finally:
        # Shutdown - ensure all services attempt to disconnect
        shutdown_errors = []

        logger.info("Shutting down services...")

        # Stop timer scheduler first
        if hasattr(app.state, "timer_scheduler"):
            try:
                logger.info("Stopping timer scheduler...")
                await app.state.timer_scheduler.stop()
                logger.info("Timer scheduler stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping timer scheduler: {e}")
                shutdown_errors.append(e)

        # Disconnect all services in reverse order
        for service in reversed(services):
            try:
                if hasattr(service, "disconnect"):
                    await service.disconnect()
                    logger.info(f"Disconnected {service.__class__.__name__}")
            except Exception as e:
                logger.error(f"Error disconnecting {service.__class__.__name__}: {e}")
                shutdown_errors.append(e)

        # If any errors occurred during disconnect, log them but don't raise
        # This ensures all services get a chance to disconnect
        if shutdown_errors:
            logger.error(f"Errors during shutdown: {shutdown_errors}")
