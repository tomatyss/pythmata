from pythmata.core.bpmn.parser import BPMNParser
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pythmata.api.routes import router as process_router
from pythmata.core.config import Settings
from pythmata.core.database import get_db, init_db
from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.events import EventBus
from pythmata.core.state import StateManager

logger = logging.getLogger(__name__)


async def handle_process_started(data: dict) -> None:
    """Handle process.started event."""
    try:
        instance_id = data["instance_id"]
        bpmn_xml = data["bpmn_xml"]
        logger.info(
            f"Handling process.started event for instance {instance_id}")

        # Get required services
        settings = Settings()
        state_manager = StateManager(settings)
        await state_manager.connect()

        try:
            # Parse BPMN XML to process graph
            parser = BPMNParser()
            process_graph = parser.parse(bpmn_xml)
            logger.info("BPMN XML parsed successfully")

            # Create executor and execute process
            executor = ProcessExecutor(state_manager=state_manager)
            await executor.execute_process(instance_id, process_graph)
            logger.info(f"Process {instance_id} execution completed")
        finally:
            await state_manager.disconnect()

    except Exception as e:
        logger.error(
            f"Error handling process.started event: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    settings = Settings()
    app.state.event_bus = EventBus(settings)
    app.state.state_manager = StateManager(settings)

    # Initialize and connect services
    init_db(settings)
    db = get_db()
    await db.connect()  # Establish database connection

    await app.state.event_bus.connect()
    await app.state.state_manager.connect()

    # Subscribe to process.started events
    await app.state.event_bus.subscribe(
        routing_key="process.started",
        callback=handle_process_started,
        queue_name="process_execution",
    )
    logger.info("Subscribed to process.started events")

    yield

    # Shutdown - ensure all services attempt to disconnect even if some fail
    errors = []

    try:
        await db.disconnect()
    except Exception as e:
        errors.append(e)

    try:
        await app.state.event_bus.disconnect()
    except Exception as e:
        errors.append(e)

    try:
        await app.state.state_manager.disconnect()
    except Exception as e:
        errors.append(e)

    # If any errors occurred during disconnect, raise the first one
    if errors:
        raise errors[0]


app = FastAPI(
    title="Pythmata",
    description="A Python-based BPMN workflow engine",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Import and include routers
app.include_router(process_router, prefix="/api")
