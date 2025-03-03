# Test Suite Documentation

This directory contains the test suite for the Pythmata project. The tests are organized to maintain clarity and reusability while following testing best practices.

## Directory Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared pytest fixtures and configuration
├── test_main.py               # Main application tests
├── api/                       # API endpoint tests
├── core/                      # Core functionality tests
│   ├── engine/               # Process engine tests
│   │   ├── base.py          # Base class for engine tests
│   │   └── ...
│   ├── saga/                # Saga pattern tests
│   │   ├── base.py         # Base class for saga tests
│   │   └── ...
│   └── testing/             # Test utilities and helpers
│       ├── __init__.py     # Shared test assertions and utilities
│       └── constants.py     # Test configuration constants
└── data/                    # Test data files
```

## Key Components

### Fixtures (`conftest.py`)

The `conftest.py` file contains shared pytest fixtures organized into sections:

- **Core Fixtures**: Basic test setup like database and Redis connections
- **Application Fixtures**: FastAPI test client and dependency overrides
- **Test Settings**: Environment-aware configuration for testing

### Base Test Classes

- **BaseEngineTest** (`core/engine/base.py`): Base class for process engine tests
  - Provides utilities for creating process flows
  - Handles common test setup and teardown

- **BaseSagaTest** (`core/saga/base.py`): Base class for saga pattern tests
  - Provides utilities for saga testing
  - Manages saga test state

### Test Utilities (`core/testing`)

- **Assertion Helpers** (`__init__.py`):
  - `assert_token_state`: Verify process token positions
  - `assert_saga_state`: Verify saga orchestration state
  - `assert_process_variables`: Verify process variable values

- **Constants** (`constants.py`):
  - Default configuration values for testing
  - Environment variable fallbacks

## Usage

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/core/test_database.py

# Run tests with specific marker
pytest -m "integration"

# Run tests with coverage
pytest --cov=pythmata
```

### Writing Tests

1. **Use Fixtures**
   ```python
   async def test_example(session, state_manager):
       # session and state_manager are automatically provided
       ...
   ```

2. **Use Base Classes**
   ```python
   from tests.core.engine.base import BaseEngineTest

   class TestProcessFlow(BaseEngineTest):
       async def test_sequence_flow(self):
           flow = self.create_sequence_flow()
           ...
   ```

3. **Use Test Assertions**
   ```python
   from tests.core.testing import assert_token_state

   async def test_process_execution(state_manager):
       await assert_token_state(
           state_manager,
           instance_id="test_instance",
           expected_count=1,
           expected_node_ids=["StartEvent_1"]
       )
   ```

## Best Practices

1. **Test Organization**
   - Keep tests focused and well-organized
   - Use descriptive test names
   - Group related tests in classes

2. **Fixture Usage**
   - Use fixtures for common setup
   - Keep fixtures simple and focused
   - Document fixture dependencies

3. **Test Isolation**
   - Each test should be independent
   - Clean up test data after each test
   - Don't rely on test execution order

4. **Assertions**
   - Use provided assertion helpers
   - Write clear assertion messages
   - Test both success and failure cases

5. **Documentation**
   - Document complex test scenarios
   - Include examples in docstrings
   - Keep this README updated

## Settings Fixtures Best Practices

The project uses different approaches for settings in tests depending on the testing scenario. Here are the best practices for using settings fixtures:

1. **Global Test Settings Fixture**
   - Use for integration tests that need realistic configuration
   - Use for testing database operations, API endpoints, or service integrations
   - Use when you need environment-aware configuration
   ```python
   async def test_feature(test_settings, state_manager, session):
       # Use components configured with test_settings
       result = await some_function_that_uses_settings()
       assert result == expected_value
   ```

2. **Local Mock Settings**
   - Use for unit tests that verify behavior in isolation
   - Use when testing error handling or specific code paths
   - Use when the actual settings values don't matter
   ```python
   @pytest.fixture
   def mock_settings():
       """Create mock settings for testing."""
       return Settings(
           server=ServerSettings(host="localhost", port=8000, debug=True),
           # Other settings with controlled values
       )
   ```

3. **Hybrid Approach (Using test_settings with Patching)**
   - Use when you need realistic settings but need to control where they're used
   - Use when testing components that create their own Settings instances internally
   ```python
   async def test_with_patched_settings(self):
       with patch(
           "module.path.Settings",
           new=MagicMock(return_value=self.test_settings)
       ):
           # Any code that creates a Settings instance will get test_settings
           result = await function_that_creates_settings_internally()
           assert result == expected_value
   ```

4. **Complete Mocking for Behavior Verification**
   - Use when testing functions that use settings but you only care about method calls
   - Use when verifying interaction patterns rather than actual functionality
   ```python
   async def test_lifecycle_function():
       mock_settings = MagicMock()
       with patch("module.path.Settings", new=MagicMock(return_value=mock_settings)):
           await function_under_test()
           # Verify expected interactions
           assert some_dependency.method.called
   ```

### Decision Framework for Choosing the Right Approach

- **Component behavior in isolation** → Local mock settings
- **Integration between components** → Global test settings
- **Method calls and interactions** → Complete mocking
- **Complex scenarios with internal Settings creation** → Hybrid approach
- **Need for realistic values** → Global test settings
- **Testing error handling** → Local mock or complete mocking

### Implementation Guidelines

- Keep the global `test_settings` fixture in `conftest.py`
- Use descriptive fixture names (`test_settings`, `mock_settings`, etc.)
- Document the purpose of custom settings fixtures
- Use appropriate fixture scope (`session` for global, `function` for mocks)
- Be consistent within test modules
