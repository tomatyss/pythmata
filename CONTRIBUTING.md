# Contributing to Pythmata

Thank you for your interest in contributing to Pythmata! This document provides guidelines and instructions for contributing to the project.

## Development Environment Setup

### Prerequisites

- Docker and Docker Compose
- Node.js 20.x (for local frontend development)
- Python 3.11+ (for local backend development)
- Git

### Local Development Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/pythmata.git
   cd pythmata
   ```

2. **Frontend Development**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   The frontend development server will be available at http://localhost:3000

3. **Backend Development**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   python -m pythmata
   ```
   The backend API will be available at http://localhost:8000

4. **Docker Development**
   ```bash
   docker-compose up
   ```
   This will start all services including PostgreSQL, Redis, and RabbitMQ.

## Project Structure

### Frontend Structure

```
frontend/
├── src/
│   ├── components/        # Shared React components
│   │   ├── shared/       # Common UI components
│   │   └── Layout/       # Layout components
│   ├── hooks/            # Custom React hooks
│   ├── lib/              # Utility functions and services
│   ├── pages/            # Page components
│   ├── store/            # State management
│   └── types/            # TypeScript type definitions
├── public/               # Static assets
└── tests/               # Frontend tests
```

### Backend Structure

```
backend/
├── src/
│   ├── pythmata/
│   │   ├── core/        # Core BPMN engine
│   │   ├── api/         # API endpoints
│   │   ├── models/      # Data models
│   │   └── services/    # Business logic
├── tests/              # Backend tests
└── docs/              # Documentation
```

## Coding Standards

### Frontend Guidelines

1. **TypeScript**
   - Use TypeScript for all new code
   - Define interfaces for component props
   - Avoid using `any` type
   - Use type inference when possible

2. **React Components**
   - Use functional components with hooks
   - Keep components focused and small
   - Use proper prop types
   - Document complex components

3. **State Management**
   - Use Zustand for global state
   - Use React Query for API data
   - Keep local state minimal

4. **Styling**
   - Use Material-UI components
   - Follow theme configuration
   - Use Tailwind utilities when needed

### Backend Guidelines

1. **Python Style**
   - Follow PEP 8 guidelines
   - Use type hints
   - Document functions and classes
   - Keep functions focused

2. **API Design**
   - Follow RESTful principles
   - Document endpoints
   - Validate input data
   - Handle errors gracefully

3. **Testing**
   - Write unit tests for new features
   - Maintain test coverage
   - Mock external dependencies

## Git Workflow

1. **Branching**
   - `main`: Production-ready code
   - `develop`: Development branch
   - Feature branches: `feature/description`
   - Bug fixes: `fix/description`

2. **Commits**
   - Write clear commit messages
   - Use conventional commits format
   - Keep commits focused

3. **Pull Requests**
   - Create PR against `develop`
   - Include tests
   - Update documentation
   - Request reviews

## Testing

### Frontend Testing

```bash
# Run unit tests
npm test

# Run e2e tests
npm run test:e2e

# Check test coverage
npm run test:coverage
```

### Backend Testing

```bash
# Run unit tests
pytest

# Run with coverage
pytest --cov=pythmata
```

## Documentation

- Update README.md for major changes
- Document new features
- Update API documentation
- Include examples when relevant

## Release Process

1. **Version Bump**
   - Update version in package.json
   - Update version in pyproject.toml
   - Update CHANGELOG.md

2. **Testing**
   - Run all tests
   - Perform manual testing
   - Check documentation

3. **Release**
   - Merge to main branch
   - Create release tag
   - Update release notes

## Getting Help

- Create an issue for bugs
- Use discussions for questions
- Join our community chat
- Check existing documentation

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
