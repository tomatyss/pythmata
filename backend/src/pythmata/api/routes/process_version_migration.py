from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from pythmata.api.dependencies import get_session
from pythmata.api.schemas import ApiResponse, ProcessMigrationRequest, ProcessMigrationResponse
from pythmata.models.process import ProcessDefinition as ProcessDefinitionModel
from pythmata.models.process import ProcessInstance as ProcessInstanceModel
from pythmata.utils.logger import get_logger, log_error

logger = get_logger(__name__)

router = APIRouter(prefix="/migrations", tags=["migrations"])


@router.post("", response_model=ApiResponse[ProcessMigrationResponse])
@log_error(logger)
async def migrate_process_version(
    data: ProcessMigrationRequest = Body(...),
    session: AsyncSession = Depends(get_session),
):
    """
    Migrate instances of a process definition from one version to another.

    Args:
        data: Request body containing process_id, source_version, and target_version.
        session: Database session dependency.

    Returns:
        Response containing the migration summary.
    """
    try:
        # Validate the source and target process definitions
        source_process = await get_process_definition(
            session, data.process_id, data.source_version
        )
        target_process = await get_process_definition(
            session, data.process_id, data.target_version
        )

        if not source_process:
            raise HTTPException(
                status_code=404, detail="Source process version not found"
            )
        if not target_process:
            raise HTTPException(
                status_code=404, detail="Target process version not found"
            )

        # Fetch instances of the source process
        instances = await get_instances_by_version(
            session, data.process_id, data.source_version
        )

        if not instances:
            return {"data": {"migrated_instances": 0, "failed_instances": 0}}

        # Migrate each instance to the target version
        migrated_count = 0
        failed_count = 0
        for instance in instances:
            try:
                await migrate_instance(
                    session, instance, source_process, target_process
                )
                migrated_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to migrate instance {instance.id}: {str(e)}",
                    exc_info=True,
                )
                failed_count += 1

        return {
            "data": {
                "migrated_instances": migrated_count,
                "failed_instances": failed_count,
            }
        }
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def get_process_definition(
    session: AsyncSession, process_id: str, version: int
) -> Optional[ProcessDefinitionModel]:
    """
    Fetch a specific process definition by ID and version.

    Args:
        session: Database session.
        process_id: ID of the process.
        version: Version of the process.

    Returns:
        The process definition if found, else None.
    """
    result = await session.execute(
        select(ProcessDefinitionModel).filter(
            ProcessDefinitionModel.id == process_id,
            ProcessDefinitionModel.version == version,
        )
    )
    return result.scalar_one_or_none()


async def get_instances_by_version(
    session: AsyncSession, process_id: str, version: int
) -> List[ProcessInstanceModel]:
    """
    Fetch all instances of a specific process definition version.

    Args:
        session: Database session.
        process_id: ID of the process.
        version: Version of the process.

    Returns:
        List of process instances.
    """
    result = await session.execute(
        select(ProcessInstanceModel).filter(
            ProcessInstanceModel.definition_id == process_id,
            ProcessInstanceModel.version == version,
        )
    )
    return result.scalars().all()


async def migrate_instance(
    session: AsyncSession,
    instance: ProcessInstanceModel,
    source_process: ProcessDefinitionModel,
    target_process: ProcessDefinitionModel,
):
    """
    Migrate a single instance from the source process version to the target version.

    Args:
        session: Database session.
        instance: The process instance to be migrated.
        source_process: The source process definition.
        target_process: The target process definition.

    Returns:
        None
    """
    # Perform variable mapping if schema changes exist (if required)
    instance.variables = migrate_variables(
        instance.variables, source_process, target_process
    )

    # Update the instance to point to the target process version
    await session.execute(
        update(ProcessInstanceModel)
        .where(ProcessInstanceModel.id == instance.id)
        .values(
            definition_id=target_process.id,
            version=target_process.version,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await session.commit()


def migrate_variables(
    variables: dict, source_process: ProcessDefinitionModel, target_process: ProcessDefinitionModel
) -> dict:
    """
    Perform variable mapping between the source process schema and the target process schema.

    Args:
        variables: Current instance variables.
        source_process: The source process definition.
        target_process: The target process definition.

    Returns:
        Updated variables after mapping.
    """
    # For simplicity, assume variables remain unchanged
    # Implement custom variable mapping logic as needed
    return variables