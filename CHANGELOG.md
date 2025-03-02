# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup
- Frontend React/TypeScript application
  - Material-UI components
  - BPMN.js integration
  - State management with Zustand
  - Form handling with React Hook Form
  - Real-time updates with WebSocket
  - Responsive layout and theming
  - Timer event properties panel for configuring timer events
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

### Changed
- None

### Deprecated
- None

### Removed
- None

### Fixed
- Activity logs not showing in UI by committing logs to database and passing instance_manager to token movement methods

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
