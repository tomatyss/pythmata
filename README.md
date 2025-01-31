# Pythmata

A Python-based BPMN workflow engine with a modern React frontend.

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
