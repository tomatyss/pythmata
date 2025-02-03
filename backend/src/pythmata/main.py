from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pythmata.api.routes import router as process_router
from pythmata.core.config import Settings
from pythmata.core.database import get_db, init_db
from pythmata.core.events import EventBus
from pythmata.core.state import StateManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    settings = Settings()
    app.state.event_bus = EventBus(settings)
    app.state.state_manager = StateManager(settings)

    # Initialize services
    init_db(settings)

    await app.state.event_bus.connect()
    await app.state.state_manager.connect()

    yield

    # Shutdown
    db = get_db()
    await db.close()  # Close database connection
    await app.state.event_bus.disconnect()
    await app.state.state_manager.disconnect()


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
