#!/bin/bash
# =============================================================================
# Quick Start Script for Open Source Fitness Coach
# =============================================================================
# Automated setup and deployment script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is not installed"
        return 1
    fi
    return 0
}

# Main script
print_info "Open Source Fitness Coach - Quick Start"
echo ""

# Check prerequisites
print_info "Checking prerequisites..."
check_command docker || exit 1
check_command docker-compose || {
    print_warn "docker-compose not found, checking for 'docker compose'..."
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not available"
        exit 1
    fi
    COMPOSE_CMD="docker compose"
}
COMPOSE_CMD=${COMPOSE_CMD:-docker-compose}

print_info "Docker: $(docker --version)"
print_info "Compose: $($COMPOSE_CMD version --short)"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    print_warn ".env file not found"
    print_info "Creating from .env.example..."
    cp .env.example .env

    print_warn "Please edit .env file and add your API keys:"
    print_warn "  - POSTGRES_PASSWORD"
    print_warn "  - FITNESS_ANTHROPIC_API_KEY or FITNESS_OPENAI_API_KEY"
    echo ""
    read -p "Press Enter after configuring .env, or Ctrl+C to exit..."
fi

# Check if required variables are set
print_info "Validating configuration..."
source .env

if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "your-secure-password-here" ]; then
    print_error "POSTGRES_PASSWORD not configured in .env"
    exit 1
fi

if [ "$FITNESS_AI_PROVIDER" = "anthropic" ] && [ -z "$FITNESS_ANTHROPIC_API_KEY" ]; then
    print_error "FITNESS_ANTHROPIC_API_KEY not configured for Anthropic provider"
    exit 1
fi

if [ "$FITNESS_AI_PROVIDER" = "openai" ] && [ -z "$FITNESS_OPENAI_API_KEY" ]; then
    print_error "FITNESS_OPENAI_API_KEY not configured for OpenAI provider"
    exit 1
fi

print_info "Configuration validated"
print_info "AI Provider: $FITNESS_AI_PROVIDER"
print_info "RAG Provider: $FITNESS_RAG_PROVIDER"
echo ""

# Ask for deployment mode
echo "Select deployment mode:"
echo "  1) Production (default)"
echo "  2) Development (hot-reload, debug tools)"
read -p "Enter choice [1]: " MODE
MODE=${MODE:-1}

if [ "$MODE" = "2" ]; then
    print_info "Starting in DEVELOPMENT mode..."
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.dev.yml"
else
    print_info "Starting in PRODUCTION mode..."
    COMPOSE_FILES="-f docker-compose.yml"
fi
echo ""

# Build images
print_info "Building Docker images..."
$COMPOSE_CMD $COMPOSE_FILES build --no-cache

# Start services
print_info "Starting services..."
$COMPOSE_CMD $COMPOSE_FILES up -d

# Wait for services to be healthy
print_info "Waiting for services to be ready..."
sleep 5

# Check health
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        print_info "Backend is healthy!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 2
done
echo ""

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "Backend failed to start. Check logs with:"
    print_error "  $COMPOSE_CMD logs backend"
    exit 1
fi

# Success
echo ""
print_info "✅ Open Source Fitness Coach is running!"
echo ""
echo "Access points:"
echo "  - API:       http://localhost:${BACKEND_PORT:-8000}"
echo "  - API Docs:  http://localhost:${BACKEND_PORT:-8000}/docs"
echo "  - Health:    http://localhost:${BACKEND_PORT:-8000}/health"

if [ "$MODE" = "2" ]; then
    echo "  - pgAdmin:   http://localhost:5050"
fi

echo ""
echo "Useful commands:"
echo "  - View logs:     $COMPOSE_CMD logs -f"
echo "  - Stop services: $COMPOSE_CMD down"
echo "  - Restart:       $COMPOSE_CMD restart"
echo ""

# Show recent logs
print_info "Recent logs:"
$COMPOSE_CMD logs --tail=20

exit 0
