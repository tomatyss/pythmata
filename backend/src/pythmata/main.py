from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from pythmata.api.routes import router as process_router
from pythmata.core.bpmn.parser import BPMNParser
from pythmata.core.config import Settings
from pythmata.core.database import get_db, init_db
from pythmata.core.engine.executor import ProcessExecutor
from pythmata.core.engine.instance import ProcessInstanceManager
from pythmata.core.events import EventBus
from pythmata.core.state import StateManager
from pythmata.models.process import ProcessDefinition as ProcessDefinitionModel
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


async def handle_process_started(data: dict) -> None:
    """Handle process.started event."""
    try:
        instance_id = data["instance_id"]
        definition_id = data["definition_id"]
        logger.info(f"Handling process.started event for instance {instance_id}")

        # Get required services
        settings = Settings()
        state_manager = StateManager(settings)
        db = get_db()

        # Connect to state manager only since database is managed by FastAPI lifespan
        await state_manager.connect()
        try:
            # Get process definition from database
            async with db.session() as session:
                logger.info("Executing database query...")
                stmt = select(ProcessDefinitionModel).filter(
                    ProcessDefinitionModel.id == definition_id
                )
                result = await session.execute(stmt)
                definition = result.scalar_one_or_none()  # No await needed here
                logger.info(f"Definition found: {definition is not None}")
            if not definition:
                raise ValueError(f"Process definition {definition_id} not found")

            # Parse BPMN XML to process graph
            parser = BPMNParser()
            process_graph = parser.parse(definition.bpmn_xml)
            logger.info("BPMN XML parsed successfully")

            # Find start event
            start_event = next(
                (
                    node
                    for node in process_graph["nodes"]
                    if hasattr(node, "event_type") and node.event_type == "start"
                ),
                None,
            )
            if not start_event:
                raise ValueError("No start event found in process definition")
            logger.info(f"Found start event: {start_event.id}")

            # Create instance manager and executor
            async with db.session() as session:
                instance_manager = ProcessInstanceManager(session, None, state_manager)
                executor = ProcessExecutor(state_manager=state_manager, instance_manager=instance_manager)
                # Set executor on instance manager after creation to avoid circular reference
                instance_manager.executor = executor
                
                logger.info(f"Starting process execution for instance {instance_id}")
                await executor.execute_process(instance_id, process_graph)
                logger.info(f"Process {instance_id} execution completed")

        finally:
            await state_manager.disconnect()

    except Exception as e:
        logger.error(f"Error handling process.started event: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    settings = Settings()
    app.state.event_bus = EventBus(settings)
    app.state.state_manager = StateManager(settings)

    # Initialize and connect services
    logger.info("Initializing database...")
    init_db(settings)
    db = get_db()
    logger.info("Connecting to database...")
    await db.connect()  # Establish database connection
    logger.info("Database connected successfully")

    logger.info("Connecting to event bus...")
    await app.state.event_bus.connect()
    logger.info("Event bus connected successfully")

    logger.info("Connecting to state manager...")
    await app.state.state_manager.connect()
    logger.info("State manager connected successfully")

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

    logger.info("Shutting down services...")
    try:
        logger.info("Disconnecting database...")
        await db.disconnect()
        logger.info("Database disconnected successfully")
    except Exception as e:
        logger.error(f"Error disconnecting database: {e}")
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
