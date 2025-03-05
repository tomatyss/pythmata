.PHONY: help install dev build test lint format clean docker-up docker-down docker-build

# Colors
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
WHITE  := $(shell tput -Txterm setaf 7)
RESET  := $(shell tput -Txterm sgr0)

# Help
help:
	@echo ''
	@echo 'Usage:'
	@echo '  ${YELLOW}make${RESET} ${GREEN}<target>${RESET}'
	@echo ''
	@echo 'Targets:'
	@awk '/^[a-zA-Z\-\_0-9]+:/ { \
		helpMessage = match(lastLine, /^# (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 2, RLENGTH); \
			printf "  ${YELLOW}%-20s${RESET} ${GREEN}%s${RESET}\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)

# Install dependencies
install:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Installing backend dependencies..."
	cd backend && poetry install

# Start development servers
dev:
	@echo "Starting development environment..."
	docker-compose up

# Build for production
build:
	@echo "Building frontend..."
	cd frontend && npm run build
	@echo "Building backend..."
	cd backend && python setup.py build

# Run tests
test:
	@echo "Running frontend tests..."
	cd frontend && npm run test:coverage
	@echo "Running backend tests..."
	cd backend && pytest --cov=src/ tests/

# Run linting
lint:
	@echo "Linting frontend..."
	cd frontend && npm run lint
	@echo "Type checking frontend..."
	cd frontend && tsc --noEmit
	@echo "Linting backend..."
	cd backend && poetry run black --check .
	cd backend && poetry run isort --check-only .
	cd backend && poetry run mypy src/

# Fix linting issues
lint-fix:
	@echo "Fixing frontend linting issues..."
	cd frontend && npm run format
	@echo "Fixing backend linting issues..."
	cd backend && poetry run black .
	cd backend && poetry run isort .
	@echo "Removing unused imports in backend..."
	cd backend && poetry run autoflake --in-place --remove-all-unused-imports --recursive src/

# Format code
format:
	@echo "Formatting frontend..."
	cd frontend && npm run format
	@echo "Formatting backend..."
	cd backend && poetry run isort .
	cd backend && poetry run black .

# Clean build artifacts
clean:
	@echo "Cleaning frontend..."
	cd frontend && rm -rf dist node_modules
	@echo "Cleaning backend..."
	cd backend && rm -rf build dist *.egg-info .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Docker commands
docker-up:
	docker-compose up

docker-down:
	docker-compose down

docker-build:
	docker-compose build

# Database commands
db-migrate:
	cd backend && alembic upgrade head

db-rollback:
	cd backend && alembic downgrade -1

db-reset:
	cd backend && alembic downgrade base
	cd backend && alembic upgrade head

# Development utilities
watch-logs:
	docker-compose logs -f

shell-backend:
	docker-compose exec backend /bin/bash

shell-frontend:
	docker-compose exec frontend /bin/sh

# Generate documentation
docs:
	cd backend && pdoc --html --output-dir docs/ src/
	cd frontend && npm run docs

# Security checks
security-check:
	cd backend && safety check
	cd frontend && npm audit

# Type checking
type-check:
	cd frontend && npm run type-check
	cd backend && mypy src/

# Create new migration
define MIGRATION_TEMPLATE
"""$(name)

Revision ID: $$revision
Revises: $$down_revision
Create Date: $$create_date

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '$$revision'
down_revision = '$$down_revision'
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
endef
export MIGRATION_TEMPLATE

migration:
	@if [ -z "$(name)" ]; then \
		echo "Error: Migration name required. Usage: make migration name='description'"; \
		exit 1; \
	fi
	cd backend && alembic revision -m "$(name)"
