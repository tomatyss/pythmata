from fastapi import APIRouter

from pythmata.api.routes.llm import router as llm_router
from pythmata.api.routes.process_definitions import router as process_definitions_router
from pythmata.api.routes.process_instances import router as process_instances_router
from pythmata.api.routes.scripts import router as scripts_router
from pythmata.api.routes.services import router as services_router
from pythmata.api.routes.stats import router as stats_router

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(process_definitions_router)
router.include_router(process_instances_router)
router.include_router(scripts_router)
router.include_router(services_router)
router.include_router(stats_router)
router.include_router(llm_router)
