# Docker Deployment - File Index

Complete index of all Docker deployment files with descriptions and quick links.

## Directory: `/opt/helper/opensource/fitness-coach/docker/`

### Core Deployment Files

| File | Size | Description |
|------|------|-------------|
| `Dockerfile.backend` | 3.3K | Multi-stage production Dockerfile with security hardening |
| `docker-compose.yml` | 5.2K | Production configuration with PostgreSQL + backend |
| `docker-compose.dev.yml` | 2.9K | Development overrides with pgAdmin and hot-reload |
| `.dockerignore` | 436B | Build exclusions for faster builds |
| `.env.example` | 3.0K | Environment configuration template |
| `init-db.sh` | 1.0K | PostgreSQL initialization script (pgvector) |

### Automation Scripts

| File | Size | Purpose |
|------|------|---------|
| `start.sh` | 4.2K | Interactive deployment wizard |
| `healthcheck.sh` | 5.6K | Comprehensive health monitoring |
| `verify.sh` | 4.8K | File validation and checks |
| `Makefile` | 4.4K | Command shortcuts (make help) |

### Documentation

| File | Lines | Size | Contents |
|------|-------|------|----------|
| `README.md` | 480 | 12K | Docker quick start guide |
| `DEPLOYMENT.md` | 708 | 16K | Production deployment guide |
| `FILES.md` | 513 | 12K | Complete file reference |
| `SUMMARY.md` | 442 | 11K | Project summary and overview |
| `INDEX.md` | - | - | This file |

### Requirements Files

Directory: `/opt/helper/opensource/fitness-coach/backend/requirements/`

| File | Purpose | Dependencies |
|------|---------|--------------|
| `base.txt` | Core only | FastAPI, SQLAlchemy, uvicorn |
| `cloud.txt` | Cloud AI | base + anthropic + openai + pgvector |
| `ollama.txt` | Local AI | base + pgvector |
| `all.txt` | Everything | cloud + dev tools |

## Quick Navigation

### Getting Started

1. **First time setup:**
   ```bash
   ./start.sh
   ```

2. **Manual setup:**
   - Read: `README.md`
   - Configure: `.env.example` → `.env`
   - Deploy: `docker-compose.yml`

3. **Production deployment:**
   - Guide: `DEPLOYMENT.md`
   - Security: `docker-compose.yml` (hardening enabled)
   - Monitoring: `healthcheck.sh`

### Documentation by Use Case

| Need | Read This |
|------|-----------|
| Quick start | `README.md` |
| Production deployment | `DEPLOYMENT.md` |
| File descriptions | `FILES.md` |
| Project overview | `SUMMARY.md` |
| File index | `INDEX.md` (this file) |

### Scripts by Purpose

| Purpose | Run This |
|---------|----------|
| Deploy application | `./start.sh` |
| Check health | `./healthcheck.sh` |
| Verify setup | `./verify.sh` |
| Common tasks | `make help` |

## File Relationships

```
Start Here
    │
    ├─→ Quick Start
    │   └─→ start.sh → .env.example → docker-compose.yml → Dockerfile.backend
    │
    ├─→ Production
    │   └─→ DEPLOYMENT.md → docker-compose.yml → healthcheck.sh
    │
    └─→ Development
        └─→ README.md → docker-compose.dev.yml → Makefile
```

## Dependency Tree

```
docker-compose.yml
├── .env.example (template)
├── Dockerfile.backend
│   ├── backend/requirements/cloud.txt (default)
│   │   ├── base.txt
│   │   ├── anthropic
│   │   ├── openai
│   │   └── pgvector
│   └── backend/app/* (application code)
├── init-db.sh (postgres initialization)
└── docker-compose.dev.yml (optional, development)
    └── pgAdmin service
```

## File Purposes

### Deployment

- **Dockerfile.backend** - Builds the backend container image
- **docker-compose.yml** - Orchestrates multi-container deployment
- **docker-compose.dev.yml** - Adds development-specific services
- **.dockerignore** - Speeds up builds by excluding files
- **.env.example** - Template for environment configuration
- **init-db.sh** - Sets up PostgreSQL with pgvector extension

### Automation

- **start.sh** - Automates initial setup and deployment
- **healthcheck.sh** - Monitors service health and status
- **verify.sh** - Validates file structure and configuration
- **Makefile** - Provides convenient command shortcuts

### Documentation

- **README.md** - Primary documentation for Docker deployment
- **DEPLOYMENT.md** - Detailed production deployment guide
- **FILES.md** - Complete reference for all files
- **SUMMARY.md** - High-level project overview
- **INDEX.md** - Navigation and file index (this file)

### Dependencies

- **base.txt** - Minimal core dependencies
- **cloud.txt** - Production dependencies with cloud AI
- **ollama.txt** - Local AI dependencies
- **all.txt** - All dependencies including dev tools

## Usage Patterns

### Pattern 1: Quick Start (Recommended for New Users)

```bash
cd docker
./start.sh  # Automated setup
```

Reads: `start.sh` → `.env.example` → `docker-compose.yml`

### Pattern 2: Manual Setup (Advanced Users)

```bash
cd docker
cp .env.example .env
nano .env
docker compose up -d
./healthcheck.sh
```

Reads: `README.md` → `.env.example` → `docker-compose.yml`

### Pattern 3: Production Deployment

```bash
cd docker
# Read DEPLOYMENT.md first
cp .env.example .env
# Configure production settings
docker compose build --no-cache
docker compose up -d
./healthcheck.sh
```

Reads: `DEPLOYMENT.md` → `.env.example` → `docker-compose.yml`

### Pattern 4: Development

```bash
cd docker
cp .env.example .env
make dev
# Or: docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Reads: `README.md` → `docker-compose.dev.yml` → `Makefile`

## Makefile Commands Reference

Quick reference for all available make commands:

```bash
make help          # Show all commands
make start         # Start production services
make dev           # Start development mode
make stop          # Stop all services
make restart       # Restart services
make logs          # Follow all logs
make logs-backend  # Backend logs only
make logs-db       # Database logs only
make health        # Run health check
make build         # Rebuild images
make clean         # Remove all (⚠️ deletes data)
make migrate       # Run database migrations
make migrate-create MSG="description"  # Create new migration
make backup        # Backup database
make restore FILE=path  # Restore database
make shell-backend # Open backend shell
make shell-db      # Open PostgreSQL shell
make ps            # Show running containers
make stats         # Show resource usage
make config        # Validate configuration
make pull          # Pull latest images
make update        # Update and restart
make test          # Test API endpoints
```

## Environment Variables Reference

Key variables in `.env.example`:

### Required
- `POSTGRES_PASSWORD` - Database password
- `FITNESS_AI_PROVIDER` - AI provider (anthropic/openai/ollama)
- `FITNESS_ANTHROPIC_API_KEY` or `FITNESS_OPENAI_API_KEY`

### Optional
- `INSTALL_EXTRAS` - Dependencies to install (base/cloud/ollama/all)
- `FITNESS_RAG_PROVIDER` - RAG backend (pgvector/sqlite/none)
- `FITNESS_EMBEDDING_PROVIDER` - Embeddings (openai/ollama/none)
- `FITNESS_DEBUG` - Debug mode (true/false)
- `FITNESS_CORS_ORIGINS` - CORS allowed origins
- `FITNESS_RATE_LIMIT_CHAT` - Chat rate limit
- `BACKEND_PORT` - Backend port (default: 8000)

## Health Check Endpoints

All available health check endpoints:

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health` | Basic health | `{"status": "healthy"}` |
| `/health/ready` | Readiness check | `{"status": "ready", "ai_provider": "..."}` |
| `/` | API info | `{"app": "...", "status": "healthy"}` |

## Volume Reference

Docker volumes created by the deployment:

| Volume | Purpose | Backup Priority |
|--------|---------|----------------|
| `fitness-postgres-data` | PostgreSQL database | 🔴 Critical |
| `fitness-app-data` | RAG vectors, app data | 🟡 Important |
| `fitness-app-logs` | Application logs | 🟢 Optional |
| `fitness-pgadmin-data` | pgAdmin settings (dev) | 🟢 Optional |

## Port Reference

Default ports used by the application:

| Port | Service | Access |
|------|---------|--------|
| 8000 | Backend API | http://localhost:8000 |
| 5432 | PostgreSQL | localhost:5432 (dev only) |
| 5050 | pgAdmin | http://localhost:5050 (dev only) |

## File Sizes

Total size of deployment files:

```
Docker files:     ~21K (configs + scripts)
Documentation:    ~50K (guides + references)
Requirements:     ~3K  (Python dependencies)
Total:            ~74K
```

## Validation Checklist

Before deploying, ensure:

- [ ] All files present (`./verify.sh`)
- [ ] Scripts executable
- [ ] `.env` configured from `.env.example`
- [ ] Docker and Compose installed
- [ ] Ports 8000 (and 5432 for dev) available
- [ ] API key added to `.env`
- [ ] Database password set in `.env`

## Getting Help

| Issue | Solution |
|-------|----------|
| Files missing | Run `./verify.sh` |
| Services not starting | Check `docker compose logs` |
| Health check failing | Run `./healthcheck.sh` |
| Configuration invalid | Run `docker compose config` |
| Need general help | Read `README.md` |
| Production deployment | Read `DEPLOYMENT.md` |
| File descriptions | Read `FILES.md` |

## Updates and Maintenance

To update the deployment:

1. Pull latest code: `git pull`
2. Rebuild images: `make build`
3. Restart services: `make restart`
4. Verify health: `make health`

Or use the all-in-one command:
```bash
make update
```

---

**Index Version:** 1.0.0
**Last Updated:** 2026-01-29
**Total Files:** 16 (deployment) + 4 (requirements)
**Total Documentation:** 5 guides (~2,600 lines)
