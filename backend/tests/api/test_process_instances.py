import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.routes import router
from pythmata.models.process import (
    ProcessDefinition,
    ProcessInstance,
    ProcessStatus,
    Script,
)

# Setup test application
app = FastAPI()
app.include_router(router)


@pytest.fixture
async def process_definition(session: AsyncSession) -> ProcessDefinition:
    """Create a test process definition."""
    definition = ProcessDefinition(
        name="Test Process",
        bpmn_xml="<xml></xml>",
        version=1,
    )
    session.add(definition)
    await session.commit()
    await session.refresh(definition)
    return definition


@pytest.fixture
async def process_instance(
    session: AsyncSession, process_definition: ProcessDefinition
) -> ProcessInstance:
    """Create a test process instance."""
    instance = ProcessInstance(
        definition_id=process_definition.id,
        status=ProcessStatus.RUNNING,
    )
    session.add(instance)
    await session.commit()
    await session.refresh(instance)
    return instance


@pytest.fixture
async def script(
    session: AsyncSession, process_definition: ProcessDefinition
) -> Script:
    """Create a test script."""
    script = Script(
        process_def_id=process_definition.id,
        node_id="task_1",
        content="print('hello')",
        version=1,
    )
    session.add(script)
    await session.commit()
    await session.refresh(script)
    return script


async def test_list_instances_pagination(
    async_client: AsyncClient,
    session: AsyncSession,
    process_definition: ProcessDefinition,
):
    """Test GET /instances pagination."""
    # Create multiple instances
    for _ in range(15):
        instance = ProcessInstance(
            definition_id=process_definition.id,
            status=ProcessStatus.RUNNING,
        )
        session.add(instance)
    await session.commit()

    # Test default pagination
    response = await async_client.get("/instances")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["items"]) == 10  # Default page size
    assert data["total"] == 15
    assert data["page"] == 1
    assert data["pageSize"] == 10
    assert data["totalPages"] == 2

    # Test custom page size
    response = await async_client.get("/instances?page_size=5")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["items"]) == 5
    assert data["pageSize"] == 5
    assert data["totalPages"] == 3


async def test_list_instances_filtering(
    async_client: AsyncClient,
    session: AsyncSession,
    process_definition: ProcessDefinition,
):
    """Test GET /instances filtering."""
    # Create instances with different statuses
    statuses = [
        ProcessStatus.RUNNING,
        ProcessStatus.COMPLETED,
        ProcessStatus.SUSPENDED,
        ProcessStatus.ERROR
    ]
    # Create instances with timestamps after a reference date
    reference_date = datetime.now(timezone.utc).replace(microsecond=0)
    for status in statuses:
        instance = ProcessInstance(
            definition_id=process_definition.id,
            status=status,
            start_time=reference_date + timedelta(hours=1),  # Future time to ensure it's after reference
        )
        session.add(instance)
    await session.commit()

    # Test status filter
    response = await async_client.get(
        f"/instances?status=RUNNING"  # Use string value instead of enum
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == ProcessStatus.RUNNING

    # Test date range filter using the reference date
    from urllib.parse import quote
    response = await async_client.get(
        f"/instances?start_date={quote(reference_date.isoformat())}"
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["items"]) == 4  # All instances


async def test_get_instance(
    async_client: AsyncClient,
    process_instance: ProcessInstance,
):
    """Test GET /instances/{id}."""
    response = await async_client.get(f"/instances/{process_instance.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(process_instance.id)
    assert data["status"] == ProcessStatus.RUNNING

    # Test non-existent instance
    response = await async_client.get(f"/instances/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_create_instance(
    async_client: AsyncClient,
    process_definition: ProcessDefinition,
):
    """Test POST /instances."""
    response = await async_client.post(
        "/instances",
        json={
            "definition_id": str(process_definition.id),
            "variables": {"key": "value"},
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["definition_id"] == str(process_definition.id)
    assert data["status"] == ProcessStatus.RUNNING

    # Test invalid process definition
    response = await async_client.post(
        "/instances",
        json={"definition_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404


async def test_instance_state_management(
    async_client: AsyncClient,
    session: AsyncSession,
    process_instance: ProcessInstance,
):
    """Test instance suspension and resumption."""
    # Test suspension
    response = await async_client.post(
        f"/instances/{process_instance.id}/suspend"
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == ProcessStatus.SUSPENDED

    # Test resumption
    response = await async_client.post(
        f"/instances/{process_instance.id}/resume"
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == ProcessStatus.RUNNING

    # Test invalid state transitions
    process_instance.status = ProcessStatus.COMPLETED
    await session.commit()  # Commit the status change
    response = await async_client.post(
        f"/instances/{process_instance.id}/suspend"
    )
    assert response.status_code == 400


async def test_get_statistics(
    async_client: AsyncClient,
    session: AsyncSession,
    process_definition: ProcessDefinition,
):
    """Test GET /stats."""
    # Create instances with different statuses
    now = datetime.now(timezone.utc)
    statuses = {
        ProcessStatus.RUNNING: 2,
        ProcessStatus.COMPLETED: 3,
        ProcessStatus.ERROR: 1,
    }
    for status, count in statuses.items():
        for _ in range(count):
            instance = ProcessInstance(
                definition_id=process_definition.id,
                status=status,
                start_time=now - timedelta(hours=1),
                end_time=now if status == ProcessStatus.COMPLETED else None,
            )
            session.add(instance)
    await session.commit()

    response = await async_client.get("/stats")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_instances"] == 6
    assert data["status_counts"] == {
        "RUNNING": 2,
        "COMPLETED": 3,
        "ERROR": 1,
    }
    assert data["active_instances"] == 2
    assert data["error_rate"] == pytest.approx(16.67, rel=0.01)  # 1/6 * 100
    assert data["average_completion_time"] is not None


async def test_script_management(
    async_client: AsyncClient,
    process_definition: ProcessDefinition,
    script: Script,
):
    """Test script management endpoints."""
    # Test list scripts
    response = await async_client.get(
        f"/processes/{process_definition.id}/scripts"
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["node_id"] == "task_1"

    # Test get script
    response = await async_client.get(
        f"/processes/{process_definition.id}/scripts/task_1"
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["content"] == "print('hello')"

    # Test update script
    response = await async_client.put(
        f"/processes/{process_definition.id}/scripts/task_1",
        json={"content": "print('updated')", "version": 2},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["content"] == "print('updated')"
    assert data["version"] == 2

    # Test create new script
    response = await async_client.put(
        f"/processes/{process_definition.id}/scripts/task_2",
        json={"content": "print('new')", "version": 1},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["node_id"] == "task_2"
    assert data["content"] == "print('new')"
