# Use Python 3.11 slim image as base
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Copy scripts first and make executable
COPY scripts/start.sh scripts/install_plugin_deps.sh /app/scripts/
RUN chmod +x /app/scripts/start.sh /app/scripts/install_plugin_deps.sh

# Copy the rest of the application
COPY . .

# Create plugin directory
RUN mkdir -p /app/plugins

# Install dependencies and package in development mode
RUN poetry install --no-interaction --no-ansi

# Expose port
EXPOSE 8000

# Run the start script
CMD ["/app/scripts/start.sh"]
