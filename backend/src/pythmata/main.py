"""Main FastAPI application module."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from pythmata.api.routes import router as process_router
from pythmata.api.websocket.routes import router as websocket_router
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
    """
    Handle process.started event by initializing and executing a new process instance.

    This function follows BPMN lifecycle management best practices:
    1. Process Definition Loading
    2. Instance Initialization
    3. Token Creation and Management
    4. Process Execution

    Args:
        data: Dictionary containing instance_id and definition_id
    """
    try:
        instance_id = data["instance_id"]
        definition_id = data["definition_id"]
        logger.info(f"Handling process.started event for instance {instance_id}")

        # Get required services
        logger.info("[ProcessStarted] Initializing required services")
        try:
            settings = Settings()
            logger.info("[ProcessStarted] Settings initialized successfully")
        except Exception as e:
            logger.error(f"[ProcessStarted] Failed to initialize settings: {str(e)}")
            logger.error(
                "[ProcessStarted] Please check configuration files and environment variables"
            )
            raise

        state_manager = StateManager(settings)
        logger.info("[ProcessStarted] State manager initialized")
        db = get_db()

        # Connect to state manager only since database is managed by FastAPI lifespan
        await state_manager.connect()
        try:
            # 1. Load Process Definition
            async with db.session() as session:
                logger.info("Loading process definition...")
                stmt = select(ProcessDefinitionModel).filter(
                    ProcessDefinitionModel.id == definition_id
                )
                logger.debug(f"Executing query: {stmt}")
                result = await session.execute(stmt)
                logger.debug(f"Query result type: {type(result)}")

                definition = result.scalar_one_or_none()
                logger.debug(
                    f"Definition type: {type(definition)}, value: {definition}"
                )

                if not definition:
                    logger.error(f"Process definition {definition_id} not found")
                    return
                logger.info(f"Definition loaded successfully: {definition_id}")

                # 2. Parse and Validate BPMN
                try:
                    parser = BPMNParser()
                    logger.debug(
                        f"Definition bpmn_xml type: {type(definition.bpmn_xml)}"
                    )
                    logger.debug(f"Definition bpmn_xml value: {definition.bpmn_xml}")
                    process_graph = parser.parse(definition.bpmn_xml)
                    logger.debug(f"Process graph after parsing: {process_graph}")
                    logger.info("BPMN XML parsed successfully")
                except Exception as e:
                    logger.error(f"Failed to parse BPMN XML: {e}")
                    return

                # Validate start event existence and type
                start_event = next(
                    (
                        node
                        for node in process_graph["nodes"]
                        if hasattr(node, "event_type") and node.event_type == "start"
                    ),
                    None,
                )
                if not start_event:
                    logger.error("No start event found in process definition")
                    return
                logger.info(f"Validated start event: {start_event.id}")

            # 3. Initialize Process Instance
            async with db.session() as session:
                # Create instance manager with proper initialization
                instance_manager = ProcessInstanceManager(session, None, state_manager)
                executor = ProcessExecutor(
                    state_manager=state_manager, instance_manager=instance_manager
                )
                instance_manager.executor = executor

                # 4. Check for existing tokens
                logger.debug("Checking for existing tokens...")
                existing_tokens = await state_manager.get_token_positions(instance_id)
                logger.debug(
                    f"Token check result type: {type(existing_tokens)}, value: {existing_tokens}"
                )

                if existing_tokens is not None and len(existing_tokens) > 0:
                    logger.info(
                        f"Found existing tokens for instance {instance_id}: {existing_tokens}"
                    )
                    logger.debug("Skipping token creation due to existing tokens")
                else:
                    logger.debug("No existing tokens found, creating initial token")
                    # Create initial token only if none exist
                    initial_token = await executor.create_initial_token(
                        instance_id, start_event.id
                    )
                    logger.info(
                        f"Created initial token: {initial_token.id} at {start_event.id}"
                    )

                # 5. Execute Process (will use existing tokens if any)
                logger.debug(
                    f"Preparing to execute process with graph: {process_graph}"
                )
                logger.info(f"Starting process execution for instance {instance_id}")
                await executor.execute_process(instance_id, process_graph)
                logger.info(f"Process {instance_id} execution completed successfully")

        finally:
            await state_manager.disconnect()

    except Exception as e:
        logger.error(f"Error handling process.started event: {e}", exc_info=True)

        # Try to set error state and clean up if possible
        try:
            logger.info("[ErrorCleanup] Attempting to initialize services for cleanup")
            try:
                settings = Settings()
                logger.info("[ErrorCleanup] Settings initialized for cleanup")
            except Exception as e:
                logger.error(
                    f"[ErrorCleanup] Failed to initialize settings for cleanup: {str(e)}"
                )
                raise

            state_manager = StateManager(settings)
            logger.info("[ErrorCleanup] State manager initialized for cleanup")
            await state_manager.connect()

            async with get_db().session() as session:
                instance_manager = ProcessInstanceManager(session, None, state_manager)
                await instance_manager.handle_error(instance_id, e)
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")

        # Re-raise to ensure proper error handling at higher levels
        raise


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

# Add CORS middleware with WebSocket support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_websockets=True,  # Enable WebSocket support
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Import and include routers
app.include_router(process_router, prefix="/api")
app.include_router(websocket_router, prefix="/api/ws")  # Mount WebSocket routes
