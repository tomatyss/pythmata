import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.routes import router
from pythmata.models.process import ProcessDefinition, ProcessInstance, ProcessStatus
from tests.data.process_samples import SIMPLE_PROCESS_XML

# Setup test application
app = FastAPI()
app.include_router(router)


@pytest.fixture
async def process_definition(session: AsyncSession) -> ProcessDefinition:
    """Create a test process definition."""
    definition = ProcessDefinition(
        name="Delete Test Process",
        bpmn_xml=SIMPLE_PROCESS_XML,
        version=1,
        variable_definitions=[],
    )
    session.add(definition)
    await session.commit()
    await session.refresh(definition)
    return definition


@pytest.fixture
async def process_with_instances(
    session: AsyncSession, process_definition: ProcessDefinition
) -> tuple[ProcessDefinition, int]:
    """Create a process definition with some instances."""
    # Create instances
    instance_count = 3
    for _ in range(instance_count):
        instance = ProcessInstance(
            definition_id=process_definition.id,
            status=ProcessStatus.COMPLETED,
        )
        session.add(instance)

    await session.commit()
    return process_definition, instance_count


async def test_delete_process_definition(
    async_client: AsyncClient, process_definition: ProcessDefinition, session: AsyncSession
):
    """Test that DELETE /processes/{id} successfully deletes a process definition."""
    # Verify process exists before deletion
    result = await session.get(ProcessDefinition, process_definition.id)
    assert result is not None
    
    # Delete the process
    response = await async_client.delete(f"/processes/{process_definition.id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Process deleted successfully"}
    
    # Verify process was deleted from database
    result = await session.get(ProcessDefinition, process_definition.id)
    assert result is None


async def test_delete_nonexistent_process(async_client: AsyncClient):
    """Test that DELETE /processes/{id} returns 404 for non-existent process."""
    response = await async_client.delete("/processes/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert "Process not found" in response.json()["detail"]


async def test_delete_process_cascade_deletes_instances(
    async_client: AsyncClient, process_with_instances: tuple[ProcessDefinition, int], session: AsyncSession
):
    """Test that deleting a process definition also deletes its instances."""
    process, instance_count = process_with_instances
    
    # Verify instances exist before deletion
    instances_query = await session.execute(
        "SELECT COUNT(*) FROM process_instances WHERE definition_id = :def_id",
        {"def_id": process.id}
    )
    assert instances_query.scalar_one() == instance_count
    
    # Delete the process
    response = await async_client.delete(f"/processes/{process.id}")
    assert response.status_code == 200
    
    # Verify instances were also deleted
    instances_query = await session.execute(
        "SELECT COUNT(*) FROM process_instances WHERE definition_id = :def_id",
        {"def_id": process.id}
    )
    assert instances_query.scalar_one() == 0
