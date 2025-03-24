# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- BPMN diagram import and export functionality
  - Export diagrams as standard BPMN files
  - Import BPMN files with drag-and-drop support
  - Automatic conversion between Pythmata extensions and standard BPMN
  - Validation of imported BPMN files
  - User-friendly error handling and notifications
- WebSocket-based chat system for BPMN Process Assistant
  - Real-time streaming of LLM responses
  - Typing indicators
  - Multi-client chat sessions
  - Automatic reconnection handling
  - Connection status indicators
- Initial project setup
- Frontend React/TypeScript application
  - Material-UI components
  - BPMN.js integration
  - State management with Zustand
  - Form handling with React Hook Form
  - Real-time updates with WebSocket
  - Responsive layout and theming
  - Timer event properties panel for configuring timer events
  - Gateway condition editor for configuring sequence flow conditions
    - Support for exclusive and inclusive gateways
    - Expression validation and syntax highlighting
    - Default flow configuration
    - Process variable integration
  - Gateway properties panel for configuring gateway-specific settings
    - Default flow selection for exclusive and inclusive gateways
    - Informational guidance for different gateway types
- Backend Python application
  - BPMN execution engine
  - Process management
  - Event handling system
  - Script execution environment
  - Robust timer event scheduler for automatically triggering timer start events
    - Persistent job storage using Redis
    - Efficient scheduling using APScheduler
    - Support for all timer types (duration, date, cycle)
    - Fault tolerance with automatic recovery
    - Distributed timer execution support
- Infrastructure
  - Docker containerization
  - PostgreSQL database
  - Redis caching
  - RabbitMQ message queue
- Documentation
  - Project overview and architecture
  - Development setup guide
  - Contributing guidelines
  - Code of conduct
  - Timer events configuration and usage guide
  - Gateway conditions configuration and usage guide

### Changed
- None

### Deprecated
- None

### Removed
- None

### Fixed
- Activity logs not showing in UI by committing logs to database and passing instance_manager to token movement methods
- Timer event validation issues with xsi:type attributes in BPMN XML by enhancing the validator to handle complex type substitutions and adding specific error categorization for known valid patterns
- Foreign key violation in activity logs when triggered by timer events by ensuring process instance exists in database before creating activity logs
- "Can't find variable: amount" error in Sequence Flow Properties Panel by improving expression validation to use mock variables instead of evaluating expressions directly

### Security
- None

## [0.1.0] - 2025-01-31

### Added
- Initial release
- Basic BPMN process execution
- Process designer interface
- Script task support
- Docker development environment

[Unreleased]: https://github.com/yourusername/pythmata/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/pythmata/releases/tag/v0.1.0
