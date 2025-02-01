from pythmata.api.routes import router as process_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pythmata.core.config import Settings
from pythmata.core.events import EventBus
from pythmata.core.state import StateManager
from pythmata.core.database import init_db, get_db

app = FastAPI(
    title="Pythmata",
    description="A Python-based BPMN workflow engine",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    settings = Settings()
    app.state.event_bus = EventBus(settings)
    app.state.state_manager = StateManager(settings)

    # Initialize services
    init_db(settings)

    await app.state.event_bus.connect()
    await app.state.state_manager.connect()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    db = get_db()
    await db.close()  # Close database connection
    await app.state.event_bus.disconnect()
    await app.state.state_manager.disconnect()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

# Import and include routers
app.include_router(process_router, prefix="/api")
