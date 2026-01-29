# Docker Deployment Files

Complete list of all Docker deployment files for Open Source Fitness Coach.

## Directory Structure

```
/opt/helper/opensource/fitness-coach/
├── docker/
│   ├── Dockerfile.backend          # Multi-stage production Dockerfile
│   ├── docker-compose.yml          # Production configuration
│   ├── docker-compose.dev.yml      # Development overrides
│   ├── .dockerignore               # Docker build exclusions
│   ├── .env.example                # Environment template
│   ├── init-db.sh                  # PostgreSQL initialization
│   ├── start.sh                    # Quick start script
│   ├── healthcheck.sh              # Health monitoring script
│   ├── Makefile                    # Convenience commands
│   ├── README.md                   # Docker documentation
│   ├── DEPLOYMENT.md               # Complete deployment guide
│   └── FILES.md                    # This file
│
└── backend/requirements/           # Python dependencies
    ├── base.txt                    # Core dependencies
    ├── cloud.txt                   # Cloud providers (Anthropic/OpenAI)
    ├── ollama.txt                  # Local AI (Ollama)
    └── all.txt                     # Everything (development)
```

## File Descriptions

### Dockerfile.backend

**Purpose:** Multi-stage Docker image for production deployment

**Features:**
- Python 3.12-slim base image
- Two-stage build (builder + runtime)
- Non-root user (UID 1000)
- Configurable extras via ARG INSTALL_EXTRAS
- Health check endpoint
- Automatic database migrations on startup

**Build arguments:**
```bash
INSTALL_EXTRAS=cloud   # base, cloud, ollama, all
```

**Size:** ~200MB (production), ~500MB (all extras)

### docker-compose.yml

**Purpose:** Production-ready multi-container deployment

**Services:**
- `postgres`: PostgreSQL 16 with pgvector extension
- `backend`: FastAPI application

**Security features:**
- No new privileges
- Capability dropping
- Resource limits (CPU/RAM)
- Health checks
- Private network

**Volumes:**
- `postgres_data`: Database persistence
- `app_data`: Application data (RAG vectors)
- `app_logs`: Application logs

### docker-compose.dev.yml

**Purpose:** Development environment overrides

**Additional features:**
- Code volume mounts for hot-reload
- Debug mode enabled
- pgAdmin on port 5050
- Exposed PostgreSQL port
- Optional Ollama service
- Reduced security hardening

**Usage:**
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### .dockerignore

**Purpose:** Exclude files from Docker build context

**Excludes:**
- Python cache files (`__pycache__`, `*.pyc`)
- Virtual environments (`venv/`, `env/`)
- Environment files (`.env`, `.env.local`)
- IDE files (`.vscode/`, `.idea/`)
- Data and logs
- Documentation

**Result:** Faster builds, smaller images

### .env.example

**Purpose:** Environment configuration template

**Required variables:**
- `POSTGRES_PASSWORD` - Database password
- `FITNESS_AI_PROVIDER` - AI provider choice
- `FITNESS_ANTHROPIC_API_KEY` or `FITNESS_OPENAI_API_KEY`

**Optional variables:**
- RAG provider settings
- Embedding provider settings
- Rate limiting
- CORS origins
- Debug mode

**Usage:**
```bash
cp .env.example .env
nano .env  # Configure
```

### init-db.sh

**Purpose:** PostgreSQL initialization script

**Actions:**
1. Creates pgvector extension
2. Grants permissions to fitness user
3. Sets up public schema

**Execution:** Automatic on first container start

### start.sh

**Purpose:** Interactive deployment script

**Features:**
- Prerequisites check (Docker, Compose)
- Environment validation
- Configuration wizard
- Automatic build and start
- Health check verification
- Deployment mode selection

**Usage:**
```bash
cd docker
./start.sh
```

### healthcheck.sh

**Purpose:** Comprehensive health monitoring

**Checks:**
- Docker daemon status
- Container health status
- Database connectivity
- pgvector extension
- API endpoints
- Resource usage
- Recent logs

**Usage:**
```bash
./healthcheck.sh
# Exit code 0 = healthy, 1 = unhealthy
```

**Automation:**
```bash
# Add to crontab for monitoring
*/5 * * * * cd /path/to/docker && ./healthcheck.sh || mail -s "Alert" admin@example.com
```

### Makefile

**Purpose:** Convenient command shortcuts

**Commands:**
```bash
make help          # Show all commands
make start         # Start production
make dev           # Start development
make stop          # Stop services
make restart       # Restart services
make logs          # Follow all logs
make health        # Run health check
make build         # Rebuild images
make clean         # Remove everything
make migrate       # Run DB migrations
make backup        # Backup database
make restore       # Restore database
make shell-backend # Open backend shell
make shell-db      # Open psql shell
make test          # Test API endpoints
```

### README.md

**Purpose:** Docker deployment documentation

**Contents:**
- Quick start guide
- Configuration options
- AI provider setup
- RAG configuration
- Development mode
- Build arguments
- Security features
- Troubleshooting
- Maintenance tasks

### DEPLOYMENT.md

**Purpose:** Complete production deployment guide

**Contents:**
- Server preparation
- Cloud platform guides (AWS, GCP, DigitalOcean, Fly.io)
- Reverse proxy setup (Nginx, Traefik)
- SSL/TLS configuration
- Security hardening
- Monitoring and logging
- Backup and recovery
- Performance tuning
- Update procedures

### FILES.md

**Purpose:** This file - complete documentation index

## Requirements Files

### base.txt

**Purpose:** Core dependencies only

**Includes:**
- FastAPI, Uvicorn
- SQLAlchemy, asyncpg
- Pydantic, settings
- Rate limiting

**Size:** ~50MB

**Use case:** Minimal installation, add providers separately

### cloud.txt

**Purpose:** Cloud AI providers

**Includes:**
- base.txt
- anthropic>=0.40.0
- openai>=1.50.0
- pgvector>=0.3.0

**Size:** ~120MB

**Use case:** Production with Anthropic Claude or OpenAI GPT

### ollama.txt

**Purpose:** Local AI with Ollama

**Includes:**
- base.txt
- pgvector>=0.3.0

**Size:** ~80MB

**Use case:** Privacy-focused local deployment

**Note:** Requires Ollama binary installed separately

### all.txt

**Purpose:** Everything including dev tools

**Includes:**
- base.txt
- All AI providers
- pgvector
- pytest, ruff, mypy

**Size:** ~200MB

**Use case:** Development environment

## Usage Examples

### Quick Start

```bash
cd docker
./start.sh
```

### Production Deployment

```bash
# 1. Configure
cp .env.example .env
nano .env

# 2. Build and deploy
docker compose build --no-cache
docker compose up -d

# 3. Verify
./healthcheck.sh
```

### Development

```bash
# Start with dev tools
make dev

# Or manually
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Custom Build

```bash
# Minimal
docker build -f Dockerfile.backend --build-arg INSTALL_EXTRAS=base -t fitness:minimal .

# Cloud providers
docker build -f Dockerfile.backend --build-arg INSTALL_EXTRAS=cloud -t fitness:cloud .

# Everything
docker build -f Dockerfile.backend --build-arg INSTALL_EXTRAS=all -t fitness:full .
```

### Maintenance

```bash
# View logs
make logs

# Backup database
make backup

# Run migrations
make migrate

# Update application
make update
```

## Security Features

### Container Security

✅ **Implemented:**
- Non-root user (UID 1000)
- Read-only filesystem where possible
- No new privileges
- Capability dropping (ALL)
- Resource limits

### Network Security

✅ **Implemented:**
- Private bridge network
- Service isolation
- Optional port exposure
- TLS support via reverse proxy

### Data Security

✅ **Implemented:**
- Environment variable validation
- Secret management support
- Volume encryption ready
- Backup capabilities

## Performance Features

### Build Optimization

- Multi-stage builds
- Layer caching
- Minimal base image
- .dockerignore optimization

### Runtime Optimization

- Health checks with retries
- Resource limits
- Connection pooling (asyncpg)
- Rate limiting

### Scalability

- Horizontal scaling ready
- Multiple workers support
- Database connection pooling
- Stateless design

## Monitoring and Observability

### Health Checks

- Endpoint: `/health`
- Readiness: `/health/ready`
- Docker health checks
- Automated monitoring script

### Logging

- Structured logging
- Docker logs integration
- Log rotation
- Centralized logging ready

### Metrics

- Resource usage tracking
- Request rate limiting
- Database performance
- External monitoring ready

## Backup and Recovery

### Database Backups

```bash
# Manual backup
make backup

# Automated (crontab)
0 2 * * * cd /path/to/docker && make backup
```

### Volume Backups

```bash
# Backup volumes
docker run --rm \
  -v fitness-postgres-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/volumes.tar.gz /data
```

### Restore

```bash
# Restore database
make restore FILE=backups/backup-20240101.sql

# Restore volumes
docker run --rm \
  -v fitness-postgres-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/volumes.tar.gz -C /
```

## Troubleshooting

### Common Issues

1. **Container won't start**
   ```bash
   docker compose logs backend
   ```

2. **Database connection failed**
   ```bash
   docker compose exec postgres pg_isready -U fitness
   ```

3. **API not responding**
   ```bash
   curl http://localhost:8000/health
   ./healthcheck.sh
   ```

4. **Out of memory**
   ```bash
   docker stats
   # Increase limits in docker-compose.yml
   ```

### Getting Help

- Run health check: `./healthcheck.sh`
- Check logs: `make logs`
- View configuration: `docker compose config`
- Test endpoints: `make test`

## Contributing

When adding new files:
1. Update this documentation
2. Add to .dockerignore if needed
3. Update Dockerfile if dependencies change
4. Test with `make build && make test`

## License

MIT License - See LICENSE file for details

---

**Generated:** 2026-01-29
**Version:** 1.0.0
**Maintainer:** Open Source Fitness Coach Contributors
