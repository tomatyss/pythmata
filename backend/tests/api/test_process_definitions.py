import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.routes import router
from pythmata.api.schemas import (
    ProcessDefinitionResponse,
    ProcessStats,
    ProcessVersionResponse,
)
from pythmata.models.process import (
    ProcessDefinition,
    ProcessInstance,
    ProcessStatus,
    ProcessVersion,
)
from tests.data.process_samples import SIMPLE_PROCESS_XML

# Setup test application
app = FastAPI()
app.include_router(router)


@pytest.fixture
async def process_definition(session: AsyncSession) -> ProcessDefinition:
    """Create a test process definition."""
    definition = ProcessDefinition(
        name="Test Process",
        bpmn_xml=SIMPLE_PROCESS_XML,
        version=1,
        variable_definitions=[],
    )
    session.add(definition)
    await session.commit()
    await session.refresh(definition)

    # Add initial version entry
    initial_version = ProcessVersion(
        process_id=definition.id,
        number=1,
        bpmn_xml=SIMPLE_PROCESS_XML,
        notes="Initial version",
    )
    session.add(initial_version)
    await session.commit()
    await session.refresh(definition)

    return definition


@pytest.fixture
async def process_with_instances(
    session: AsyncSession, process_definition: ProcessDefinition
) -> tuple[ProcessDefinition, int, int]:
    """Create a process definition with some instances."""
    # Create running instances
    running_count = 3
    for _ in range(running_count):
        instance = ProcessInstance(
            definition_id=process_definition.id,
            status=ProcessStatus.RUNNING,
        )
        session.add(instance)

    # Create completed instances
    completed_count = 2
    for _ in range(completed_count):
        instance = ProcessInstance(
            definition_id=process_definition.id,
            status=ProcessStatus.COMPLETED,
        )
        session.add(instance)

    await session.commit()
    return process_definition, running_count, running_count + completed_count


@pytest.fixture
async def process_with_mixed_status_instances(
    session: AsyncSession, process_definition: ProcessDefinition
) -> tuple[ProcessDefinition, dict[ProcessStatus, int]]:
    """Create a process definition with instances in various states."""
    status_counts = {
        ProcessStatus.RUNNING: 5,
        ProcessStatus.COMPLETED: 3,
        ProcessStatus.SUSPENDED: 2,
        ProcessStatus.ERROR: 1,
    }

    for status, count in status_counts.items():
        for _ in range(count):
            instance = ProcessInstance(
                definition_id=process_definition.id,
                status=status,
            )
            session.add(instance)

    await session.commit()
    return process_definition, status_counts


@pytest.fixture
async def process_with_multiple_versions(
    session: AsyncSession, process_definition: ProcessDefinition
) -> ProcessDefinition:
    """Create a process definition with multiple versions."""
    # Version 1 already created by process_definition fixture
    version2_xml = "<bpmn>Version 2</bpmn>"
    version3_xml = "<bpmn>Version 3</bpmn>"

    version2 = ProcessVersion(
        process_id=process_definition.id,
        number=2,
        bpmn_xml=version2_xml,
        notes="Second version",
        created_at=datetime.now(timezone.utc),
    )
    version3 = ProcessVersion(
        process_id=process_definition.id,
        number=3,
        bpmn_xml=version3_xml,
        notes="Third version",
        created_at=datetime.now(timezone.utc),
    )

    session.add_all([version2, version3])

    # Update the main process definition to reflect the latest version info
    process_definition.version = 3
    process_definition.bpmn_xml = version3_xml
    session.add(process_definition)

    await session.commit()
    await session.refresh(process_definition)

    # Eager load versions for assertions later
    await session.refresh(process_definition, attribute_names=["versions"])
    return process_definition


async def test_get_processes_serialization(
    async_client: AsyncClient,
    process_with_instances: tuple[ProcessDefinition, int, int],
):
    """Test that GET /processes properly serializes ProcessDefinition models."""
    process, active_count, total_count = process_with_instances

    response = await async_client.get("/processes")
    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data["items"]) == 1

    process_data = data["items"][0]
    assert process_data["id"] == str(process.id)
    assert process_data["name"] == process.name
    assert process_data["bpmn_xml"] == process.bpmn_xml
    assert process_data["version"] == process.version
    assert process_data["variable_definitions"] == process.variable_definitions
    assert process_data["active_instances"] == active_count
    assert process_data["total_instances"] == total_count

    # Verify no SQLAlchemy internal state is present
    assert "_sa_instance_state" not in process_data


async def test_get_single_process(
    async_client: AsyncClient,
    process_with_instances: tuple[ProcessDefinition, int, int],
):
    """Test that GET /processes/{id} returns correct process with instance counts."""
    process, active_count, total_count = process_with_instances

    response = await async_client.get(f"/processes/{process.id}")
    assert response.status_code == 200

    data = response.json()["data"]
    assert data["id"] == str(process.id)
    assert data["active_instances"] == active_count
    assert data["total_instances"] == total_count


async def test_get_single_process_not_found(async_client: AsyncClient):
    """Test that GET /processes/{id} returns 404 for non-existent process."""
    response = await async_client.get("/processes/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_instance_counting_with_mixed_status(
    async_client: AsyncClient,
    process_with_mixed_status_instances: tuple[
        ProcessDefinition, dict[ProcessStatus, int]
    ],
):
    """Test that instance counting correctly handles different process statuses."""
    process, status_counts = process_with_mixed_status_instances

    response = await async_client.get(f"/processes/{process.id}")
    assert response.status_code == 200

    data = response.json()["data"]
    assert data["active_instances"] == status_counts[ProcessStatus.RUNNING]
    assert data["total_instances"] == sum(status_counts.values())


async def test_process_definition_response_validation():
    """Test that ProcessDefinitionResponse properly validates its fields."""
    # Test with missing required fields
    with pytest.raises(Exception) as exc_info:
        ProcessDefinitionResponse.model_validate({})
    assert "id" in str(exc_info.value)

    # Test with invalid field types
    with pytest.raises(Exception) as exc_info:
        ProcessDefinitionResponse.model_validate(
            {
                "id": "not-a-uuid",
                "name": "Test",
                "bpmn_xml": "<xml></xml>",
                "version": "not-an-int",
                "variable_definitions": [],
                "created_at": "not-a-datetime",
                "updated_at": "not-a-datetime",
                "active_instances": "not-an-int",
                "total_instances": "not-an-int",
            }
        )
    assert any(
        field in str(exc_info.value)
        for field in ["id", "version", "active_instances", "total_instances"]
    )


async def test_get_processes_with_no_instances(
    async_client: AsyncClient,
    process_definition: ProcessDefinition,
):
    """Test GET /processes when process has no instances."""
    response = await async_client.get("/processes")
    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data["items"]) == 1

    process_data = data["items"][0]
    assert process_data["active_instances"] == 0
    assert process_data["total_instances"] == 0


async def test_process_status_enum_serialization():
    """Test that ProcessStatus enum can be properly serialized in responses."""
    # Test schema generation
    type_adapter = TypeAdapter(ProcessStatus)
    schema = type_adapter.json_schema()

    # Verify schema contains enum values
    assert schema["enum"] == ["RUNNING", "COMPLETED", "SUSPENDED", "ERROR"]
    assert schema["type"] == "string"

    # Test serialization in complex structures
    stats = ProcessStats(
        total_instances=10,
        status_counts={
            "RUNNING": 5,
            "COMPLETED": 3,
            "ERROR": 2,
        },
        average_completion_time=60.0,
        error_rate=0.2,
        active_instances=5,
    )

    # Verify complex structure serialization works
    json_str = stats.model_dump_json()
    data = json.loads(json_str)
    assert "RUNNING" in data["status_counts"]
    assert data["status_counts"]["RUNNING"] == 5


async def test_multiple_processes_instance_counting(
    async_client: AsyncClient, session: AsyncSession
):
    """Test that instance counting works correctly across multiple processes."""
    # Create two processes
    process1 = ProcessDefinition(
        name="Process 1",
        bpmn_xml=SIMPLE_PROCESS_XML,
        version=1,
    )
    process2 = ProcessDefinition(
        name="Process 2",
        bpmn_xml=SIMPLE_PROCESS_XML,
        version=1,
    )
    session.add_all([process1, process2])
    await session.commit()

    # Add instances to process1
    for _ in range(3):
        instance = ProcessInstance(
            definition_id=process1.id,
            status=ProcessStatus.RUNNING,
        )
        session.add(instance)

    # Add instances to process2
    for _ in range(2):
        instance = ProcessInstance(
            definition_id=process2.id,
            status=ProcessStatus.RUNNING,
        )
        session.add(instance)
    for _ in range(2):
        instance = ProcessInstance(
            definition_id=process2.id,
            status=ProcessStatus.COMPLETED,
        )
        session.add(instance)

    await session.commit()

    # Test individual process endpoints
    response1 = await async_client.get(f"/processes/{process1.id}")
    data1 = response1.json()["data"]
    assert data1["active_instances"] == 3
    assert data1["total_instances"] == 3

    response2 = await async_client.get(f"/processes/{process2.id}")
    data2 = response2.json()["data"]
    assert data2["active_instances"] == 2
    assert data2["total_instances"] == 4

    # Test list endpoint
    response_list = await async_client.get("/processes")
    data_list = response_list.json()["data"]
    assert len(data_list["items"]) == 2

    # Verify processes are ordered by created_at desc
    processes = data_list["items"]
    assert processes[0]["name"] == "Process 2"  # Created later
    assert processes[1]["name"] == "Process 1"  # Created first


# --- Process Version Tests ---


async def test_get_process_versions(
    async_client: AsyncClient,
    process_with_multiple_versions: ProcessDefinition,
):
    """Test GET /processes/{process_id}/versions endpoint."""
    process = process_with_multiple_versions
    process_id = process.id

    response = await async_client.get(f"/processes/{process_id}/versions")
    assert response.status_code == 200

    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) == 3

    # Validate structure using ProcessVersionResponse schema
    validated_versions = TypeAdapter(list[ProcessVersionResponse]).validate_python(data)

    # Versions should be ordered by number descending
    assert validated_versions[0].number == 3
    assert validated_versions[1].number == 2
    assert validated_versions[2].number == 1

    # Check details of the latest version
    assert validated_versions[0].process_id == process_id
    assert validated_versions[0].bpmn_xml == "<bpmn>Version 3</bpmn>"
    assert validated_versions[0].notes == "Third version"

    # Check details of the first version
    assert validated_versions[2].process_id == process_id
    assert validated_versions[2].bpmn_xml == SIMPLE_PROCESS_XML
    assert validated_versions[2].notes == "Initial version"


async def test_get_process_versions_not_found(async_client: AsyncClient):
    """Test GET /processes/{process_id}/versions for non-existent process."""
    non_existent_id = uuid4()
    response = await async_client.get(f"/processes/{non_existent_id}/versions")
    assert response.status_code == 404
    assert "Process definition not found" in response.json()["detail"]


async def test_create_process_creates_initial_version(
    async_client: AsyncClient, session: AsyncSession
):
    """Test that POST /processes creates an initial ProcessVersion entry."""
    process_name = "New Process with Version"
    process_xml = "<bpmn>Initial XML</bpmn>"
    payload = {
        "name": process_name,
        "bpmn_xml": process_xml,
        "variable_definitions": [],
    }

    response = await async_client.post("/processes", json=payload)
    assert response.status_code == 200

    created_process_data = response.json()["data"]
    process_id = created_process_data["id"]

    # Verify the ProcessDefinition was created correctly
    assert created_process_data["name"] == process_name
    assert created_process_data["version"] == 1
    assert created_process_data["bpmn_xml"] == process_xml

    # Now verify the ProcessVersion was created in the database
    result = await session.execute(
        select(ProcessVersion).filter(ProcessVersion.process_id == process_id)
    )
    versions = result.scalars().all()

    assert len(versions) == 1
    initial_version = versions[0]
    assert initial_version.number == 1
    assert initial_version.bpmn_xml == process_xml
    assert initial_version.notes == "Initial version created."
    assert str(initial_version.process_id) == process_id


async def test_get_process_versions_single_version(
    async_client: AsyncClient, process_definition: ProcessDefinition
):
    """Test GET /processes/{process_id}/versions when only one version exists."""
    process_id = process_definition.id

    response = await async_client.get(f"/processes/{process_id}/versions")
    assert response.status_code == 200

    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) == 1

    validated_version = ProcessVersionResponse.model_validate(data[0])
    assert validated_version.number == 1
    assert validated_version.process_id == process_id
    assert validated_version.bpmn_xml == SIMPLE_PROCESS_XML
    assert validated_version.notes == "Initial version"