"""Tests for the services API routes."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from pythmata.core.auth import get_current_user
from pythmata.core.services.registry import ServiceTaskRegistry
from pythmata.main import app


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    mock_user = MagicMock()
    mock_user.id = "00000000-0000-0000-0000-000000000000"
    mock_user.email = "test@example.com"
    mock_user.is_active = True
    mock_user.roles = []
    return mock_user


@pytest.fixture
def client(mock_user):
    """Create a test client with authentication mocked."""
    # Override the authentication dependency
    app.dependency_overrides[get_current_user] = lambda: mock_user
    client = TestClient(app)
    yield client
    # Clean up the override after the test
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_registry():
    """Create a mock registry with test service tasks."""
    mock_tasks = [
        {
            "name": "http",
            "description": "Make HTTP requests to external services and APIs",
            "properties": [
                {
                    "name": "url",
                    "label": "URL",
                    "type": "string",
                    "required": True,
                    "description": "URL to send the request to",
                },
                {
                    "name": "method",
                    "label": "Method",
                    "type": "string",
                    "required": True,
                    "default": "GET",
                    "options": ["GET", "POST", "PUT", "DELETE"],
                    "description": "HTTP method to use",
                },
            ],
        },
        {
            "name": "logger",
            "description": "Log messages during process execution",
            "properties": [
                {
                    "name": "level",
                    "label": "Log Level",
                    "type": "string",
                    "required": True,
                    "default": "info",
                    "options": ["info", "warning", "error", "debug"],
                    "description": "Logging level",
                },
                {
                    "name": "message",
                    "label": "Message",
                    "type": "string",
                    "required": True,
                    "description": "Message to log",
                },
            ],
        },
    ]

    # Create a mock registry that returns the mock tasks
    mock_registry = MagicMock(spec=ServiceTaskRegistry)
    mock_registry.list_tasks.return_value = mock_tasks

    return mock_registry


def test_list_service_tasks(client, mock_registry):
    """Test listing service tasks."""
    # Patch the get_service_task_registry function to return our mock registry
    with patch(
        "pythmata.api.routes.services.get_service_task_registry",
        return_value=mock_registry,
    ):
        response = client.get("/api/services/tasks")

        assert response.status_code == 200
        data = response.json()

        # Verify the response contains the expected tasks
        assert len(data) == 2
        assert data[0]["name"] == "http"
        assert data[1]["name"] == "logger"

        # Verify the properties are included
        assert len(data[0]["properties"]) == 2
        assert data[0]["properties"][0]["name"] == "url"
        assert data[0]["properties"][1]["name"] == "method"

        assert len(data[1]["properties"]) == 2
        assert data[1]["properties"][0]["name"] == "level"
        assert data[1]["properties"][1]["name"] == "message"


def test_list_service_tasks_error(client):
    """Test error handling when listing service tasks."""
    # Patch the get_service_task_registry function to raise an exception
    with patch(
        "pythmata.api.routes.services.get_service_task_registry",
        side_effect=Exception("Test error"),
    ):
        response = client.get("/api/services/tasks")

        assert response.status_code == 500
        data = response.json()

        # Verify the error message
        assert "detail" in data
        assert "Test error" in data["detail"]
