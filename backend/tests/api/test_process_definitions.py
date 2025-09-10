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
    """Test GET /processes/{process_id}/versions endpoint with pagination."""
    process = process_with_multiple_versions
    process_id = process.id
    total_versions = 3 # Based on the fixture

    # Test fetching the first page with default page size
    response = await async_client.get(f"/processes/{process_id}/versions?page=1&pageSize=10")
    assert response.status_code == 200

    data = response.json()["data"]
    assert isinstance(data, dict)
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "pageSize" in data
    assert "totalPages" in data

    assert data["total"] == total_versions
    assert data["page"] == 1
    assert data["pageSize"] == 10
    assert data["totalPages"] == 1 # 3 items / 10 per page = 1 page
    assert len(data["items"]) == total_versions # All versions fit on the first page

    # Validate structure using ProcessVersionResponse schema
    validated_versions = TypeAdapter(list[ProcessVersionResponse]).validate_python(data["items"])

    # Versions should be ordered by number descending
    assert validated_versions[0].number == 3

    # Check details of the first version
    assert validated_versions[2].process_id == process_id
    assert validated_versions[2].bpmn_xml == SIMPLE_PROCESS_XML
    assert validated_versions[2].notes == "Initial version"

    # Test fetching with a smaller page size (page 1)
    response_page1_size2 = await async_client.get(f"/processes/{process_id}/versions?page=1&pageSize=2")
    assert response_page1_size2.status_code == 200
    data_page1_size2 = response_page1_size2.json()["data"]
    assert data_page1_size2["total"] == total_versions
    assert data_page1_size2["page"] == 1
    assert data_page1_size2["pageSize"] == 2
    assert data_page1_size2["totalPages"] == 2 # 3 items / 2 per page = 2 pages
    assert len(data_page1_size2["items"]) == 2
    assert data_page1_size2["items"][0]["number"] == 3
    assert data_page1_size2["items"][1]["number"] == 2

    # Test fetching with a smaller page size (page 2)
    response_page2_size2 = await async_client.get(f"/processes/{process_id}/versions?page=2&pageSize=2")
    assert response_page2_size2.status_code == 200
    data_page2_size2 = response_page2_size2.json()["data"]
    assert data_page2_size2["total"] == total_versions
    assert data_page2_size2["page"] == 2
    assert data_page2_size2["pageSize"] == 2
    assert data_page2_size2["totalPages"] == 2
    assert len(data_page2_size2["items"]) == 1 # Remaining item
    assert data_page2_size2["items"][0]["number"] == 1


async def test_get_process_versions_invalid_pagination(async_client: AsyncClient, process_with_multiple_versions: ProcessDefinition):
    """Test GET /processes/{process_id}/versions with invalid pagination params."""
    process = process_with_multiple_versions
    process_id = process.id

    # Test invalid page number (less than 1)
    response_invalid_page = await async_client.get(f"/processes/{process_id}/versions?page=0&pageSize=5")
    assert response_invalid_page.status_code == 422 # Unprocessable Entity for validation errors

    # Test invalid page size (less than 1)
    response_invalid_size_small = await async_client.get(f"/processes/{process_id}/versions?page=1&pageSize=0")
    assert response_invalid_size_small.status_code == 422

    # Test invalid page size (greater than max)
    response_invalid_size_large = await async_client.get(f"/processes/{process_id}/versions?page=1&pageSize=200")
    assert response_invalid_size_large.status_code == 422


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
    assert isinstance(data, dict)
    assert "items" in data
    assert data["total"] == 1
    assert data["page"] == 1
    assert len(data["items"]) == 1

    validated_version = ProcessVersionResponse.model_validate(data["items"][0])
    assert validated_version.number == 1
    assert validated_version.process_id == process_id
    assert validated_version.bpmn_xml == SIMPLE_PROCESS_XML
    assert validated_version.notes == "Initial version"


async def test_update_process_creates_new_version(
    async_client: AsyncClient,
    process_definition: ProcessDefinition,
    session: AsyncSession,
):
    """Test that updating BPMN XML creates a new version."""
    process_id = process_definition.id
    new_xml = "<bpmn>Updated XML</bpmn>"
    update_notes = "Updated process flow"

    # Update the process with new BPMN XML
    response = await async_client.put(
        f"/processes/{process_id}",
        json={
            "bpmn_xml": new_xml,
            "notes": update_notes,
        },
    )
    assert response.status_code == 200

    # Verify process definition was updated
    data = response.json()["data"]
    assert data["bpmn_xml"] == new_xml
    assert data["version"] == 2  # Version should increment

    # Verify new version was created
    versions_response = await async_client.get(f"/processes/{process_id}/versions")
    assert versions_response.status_code == 200
    versions_data = versions_response.json()["data"]
    assert versions_data["total"] == 2
    assert len(versions_data["items"]) == 2
    versions = versions_data["items"]

    # Latest version should be first
    latest_version = versions[0]
    assert latest_version["number"] == 2
    assert latest_version["bpmn_xml"] == new_xml
    assert latest_version["notes"] == update_notes


async def test_update_process_without_xml_change(
    async_client: AsyncClient,
    process_definition: ProcessDefinition,
    session: AsyncSession,
):
    """Test that updating fields other than BPMN XML doesn't create a new version."""
    process_id = process_definition.id
    new_name = "Updated Process Name"

    # Update only the name
    response = await async_client.put(
        f"/processes/{process_id}",
        json={
            "name": new_name,
        },
    )
    assert response.status_code == 200

    # Verify process name was updated
    data = response.json()["data"]
    assert data["name"] == new_name
    assert data["version"] == 1  # Version should not change

    # Verify no new version was created
    versions_response = await async_client.get(f"/processes/{process_id}/versions")
    assert versions_response.status_code == 200
    versions_data = versions_response.json()["data"]
    assert versions_data["total"] == 1
    assert len(versions_data["items"]) == 1


async def test_multiple_bpmn_updates(
    async_client: AsyncClient,
    process_definition: ProcessDefinition,
    session: AsyncSession,
):
    """Test that multiple BPMN XML updates create sequential versions."""
    process_id = process_definition.id
    updates = [
        ("<bpmn>Version 2</bpmn>", "Second version"),
        ("<bpmn>Version 3</bpmn>", "Third version"),
        ("<bpmn>Version 4</bpmn>", "Fourth version"),
    ]

    current_version = 1
    for xml, notes in updates:
        current_version += 1
        response = await async_client.put(
            f"/processes/{process_id}",
            json={
                "bpmn_xml": xml,
                "notes": notes,
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["version"] == current_version
        assert data["bpmn_xml"] == xml

    # Verify all versions exist and are in correct order
    versions_response = await async_client.get(f"/processes/{process_id}/versions")
    assert versions_response.status_code == 200
    versions_data = versions_response.json()["data"]
    expected_total = 4 # Initial + 3 updates
    assert versions_data["total"] == expected_total
    assert versions_data["page"] == 1
    # Assuming default page size is >= 4, all items should be on the first page
    assert len(versions_data["items"]) == expected_total
    versions = versions_data["items"]

    # Verify version order (newest first)
    for i, version in enumerate(versions):
        expected_version = 4 - i
        assert version["number"] == expected_version
        if expected_version > 1:
            update_index = expected_version - 2
            assert version["bpmn_xml"] == updates[update_index][0]
            assert version["notes"] == updates[update_index][1]


async def test_update_process_with_empty_notes(
    async_client: AsyncClient,
    process_definition: ProcessDefinition,
    session: AsyncSession,
):
    """Test that updating BPMN XML without notes creates default note text."""
    process_id = process_definition.id
    new_xml = "<bpmn>Updated without notes</bpmn>"

    response = await async_client.put(
        f"/processes/{process_id}",
        json={
            "bpmn_xml": new_xml,
        },
    )
    assert response.status_code == 200

    # Verify new version was created with default notes
    versions_response = await async_client.get(f"/processes/{process_id}/versions")
    versions_data = versions_response.json()["data"]
    assert versions_data["total"] == 2
    assert len(versions_data["items"]) == 2
    latest_version = versions_data["items"][0]
    assert latest_version["number"] == 2
    assert latest_version["notes"] == "Version 2 created via update."


# --- Tests for GET /processes/{process_id}/versions/{version_number} ---


async def test_get_specific_process_version(
    async_client: AsyncClient,
    process_with_multiple_versions: ProcessDefinition,
):
    """Test getting a specific version of a process."""
    process = process_with_multiple_versions
    process_id = process.id
    version_to_get = 2

    response = await async_client.get(
        f"/processes/{process_id}/versions/{version_to_get}"
    )
    assert response.status_code == 200

    data = response.json()["data"]
    validated_version = ProcessVersionResponse.model_validate(data)

    assert validated_version.number == version_to_get
    assert validated_version.process_id == process_id
    assert validated_version.bpmn_xml == "<bpmn>Version 2</bpmn>"
    assert validated_version.notes == "Second version"


async def test_get_specific_process_version_latest(
    async_client: AsyncClient,
    process_with_multiple_versions: ProcessDefinition,
):
    """Test getting the latest version of a process."""
    process = process_with_multiple_versions
    process_id = process.id
    version_to_get = 3

    response = await async_client.get(
        f"/processes/{process_id}/versions/{version_to_get}"
    )
    assert response.status_code == 200

    data = response.json()["data"]
    validated_version = ProcessVersionResponse.model_validate(data)

    assert validated_version.number == version_to_get
    assert validated_version.process_id == process_id
    assert validated_version.bpmn_xml == "<bpmn>Version 3</bpmn>"
    assert validated_version.notes == "Third version"


async def test_get_specific_process_version_first(
    async_client: AsyncClient,
    process_with_multiple_versions: ProcessDefinition,
):
    """Test getting the first version of a process."""
    process = process_with_multiple_versions
    process_id = process.id
    version_to_get = 1

    response = await async_client.get(
        f"/processes/{process_id}/versions/{version_to_get}"
    )
    assert response.status_code == 200

    data = response.json()["data"]
    validated_version = ProcessVersionResponse.model_validate(data)

    assert validated_version.number == version_to_get
    assert validated_version.process_id == process_id
    assert validated_version.bpmn_xml == SIMPLE_PROCESS_XML
    assert validated_version.notes == "Initial version"


async def test_get_specific_process_version_not_found(
    async_client: AsyncClient,
    process_with_multiple_versions: ProcessDefinition,
):
    """Test getting a version number that doesn't exist for a process."""
    process = process_with_multiple_versions
    process_id = process.id
    non_existent_version = 99

    response = await async_client.get(
        f"/processes/{process_id}/versions/{non_existent_version}"
    )
    assert response.status_code == 404
    assert (
        f"Version {non_existent_version} not found for process {process_id}"
        in response.json()["detail"]
    )


async def test_get_specific_process_version_process_not_found(
    async_client: AsyncClient,
):
    """Test getting a version for a process ID that doesn't exist."""
    non_existent_process_id = uuid4()
    version_number = 1

    response = await async_client.get(
        f"/processes/{non_existent_process_id}/versions/{version_number}"
    )
    assert response.status_code == 404
    assert "Process definition not found" in response.json()["detail"]