# Docker Deployment Guide

Complete Docker deployment for Open Source Fitness Coach with production-ready configuration.

## Quick Start

### 1. Prerequisites

- Docker 24.0+ with Compose V2
- At least 2GB RAM and 10GB disk space
- API key for your chosen AI provider (Anthropic, OpenAI, or Ollama)

### 2. Configuration

```bash
# Navigate to docker directory
cd docker

# Copy environment template
cp .env.example .env

# Edit configuration (add your API keys)
nano .env
```

**Required configuration:**
- `POSTGRES_PASSWORD` - Secure database password
- `FITNESS_ANTHROPIC_API_KEY` or `FITNESS_OPENAI_API_KEY` - AI provider API key

### 3. Deploy

```bash
# Build and start services
docker compose up -d

# Check logs
docker compose logs -f

# Verify health
curl http://localhost:8000/health
```

**Access points:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Configuration Options

### AI Providers

Choose one of three AI providers:

#### 1. Anthropic Claude (Recommended)
```env
FITNESS_AI_PROVIDER=anthropic
FITNESS_ANTHROPIC_API_KEY=sk-ant-your-key
FITNESS_ANTHROPIC_MODEL=claude-sonnet-4-20250514
INSTALL_EXTRAS=cloud
```

#### 2. OpenAI GPT
```env
FITNESS_AI_PROVIDER=openai
FITNESS_OPENAI_API_KEY=sk-your-key
FITNESS_OPENAI_MODEL=gpt-4o
INSTALL_EXTRAS=cloud
```

#### 3. Ollama (Local, Privacy-focused)
```env
FITNESS_AI_PROVIDER=ollama
FITNESS_OLLAMA_BASE_URL=http://ollama:11434
FITNESS_OLLAMA_MODEL=llama3.2
INSTALL_EXTRAS=ollama
```

For Ollama, uncomment the ollama service in `docker-compose.dev.yml`.

### RAG Providers

Choose embedding and RAG backend:

#### PostgreSQL + pgvector (Default, Recommended)
```env
FITNESS_RAG_PROVIDER=pgvector
FITNESS_EMBEDDING_PROVIDER=openai
FITNESS_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

#### SQLite (Lightweight)
```env
FITNESS_RAG_PROVIDER=sqlite
FITNESS_EMBEDDING_PROVIDER=openai
```

#### Disabled (No memory)
```env
FITNESS_RAG_PROVIDER=none
FITNESS_EMBEDDING_PROVIDER=none
```

### Install Extras

Control which dependencies are installed:

| Value | Dependencies | Use Case |
|-------|--------------|----------|
| `base` | Core only | Minimal installation |
| `cloud` | Anthropic + OpenAI | Cloud AI providers |
| `ollama` | Ollama only | Local AI |
| `all` | Everything | Development |

```env
INSTALL_EXTRAS=cloud
```

## Development Mode

Development configuration with hot-reload and debugging tools:

```bash
# Start with dev overrides
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Features:
# - Code hot-reload (volume mounts)
# - Debug mode enabled
# - pgAdmin on port 5050
# - Exposed PostgreSQL port 5432
```

**pgAdmin Access:**
- URL: http://localhost:5050
- Email: admin@fitness.local (configurable in .env)
- Password: admin (configurable in .env)

## Docker Images

### Multi-stage Build

The `Dockerfile.backend` uses multi-stage builds for optimization:

1. **Builder Stage**: Compiles dependencies
2. **Runtime Stage**: Minimal image with only runtime needs

**Benefits:**
- Smaller final image (~200MB vs ~500MB)
- Faster deployment
- Better security (no build tools)

### Build Arguments

```bash
# Cloud providers only (default)
docker build -f docker/Dockerfile.backend -t fitness-coach:cloud \
  --build-arg INSTALL_EXTRAS=cloud .

# All dependencies (development)
docker build -f docker/Dockerfile.backend -t fitness-coach:full \
  --build-arg INSTALL_EXTRAS=all .

# Minimal installation
docker build -f docker/Dockerfile.backend -t fitness-coach:minimal \
  --build-arg INSTALL_EXTRAS=base .
```

## Security Features

### Backend Container

✅ **Enabled:**
- Non-root user (UID 1000)
- No new privileges
- Capability dropping (ALL)
- Health checks
- Resource limits

### PostgreSQL Container

✅ **Enabled:**
- No new privileges
- Health checks
- Resource limits
- Volume encryption ready

### Network Isolation

- Private bridge network
- Services communicate only via network
- No host network mode

## Volumes

| Volume | Purpose | Backup Needed |
|--------|---------|---------------|
| `postgres_data` | Database | ✅ Critical |
| `app_data` | RAG vectors, app data | ✅ Important |
| `app_logs` | Application logs | ❌ Optional |

### Backup Strategy

```bash
# Backup database
docker compose exec postgres pg_dump -U fitness fitness > backup.sql

# Backup volumes
docker run --rm -v fitness-postgres-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres-data-backup.tar.gz /data

# Restore database
cat backup.sql | docker compose exec -T postgres psql -U fitness fitness

# Restore volume
docker run --rm -v fitness-postgres-data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/postgres-data-backup.tar.gz -C /
```

## Health Checks

### Backend

```bash
# Health check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/health/ready

# Docker health status
docker inspect --format='{{.State.Health.Status}}' fitness-backend
```

### PostgreSQL

```bash
# Connection test
docker compose exec postgres pg_isready -U fitness

# Docker health status
docker inspect --format='{{.State.Health.Status}}' fitness-postgres
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs backend
docker compose logs postgres

# Check environment
docker compose config

# Verify ports available
netstat -tlnp | grep -E '8000|5432'
```

### Database connection failed

```bash
# Check postgres is healthy
docker compose ps

# Test connection from backend
docker compose exec backend curl -v postgres:5432

# Check credentials
docker compose exec postgres psql -U fitness -d fitness -c "SELECT 1"
```

### API returns 500 errors

```bash
# Check backend logs with details
docker compose logs backend --tail=100

# Check environment variables
docker compose exec backend env | grep FITNESS

# Verify API key is set
docker compose exec backend sh -c 'echo $FITNESS_ANTHROPIC_API_KEY | cut -c1-10'
```

### Out of memory

```bash
# Check resource usage
docker stats

# Increase limits in docker-compose.yml:
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G  # Increase from 2G
```

## Production Deployment

### Recommended Configuration

```yaml
# docker-compose.prod.yml (override)
services:
  backend:
    restart: always
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
    environment:
      FITNESS_DEBUG: "false"
      FITNESS_RATE_LIMIT_CHAT: "5/minute"

  postgres:
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

### Deploy with Overrides

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Reverse Proxy (nginx)

```nginx
server {
    listen 80;
    server_name fitness.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;

        # SSE streaming support
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
    }
}
```

### SSL with Let's Encrypt

```bash
# Install certbot
apt install certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d fitness.example.com

# Auto-renewal
systemctl enable certbot.timer
```

## Maintenance

### Update Images

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker compose build --no-cache
docker compose up -d

# Verify
docker compose ps
docker compose logs -f
```

### Database Migrations

```bash
# Run migrations
docker compose exec backend alembic upgrade head

# Create new migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Check current version
docker compose exec backend alembic current
```

### Clean Up

```bash
# Stop services
docker compose down

# Remove volumes (WARNING: deletes data)
docker compose down -v

# Clean unused images
docker image prune -a

# Full cleanup
docker system prune -a --volumes
```

## Monitoring

### Resource Usage

```bash
# Real-time stats
docker stats fitness-backend fitness-postgres

# Disk usage
docker system df
```

### Logs

```bash
# Follow all logs
docker compose logs -f

# Specific service
docker compose logs -f backend

# Last 100 lines
docker compose logs --tail=100 backend

# Since timestamp
docker compose logs --since 2024-01-01T00:00:00 backend
```

## Performance Tuning

### PostgreSQL

Edit `docker-compose.yml`:

```yaml
services:
  postgres:
    environment:
      # Add performance settings
      POSTGRES_SHARED_BUFFERS: 256MB
      POSTGRES_EFFECTIVE_CACHE_SIZE: 1GB
      POSTGRES_WORK_MEM: 16MB
    command:
      - postgres
      - -c
      - shared_buffers=256MB
      - -c
      - effective_cache_size=1GB
```

### Backend Workers

For high traffic, use multiple workers:

```yaml
services:
  backend:
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"
```

## Support

- GitHub Issues: https://github.com/yourusername/fitness-coach
- Documentation: https://github.com/yourusername/fitness-coach/docs
- Discord: https://discord.gg/your-server
