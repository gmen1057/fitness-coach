# Deployment Guide

Complete deployment guide for Open Source Fitness Coach in various environments.

## Table of Contents

- [Quick Start](#quick-start)
- [Production Deployment](#production-deployment)
- [Development Setup](#development-setup)
- [Cloud Platforms](#cloud-platforms)
- [Security Hardening](#security-hardening)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Quick Start

### 1. Automated Setup

The fastest way to get started:

```bash
cd docker
./start.sh
```

This script will:
1. Check prerequisites (Docker, Compose)
2. Create `.env` from template
3. Validate configuration
4. Build and start services
5. Run health checks

### 2. Manual Setup

If you prefer manual control:

```bash
# 1. Configure environment
cd docker
cp .env.example .env
nano .env  # Add your API keys

# 2. Build and start
docker compose up -d

# 3. Check health
./healthcheck.sh
```

### 3. Using Makefile

Convenient commands for common tasks:

```bash
# Start services
make start

# View logs
make logs

# Run health check
make health

# Stop services
make stop
```

See `make help` for all available commands.

## Production Deployment

### Prerequisites

- Server with 2GB+ RAM and 10GB+ disk
- Docker 24.0+ and Compose V2
- Domain name (optional, for SSL)
- API key for chosen AI provider

### Step 1: Server Preparation

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Add user to docker group (optional)
usermod -aG docker $USER

# Install Docker Compose (if not included)
apt install docker-compose-plugin
```

### Step 2: Clone and Configure

```bash
# Clone repository
git clone https://github.com/yourusername/fitness-coach.git
cd fitness-coach/docker

# Configure environment
cp .env.example .env

# Edit with production values
nano .env
```

**Critical production settings:**

```env
# Strong database password
POSTGRES_PASSWORD=<generate-strong-password>

# AI provider (choose one)
FITNESS_AI_PROVIDER=anthropic
FITNESS_ANTHROPIC_API_KEY=sk-ant-...

# RAG for better memory
FITNESS_RAG_PROVIDER=pgvector
FITNESS_EMBEDDING_PROVIDER=openai
FITNESS_OPENAI_API_KEY=sk-...

# Security
FITNESS_DEBUG=false
FITNESS_CORS_ORIGINS=["https://yourdomain.com"]

# Rate limiting (adjust based on load)
FITNESS_RATE_LIMIT_CHAT=5/minute
```

### Step 3: Deploy

```bash
# Build images
docker compose build --no-cache

# Start services
docker compose up -d

# Verify
./healthcheck.sh
```

### Step 4: Configure Reverse Proxy

#### Using Nginx

```bash
# Install Nginx
apt install nginx certbot python3-certbot-nginx

# Create config
nano /etc/nginx/sites-available/fitness-coach
```

```nginx
server {
    listen 80;
    server_name fitness.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # SSE streaming support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        chunked_transfer_encoding off;
    }
}
```

```bash
# Enable site
ln -s /etc/nginx/sites-available/fitness-coach /etc/nginx/sites-enabled/

# Test config
nginx -t

# Reload Nginx
systemctl reload nginx

# Get SSL certificate
certbot --nginx -d fitness.yourdomain.com
```

#### Using Traefik

```yaml
# docker-compose.prod.yml
services:
  traefik:
    image: traefik:v2.10
    command:
      - "--api.insecure=false"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=you@example.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik-certs:/letsencrypt
    networks:
      - fitness-network

  backend:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.fitness.rule=Host(`fitness.yourdomain.com`)"
      - "traefik.http.routers.fitness.entrypoints=websecure"
      - "traefik.http.routers.fitness.tls.certresolver=letsencrypt"
      - "traefik.http.services.fitness.loadbalancer.server.port=8000"

volumes:
  traefik-certs:
```

### Step 5: Systemd Service (Optional)

For automatic startup on reboot:

```bash
nano /etc/systemd/system/fitness-coach.service
```

```ini
[Unit]
Description=Open Source Fitness Coach
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/fitness-coach/docker
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
systemctl enable fitness-coach.service
systemctl start fitness-coach.service
```

## Development Setup

Development mode with hot-reload and debugging tools:

```bash
# Start with dev configuration
make dev

# Or manually
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Access pgAdmin
# URL: http://localhost:5050
# Email: admin@fitness.local
# Password: admin
```

**Development features:**
- Hot-reload on code changes
- Debug logging enabled
- pgAdmin for database management
- Exposed PostgreSQL port (5432)
- All dependencies installed

**Add pgAdmin server:**
1. Open http://localhost:5050
2. Add Server → General: "Fitness Coach"
3. Connection tab:
   - Host: postgres
   - Port: 5432
   - Database: fitness
   - Username: fitness
   - Password: (from .env)

## Cloud Platforms

### DigitalOcean

```bash
# Create Droplet (2GB RAM minimum)
doctl compute droplet create fitness-coach \
  --image docker-20-04 \
  --size s-2vcpu-2gb \
  --region nyc1

# SSH and deploy
ssh root@<droplet-ip>
git clone https://github.com/yourusername/fitness-coach.git
cd fitness-coach/docker
./start.sh
```

### AWS ECS

See `aws/README.md` for Fargate deployment guide.

### Google Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT-ID/fitness-coach

# Deploy
gcloud run deploy fitness-coach \
  --image gcr.io/PROJECT-ID/fitness-coach \
  --platform managed \
  --region us-central1 \
  --set-env-vars FITNESS_AI_PROVIDER=anthropic \
  --set-secrets FITNESS_ANTHROPIC_API_KEY=fitness-api-key:latest
```

### Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Launch
fly launch

# Deploy
fly deploy
```

## Security Hardening

### 1. Database Security

```env
# Use strong passwords
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Restrict access
FITNESS_DATABASE_URL=postgresql+asyncpg://fitness:PASSWORD@postgres:5432/fitness
```

### 2. Network Security

```yaml
# docker-compose.yml
services:
  postgres:
    networks:
      - fitness-network
    # Don't expose port to host in production
    # ports:
    #   - "5432:5432"
```

### 3. Secrets Management

Don't commit `.env` file. Use Docker secrets instead:

```bash
# Create secrets
echo "sk-ant-..." | docker secret create anthropic_api_key -
echo "password" | docker secret create postgres_password -

# Update compose file
services:
  backend:
    secrets:
      - anthropic_api_key
    environment:
      FITNESS_ANTHROPIC_API_KEY_FILE: /run/secrets/anthropic_api_key

secrets:
  anthropic_api_key:
    external: true
  postgres_password:
    external: true
```

### 4. Rate Limiting

Adjust based on expected load:

```env
# Conservative limits
FITNESS_RATE_LIMIT_CHAT=5/minute
FITNESS_RATE_LIMIT_DEFAULT=60/minute
```

Add Nginx rate limiting:

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
    location / {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://localhost:8000;
    }
}
```

### 5. HTTPS Only

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name fitness.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

## Monitoring

### 1. Health Checks

```bash
# Automated monitoring
*/5 * * * * cd /path/to/fitness-coach/docker && ./healthcheck.sh || mail -s "Fitness Coach Down" admin@example.com
```

### 2. Logging

Centralized logging with Loki:

```yaml
# docker-compose.monitoring.yml
services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: -config.file=/etc/promtail/config.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
```

### 3. Metrics

Add Prometheus exporter:

```python
# app/main.py
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(...)

# Add metrics
Instrumentator().instrument(app).expose(app)
```

### 4. Uptime Monitoring

Use external services:
- UptimeRobot (free)
- Pingdom
- StatusCake

Monitor endpoint: `https://yourdomain.com/health`

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs backend

# Common issues:
# 1. Missing API key
grep API_KEY .env

# 2. Database not ready
docker compose logs postgres

# 3. Port already in use
netstat -tlnp | grep 8000
```

### Database connection failed

```bash
# Test connection
docker compose exec postgres psql -U fitness -d fitness -c "SELECT 1"

# Check network
docker network inspect fitness-network

# Recreate database
docker compose down postgres
docker volume rm fitness-postgres-data
docker compose up -d postgres
```

### Out of memory

```bash
# Check usage
docker stats

# Increase limits in docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G
```

### Slow responses

```bash
# Check AI provider status
curl https://status.anthropic.com

# Check database performance
docker compose exec postgres psql -U fitness -d fitness -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;"

# Enable query logging
docker compose exec postgres psql -U fitness -d fitness -c "
ALTER SYSTEM SET log_min_duration_statement = 100;
SELECT pg_reload_conf();"
```

### SSL certificate issues

```bash
# Test certificate
certbot certificates

# Renew manually
certbot renew --force-renewal

# Check Nginx config
nginx -t
```

## Backup and Recovery

### Automated Backups

```bash
# Create backup script
cat > /root/backup-fitness.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=/backups/fitness
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Database backup
cd /path/to/fitness-coach/docker
docker compose exec -T postgres pg_dump -U fitness fitness | \
  gzip > $BACKUP_DIR/db-$DATE.sql.gz

# Volume backup
docker run --rm \
  -v fitness-postgres-data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/volumes-$DATE.tar.gz /data

# Keep only last 7 days
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /root/backup-fitness.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /root/backup-fitness.sh" | crontab -
```

### Disaster Recovery

```bash
# Stop services
docker compose down

# Restore database
gunzip < /backups/fitness/db-20240101_020000.sql.gz | \
  docker compose exec -T postgres psql -U fitness fitness

# Restore volumes
docker run --rm \
  -v fitness-postgres-data:/data \
  -v /backups/fitness:/backup \
  alpine tar xzf /backup/volumes-20240101_020000.tar.gz -C /

# Start services
docker compose up -d
```

## Performance Optimization

### Database Tuning

```yaml
# docker-compose.yml
services:
  postgres:
    command:
      - postgres
      - -c
      - shared_buffers=256MB
      - -c
      - effective_cache_size=1GB
      - -c
      - work_mem=16MB
      - -c
      - maintenance_work_mem=64MB
      - -c
      - max_connections=100
```

### Backend Scaling

Run multiple workers:

```yaml
services:
  backend:
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"
    deploy:
      replicas: 3
```

### Caching

Add Redis for response caching:

```yaml
services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

## Updates and Maintenance

### Update Application

```bash
# Pull latest code
git pull

# Rebuild and restart
make update

# Or manually
docker compose build --no-cache
docker compose up -d
```

### Update Dependencies

```bash
# Update base image
docker pull python:3.12-slim

# Update PostgreSQL
docker pull pgvector/pgvector:pg16

# Rebuild
docker compose build
```

## Getting Help

- Documentation: `/docs/README.md`
- GitHub Issues: https://github.com/yourusername/fitness-coach/issues
- Discord: https://discord.gg/your-server
- Email: support@example.com
