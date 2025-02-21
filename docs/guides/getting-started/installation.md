# Installing Pythmata

This guide walks you through the process of installing and setting up Pythmata for local development.

## Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- Docker and Docker Compose
- Git

## System Requirements

- Memory: 4GB RAM minimum, 8GB recommended
- Storage: 1GB free space
- OS: Linux, macOS, or Windows with WSL2

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/pythmata.git
cd pythmata
```

### 2. Environment Setup

#### Backend Setup

1. Install Poetry (Python dependency manager):
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Install backend dependencies:
```bash
cd backend
poetry install
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

#### Frontend Setup

1. Install frontend dependencies:
```bash
cd frontend
npm install
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Database Setup

1. Start the required services using Docker Compose:
```bash
docker-compose up -d postgres redis rabbitmq
```

2. Run database migrations:
```bash
cd backend
poetry run alembic upgrade head
```

## Running the Application

### Development Mode

1. Start the backend server:
```bash
cd backend
poetry run uvicorn pythmata.main:app --reload
```

2. Start the frontend development server:
```bash
cd frontend
npm run dev
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Docker Deployment

To run the entire application using Docker:

```bash
docker-compose up -d
```

This will start:
- Frontend on http://localhost:3000
- Backend on http://localhost:8000
- PostgreSQL on localhost:5432
- Redis on localhost:6379
- RabbitMQ on localhost:5672 (Management: 15672)

## Verification

1. Check service health:
```bash
curl http://localhost:8000/health
```

2. Access the frontend:
- Open http://localhost:3000 in your browser
- You should see the Pythmata dashboard

3. Verify API documentation:
- Open http://localhost:8000/docs in your browser
- You should see the Swagger UI documentation

## Common Issues

### Database Connection

If you encounter database connection issues:
1. Ensure PostgreSQL is running:
```bash
docker-compose ps
```
2. Check database credentials in .env
3. Verify database migrations are up to date

### Redis Connection

If Redis connection fails:
1. Verify Redis is running:
```bash
docker-compose ps
```
2. Check Redis connection settings in .env
3. Ensure Redis port is not in use

### Frontend Build Issues

If you encounter frontend build problems:
1. Clear node_modules and reinstall:
```bash
cd frontend
rm -rf node_modules
npm install
```
2. Verify Node.js version compatibility
3. Check for environment variable configuration

## Next Steps

After successful installation:
1. Review the [Basic Concepts Guide](basic-concepts.md)
2. Explore [Example Workflows](../../examples/basic/order-process.md)

## Support

If you encounter any issues:
1. Check our GitHub Issues
2. Search existing GitHub issues
3. Create a new issue with:
   - Detailed description
   - Environment information
   - Steps to reproduce
   - Error messages/logs
