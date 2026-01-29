#!/bin/bash
# =============================================================================
# Health Check Script for Open Source Fitness Coach
# =============================================================================
# Comprehensive health monitoring for all services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Detect compose command
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_service_status() {
    local service=$1
    local status=$($COMPOSE_CMD ps -q $service 2>/dev/null)

    if [ -z "$status" ]; then
        print_error "$service: Not running"
        return 1
    fi

    local health=$(docker inspect --format='{{.State.Health.Status}}' $($COMPOSE_CMD ps -q $service) 2>/dev/null)

    if [ "$health" = "healthy" ]; then
        print_success "$service: Healthy"
        return 0
    elif [ "$health" = "unhealthy" ]; then
        print_error "$service: Unhealthy"
        return 1
    elif [ -z "$health" ]; then
        local state=$(docker inspect --format='{{.State.Status}}' $($COMPOSE_CMD ps -q $service) 2>/dev/null)
        if [ "$state" = "running" ]; then
            print_success "$service: Running (no health check)"
            return 0
        else
            print_error "$service: $state"
            return 1
        fi
    else
        print_warning "$service: $health"
        return 2
    fi
}

check_endpoint() {
    local url=$1
    local name=$2

    if curl -sf "$url" > /dev/null 2>&1; then
        print_success "$name: Accessible"
        return 0
    else
        print_error "$name: Not accessible"
        return 1
    fi
}

check_database_connection() {
    if $COMPOSE_CMD exec -T postgres pg_isready -U fitness > /dev/null 2>&1; then
        print_success "Database: Connection OK"
        return 0
    else
        print_error "Database: Connection failed"
        return 1
    fi
}

get_resource_usage() {
    local service=$1
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep $service || echo "N/A"
}

# Main health check
print_header "Open Source Fitness Coach - Health Check"

ALL_HEALTHY=true

# Check Docker daemon
print_header "Docker Daemon"
if docker info > /dev/null 2>&1; then
    print_success "Docker daemon: Running"
else
    print_error "Docker daemon: Not running"
    exit 1
fi

# Check services
print_header "Service Status"
check_service_status "postgres" || ALL_HEALTHY=false
check_service_status "backend" || ALL_HEALTHY=false

# Check database connection
print_header "Database Connectivity"
check_database_connection || ALL_HEALTHY=false

# Check pgvector extension
if $COMPOSE_CMD exec -T postgres psql -U fitness -d fitness -c "SELECT extname FROM pg_extension WHERE extname='vector'" 2>/dev/null | grep -q vector; then
    print_success "pgvector extension: Installed"
else
    print_warning "pgvector extension: Not found (RAG may not work)"
fi

# Check API endpoints
print_header "API Endpoints"
check_endpoint "http://localhost:8000" "Backend API" || ALL_HEALTHY=false
check_endpoint "http://localhost:8000/health" "Health endpoint" || ALL_HEALTHY=false
check_endpoint "http://localhost:8000/health/ready" "Readiness endpoint" || ALL_HEALTHY=false

# Check API response
print_header "API Response"
RESPONSE=$(curl -s http://localhost:8000/ 2>/dev/null)
if echo "$RESPONSE" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
    print_success "API status: $(echo $RESPONSE | jq -r '.status')"
    print_success "AI provider: $(echo $RESPONSE | jq -r '.ai_provider')"
    print_success "RAG provider: $(echo $RESPONSE | jq -r '.rag_provider')"
else
    print_error "API response: Invalid or unhealthy"
    ALL_HEALTHY=false
fi

# Resource usage
print_header "Resource Usage"
echo ""
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}" | grep -E "NAME|fitness"

# Volume usage
print_header "Volume Usage"
echo ""
docker volume ls --filter name=fitness --format "table {{.Name}}\t{{.Driver}}" | head -10

# Recent logs
print_header "Recent Backend Logs (last 5 lines)"
$COMPOSE_CMD logs --tail=5 backend

# Network info
print_header "Network Configuration"
if docker network inspect fitness-network > /dev/null 2>&1; then
    print_success "Network: fitness-network exists"
    CONNECTED=$(docker network inspect fitness-network --format='{{range .Containers}}{{.Name}} {{end}}')
    print_success "Connected: $CONNECTED"
else
    print_error "Network: fitness-network not found"
    ALL_HEALTHY=false
fi

# Summary
print_header "Summary"
if [ "$ALL_HEALTHY" = true ]; then
    echo -e "${GREEN}✓ All systems operational${NC}"
    exit 0
else
    echo -e "${RED}✗ Some systems are unhealthy${NC}"
    echo ""
    echo "Troubleshooting steps:"
    echo "  1. Check logs:      $COMPOSE_CMD logs -f"
    echo "  2. Restart services: $COMPOSE_CMD restart"
    echo "  3. Check .env:      cat .env"
    echo "  4. Rebuild:         $COMPOSE_CMD build --no-cache"
    exit 1
fi
