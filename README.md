# Pythmata

A Python-based BPMN workflow engine with a modern React frontend.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.8-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/react-19.0.0-61DAFB.svg)](https://reactjs.org/)
[![Version](https://img.shields.io/badge/version-0.1.0-brightgreen.svg)](https://github.com/yourusername/pythmata)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://www.postgresql.org/)
[![Documentation](https://img.shields.io/badge/docs-MkDocs-blue.svg)](https://www.mkdocs.org/)


> **⚠️ DISCLAIMER: Work in Progress**  
> This project is under active development and has not reached a stable release yet.  
> APIs, features, and functionality may change without notice.  
> Not recommended for production use at this time.

## Overview

Pythmata is a workflow engine that implements the Business Process Model and Notation (BPMN) standard. It allows users to design, deploy, and execute business processes using a visual BPMN modeler, while providing powerful scripting capabilities for task automation.

## Architecture

### Frontend (React/TypeScript)

The frontend is built with modern React and TypeScript, following a component-based architecture with:

- **State Management**:
  - Zustand for global state management
  - React Query for server state and data fetching
  - React Hook Form for form handling and validation

- **UI Components**:
  - Material-UI (MUI) as the component library
  - Custom shared components for consistency
  - BPMN.js for process modeling and visualization

- **Key Features**:
  - Real-time process monitoring
  - Visual BPMN process designer
  - Script editor for task automation
  - Gateway condition configuration
  - Process instance management
  - Variable inspection and modification

### Backend (Python)

The backend is built with Python, implementing a robust BPMN execution engine with:

- **Core Engine**:
  - BPMN element implementations
  - Process instance management
  - Event handling and propagation
  - Script execution environment

- **Services**:
  - Process definition management
  - Instance execution and control
  - Variable management
  - Script execution and sandboxing

### Infrastructure

The project uses a modern containerized architecture with:

- **Docker Containers**:
  - Frontend (Node.js/Nginx)
  - Backend (Python)
  - PostgreSQL (Process data)
  - Redis (Caching/Pub-Sub)
  - RabbitMQ (Message Queue)

- **Development Tools**:
  - Docker Compose for local development
  - TypeScript for type safety
  - ESLint/Prettier for code formatting
  - Vite for frontend development

## Key Concepts

### Process Definitions

- **BPMN Modeling**: Users can create and modify process definitions using the visual BPMN modeler
- **Version Control**: Process definitions are versioned for tracking changes
- **XML Storage**: Processes are stored in BPMN 2.0 XML format

### Process Instances

- **Execution**: Running instances of process definitions
- **State Management**: Tracks current state and history
- **Variable Handling**: Manages process variables and their scopes
- **Event System**: Handles BPMN events and message flows

### Script Tasks

- **Python Scripting**: Embedded Python script execution
- **Sandboxing**: Secure script execution environment
- **Variable Access**: Scripts can access and modify process variables
- **External Integration**: Ability to interact with external systems

### Plugin System

- **Custom Service Tasks**: Extend the engine with custom service tasks
- **Plugin Discovery**: Automatic discovery and loading of plugins
- **Dependency Management**: Plugin-specific dependency management
- **Isolation**: Keep custom code separate from the core engine

### Event System

- **BPMN Events**: Implementation of start, intermediate, and end events
- **Message Events**: Handling of message-based communication
- **Timer Events**: Scheduling and execution of time-based events
- **Error Handling**: Error events and exception management

## Technical Implementation

### Frontend Architecture

1. **Component Structure**:
   - Shared components for reusability
   - Page-based routing
   - Layout management
   - Modal and dialog system

2. **State Management**:
   - Process store
   - Instance store
   - UI state management
   - Form state handling

3. **API Integration**:
   - Axios for HTTP requests
   - WebSocket for real-time updates
   - Error handling and retries
   - Request/response interceptors

4. **Styling and Theming**:
   - Material-UI theming
   - Tailwind CSS utilities
   - Responsive design
   - Dark/light mode support

### Backend Architecture

1. **Core Engine**:
   - BPMN element implementations
   - Process execution logic
   - Event handling system
   - Variable management

2. **Data Layer**:
   - PostgreSQL for persistent storage
   - Redis for caching and pub/sub
   - RabbitMQ for async tasks

3. **API Layer**:
   - RESTful API endpoints
   - WebSocket connections
   - Authentication/Authorization
   - Request validation

4. **Script Execution**:
   - Python script parsing
   - Sandboxed execution
   - Variable context management
   - Error handling

## Development Setup

1. **Prerequisites**:
   - Docker and Docker Compose
   - Node.js (for local frontend development)
   - Python (for local backend development)

2. **Environment Setup**:
   ```bash
   # Clone repository
   git clone https://github.com/yourusername/pythmata.git
   cd pythmata

   # Start services
   docker-compose up
   ```

3. **Development Workflow**:
   - Frontend development server: http://localhost:3000
   - Backend API: http://localhost:8000
   - PostgreSQL: localhost:5432
   - Redis: localhost:6379
   - RabbitMQ: localhost:5672 (Management: 15672)

## Test Setup

1. **Test Database**:
   - The test suite uses a separate database (`pythmata_test` by default)
   - Database is automatically created and migrated before tests run
   - Tables are created fresh for each test and cleaned up afterward

2. **Environment Variables**:
   ```bash
   # Database Configuration
   POSTGRES_USER=pythmata          # Database user
   POSTGRES_PASSWORD=pythmata      # Database password
   POSTGRES_HOST=localhost         # Database host
   POSTGRES_PORT=5432             # Database port
   POSTGRES_TEST_DB=pythmata_test # Test database name
   DB_POOL_SIZE=5                # Database connection pool size
   DB_MAX_OVERFLOW=10            # Maximum pool overflow

   # Redis Configuration
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_POOL_SIZE=10

   # RabbitMQ Configuration
   RABBITMQ_USER=guest
   RABBITMQ_PASSWORD=guest
   RABBITMQ_HOST=localhost
   RABBITMQ_PORT=5672
   RABBITMQ_CONNECTION_ATTEMPTS=3
   RABBITMQ_RETRY_DELAY=1
   ```

3. **Running Tests**:
   ```bash
   # Navigate to backend directory
   cd backend

   # Run all tests
   pytest

   # Run specific test file
   pytest tests/path/to/test_file.py

   # Run with coverage report
   pytest --cov=src
   ```

4. **CI/CD Integration**:
   - Test database is automatically created if it doesn't exist
   - Migrations are applied before test execution
   - Environment variables can be configured in CI/CD pipeline
   - Test results and coverage reports are generated

## Project Structure

```
pythmata/
├── frontend/                # React frontend application
│   ├── src/
│   │   ├── components/     # Shared React components
│   │   ├── hooks/         # Custom React hooks
│   │   ├── lib/           # Utility functions and services
│   │   ├── pages/         # Page components
│   │   ├── store/         # State management
│   │   └── types/         # TypeScript type definitions
│   └── public/            # Static assets
├── backend/               # Python backend application
│   ├── src/
│   │   ├── core/         # Core engine implementation
│   │   ├── api/          # API endpoints
│   │   ├── models/       # Data models
│   │   └── services/     # Business logic services
│   └── tests/            # Backend tests
└── config/               # Configuration files
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

<a href="https://www.buymeacoffee.com/tomatyss" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>
