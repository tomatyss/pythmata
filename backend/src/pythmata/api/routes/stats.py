from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.schemas import ApiResponse, ProcessStats
from pythmata.api.dependencies import get_session
from pythmata.models.process import ProcessInstance as ProcessInstanceModel
from pythmata.models.process import ProcessStatus
from pythmata.utils.logger import get_logger

router = APIRouter(tags=["stats"])
logger = get_logger(__name__)


@router.get("/stats", response_model=ApiResponse[ProcessStats])
async def get_statistics(session: AsyncSession = Depends(get_session)):
    """Get process statistics."""
    try:
        # Get total instances
        total_query = select(func.count()).select_from(ProcessInstanceModel)
        total_instances = await session.scalar(total_query)

        # Get status counts
        status_query = select(
            ProcessInstanceModel.status, func.count(ProcessInstanceModel.id)
        ).group_by(ProcessInstanceModel.status)
        status_result = await session.execute(status_query)
        status_counts = dict(status_result.all())

        # Get average completion time for completed instances
        completion_query = select(
            func.avg(ProcessInstanceModel.end_time - ProcessInstanceModel.start_time)
        ).where(ProcessInstanceModel.status == ProcessStatus.COMPLETED)
        avg_completion_time = await session.scalar(completion_query)
        avg_completion_seconds = (
            avg_completion_time.total_seconds()
            if avg_completion_time is not None
            else None
        )

        # Calculate error rate
        error_count = status_counts.get(ProcessStatus.ERROR, 0)
        error_rate = (error_count / total_instances * 100) if total_instances > 0 else 0

        # Get active instances count
        active_instances = status_counts.get(ProcessStatus.RUNNING, 0)

        return {
            "data": ProcessStats(
                total_instances=total_instances,
                status_counts=status_counts,
                average_completion_time=avg_completion_seconds,
                error_rate=error_rate,
                active_instances=active_instances,
            )
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
