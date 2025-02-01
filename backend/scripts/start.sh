#!/bin/bash
set -e

# Wait for postgres
echo "Waiting for postgres..."
while ! nc -z postgres 5432; do
  sleep 0.1
done
echo "PostgreSQL started"

# Run migrations
echo "Running database migrations..."
poetry run alembic upgrade head

# Start application
echo "Starting application..."
poetry run uvicorn pythmata.main:app --host 0.0.0.0 --port 8000 --reload
