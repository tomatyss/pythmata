import json
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.api.routes import router
from pythmata.api.schemas import ProcessDefinitionResponse, ProcessStats
from pythmata.models.process import ProcessDefinition, ProcessInstance, ProcessStatus
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
