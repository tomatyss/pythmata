# Performance Reference

## System Requirements

### Minimum Requirements
- CPU: 2 cores
- Memory: 4GB RAM
- Storage: 20GB
- Network: 100Mbps

### Recommended Requirements
- CPU: 4+ cores
- Memory: 8GB+ RAM
- Storage: 50GB SSD
- Network: 1Gbps

## Performance Tuning

### Database Optimization
```python
# Connection Pool Configuration
engine = create_async_engine(
    settings.db_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout
)

# Query Optimization
from sqlalchemy import Index
Index('idx_process_instance_status', ProcessInstance.status)
Index('idx_process_instance_process_id', ProcessInstance.process_id)
```

### Redis Caching
```python
# Cache Configuration
cache = Redis(
    url=settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
    pool_size=settings.redis_pool_size
)

# Cache Usage
@cached(ttl=300)  # 5 minutes
async def get_process_definition(id: str):
    return await db.get_process(id)
```

### Process Engine Settings
```python
# Token Batch Processing
settings = {
    'token_batch_size': 100,     # Process tokens in batches
    'max_parallel_tokens': 50,    # Maximum parallel token executions
    'state_check_interval': 5     # Seconds between state checks
}

# Variable Size Limits
settings = {
    'max_variable_size': 1048576,  # 1MB
    'max_total_variables': 10485760 # 10MB per instance
}
```

## Scaling Strategies

### Horizontal Scaling
```yaml
# docker-compose.scale.yml
services:
  worker:
    build: ./backend
    command: python worker.py
    environment:
      - PYTHMATA_RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G
```

### Load Balancing
```nginx
# nginx.conf
upstream backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://backend;
    }
}
```

## Monitoring

### Metrics Collection
```python
# Prometheus Metrics
from prometheus_client import Counter, Histogram

process_instances = Counter(
    'process_instances_total',
    'Total number of process instances'
)

execution_time = Histogram(
    'process_execution_seconds',
    'Time spent executing process instances'
)
```

### Performance Dashboards
```python
# Grafana Dashboard Configuration
dashboard = {
    'process_metrics': {
        'active_instances': 'pythmata_active_instances',
        'execution_time': 'pythmata_execution_time_seconds',
        'error_rate': 'pythmata_errors_total',
        'token_throughput': 'pythmata_tokens_processed_total'
    }
}
```

## Optimization Tips

### 1. Database
- Use appropriate indexes
- Regular vacuum and analyze
- Monitor query performance
- Optimize connection pools

### 2. Caching
- Cache process definitions
- Cache frequently accessed data
- Use appropriate TTLs
- Monitor cache hit rates

### 3. Process Execution
- Batch token processing
- Parallel execution where possible
- Efficient variable handling
- Proper error handling

### 4. Network
- Use connection pooling
- Enable keepalive
- Compress responses
- Use WebSocket for real-time updates

## Performance Testing

### Load Testing
```python
# locust test example
from locust import HttpUser, task, between

class ProcessUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def start_process(self):
        self.client.post(
            "/api/v1/processes/OrderProcess/instances",
            json={"variables": {"amount": 100}}
        )
```

### Benchmarking
```bash
# Apache Benchmark Example
ab -n 1000 -c 10 http://localhost:8000/api/v1/processes

# wrk Example
wrk -t12 -c400 -d30s http://localhost:8000/api/v1/processes
```

## Common Issues

### 1. Memory Leaks
- Monitor memory usage
- Implement proper cleanup
- Use memory profiling
- Set appropriate limits

### 2. CPU Bottlenecks
- Profile CPU usage
- Optimize hot paths
- Use async where appropriate
- Scale horizontally

### 3. Database Performance
- Monitor slow queries
- Optimize indexes
- Use connection pooling
- Regular maintenance

### 4. Network Issues
- Monitor latency
- Use connection pooling
- Enable compression
- Implement retry logic

## Performance Checklist

1. Database
   - [ ] Indexes optimized
   - [ ] Connection pools configured
   - [ ] Query performance monitored
   - [ ] Regular maintenance scheduled

2. Caching
   - [ ] Process definitions cached
   - [ ] Cache size configured
   - [ ] TTLs set appropriately
   - [ ] Hit rates monitored

3. Process Engine
   - [ ] Batch processing configured
   - [ ] Parallel execution enabled
   - [ ] Resource limits set
   - [ ] Error handling implemented

4. Monitoring
   - [ ] Metrics collection enabled
   - [ ] Dashboards configured
   - [ ] Alerts set up
   - [ ] Performance baselines established
