"""
Pythmata FastAPI application entry point.

This module initializes the FastAPI application, sets up middleware,
and defines the API endpoints. It serves as the main entry point for the
Pythmata workflow engine.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pythmata.api.routes import router as process_router
from pythmata.core.utils import lifespan
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


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
