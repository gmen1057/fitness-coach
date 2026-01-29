#!/bin/bash
# =============================================================================
# Verification Script - Check Docker Deployment Files
# =============================================================================
# Verifies all required files are present and valid

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}━━━ $1 ━━━${NC}"
}

print_ok() {
    echo -e "${GREEN}✓${NC} $1"
}

print_fail() {
    echo -e "${RED}✗${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

ALL_OK=true

print_header "Verifying Docker Deployment Files"

# Check required files
print_header "Required Files"

FILES=(
    "Dockerfile.backend"
    "docker-compose.yml"
    "docker-compose.dev.yml"
    ".dockerignore"
    ".env.example"
    "init-db.sh"
    "start.sh"
    "healthcheck.sh"
    "Makefile"
    "README.md"
    "DEPLOYMENT.md"
    "FILES.md"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        print_ok "$file exists"
    else
        print_fail "$file missing"
        ALL_OK=false
    fi
done

# Check executable permissions
print_header "Executable Scripts"

SCRIPTS=(
    "init-db.sh"
    "start.sh"
    "healthcheck.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -x "$script" ]; then
        print_ok "$script is executable"
    else
        print_warn "$script not executable (running chmod +x)"
        chmod +x "$script"
    fi
done

# Check requirements files
print_header "Requirements Files"

REQ_FILES=(
    "../backend/requirements/base.txt"
    "../backend/requirements/cloud.txt"
    "../backend/requirements/ollama.txt"
    "../backend/requirements/all.txt"
)

for file in "${REQ_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_ok "$(basename $file) exists"
    else
        print_fail "$(basename $file) missing"
        ALL_OK=false
    fi
done

# Validate docker-compose.yml
print_header "Docker Compose Validation"

if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    print_fail "Docker Compose not found"
    ALL_OK=false
    COMPOSE_CMD=""
fi

if [ -n "$COMPOSE_CMD" ]; then
    if $COMPOSE_CMD -f docker-compose.yml config > /dev/null 2>&1; then
        print_ok "docker-compose.yml is valid"
    else
        print_fail "docker-compose.yml has errors"
        ALL_OK=false
    fi

    if $COMPOSE_CMD -f docker-compose.yml -f docker-compose.dev.yml config > /dev/null 2>&1; then
        print_ok "docker-compose.dev.yml is valid"
    else
        print_fail "docker-compose.dev.yml has errors"
        ALL_OK=false
    fi
fi

# Validate Dockerfile
print_header "Dockerfile Validation"

if [ -f "Dockerfile.backend" ]; then
    # Check for required instructions
    if grep -q "FROM python:3.12-slim" Dockerfile.backend; then
        print_ok "Base image specified"
    else
        print_warn "Unexpected base image"
    fi

    if grep -q "ARG INSTALL_EXTRAS" Dockerfile.backend; then
        print_ok "Build arguments defined"
    else
        print_warn "INSTALL_EXTRAS argument missing"
    fi

    if grep -q "USER fitness" Dockerfile.backend; then
        print_ok "Non-root user configured"
    else
        print_warn "Running as root (security risk)"
    fi

    if grep -q "HEALTHCHECK" Dockerfile.backend; then
        print_ok "Health check configured"
    else
        print_warn "No health check defined"
    fi
fi

# Check .env.example
print_header "Environment Configuration"

if [ -f ".env.example" ]; then
    REQUIRED_VARS=(
        "POSTGRES_PASSWORD"
        "FITNESS_AI_PROVIDER"
        "FITNESS_ANTHROPIC_API_KEY"
        "FITNESS_DATABASE_URL"
    )

    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^$var=" .env.example; then
            print_ok "$var defined in .env.example"
        else
            print_warn "$var missing from .env.example"
        fi
    done
fi

# Check documentation
print_header "Documentation"

DOC_FILES=(
    "README.md"
    "DEPLOYMENT.md"
    "FILES.md"
)

for doc in "${DOC_FILES[@]}"; do
    if [ -f "$doc" ]; then
        LINES=$(wc -l < "$doc")
        SIZE=$(du -h "$doc" | cut -f1)
        print_ok "$doc: $LINES lines, $SIZE"
    fi
done

# Summary
print_header "Summary"

if [ "$ALL_OK" = true ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Configure environment:  cp .env.example .env && nano .env"
    echo "  2. Quick start:            ./start.sh"
    echo "  3. Or manual start:        docker compose up -d"
    echo "  4. Check health:           ./healthcheck.sh"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some checks failed${NC}"
    echo ""
    echo "Please fix the issues above before deploying."
    echo ""
    exit 1
fi
