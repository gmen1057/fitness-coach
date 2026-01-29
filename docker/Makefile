# =============================================================================
# Makefile for Open Source Fitness Coach Docker Deployment
# =============================================================================

.PHONY: help start stop restart logs build clean health dev prod migrate backup restore

# Detect compose command
COMPOSE := $(shell command -v docker-compose 2>/dev/null || echo "docker compose")

# Colors
GREEN  := \033[0;32m
YELLOW := \033[1;33m
NC     := \033[0m

help: ## Show this help message
	@echo "$(GREEN)Open Source Fitness Coach - Docker Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make $(YELLOW)<target>$(NC)\n\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

start: ## Start services in production mode
	@echo "$(GREEN)Starting services in production mode...$(NC)"
	$(COMPOSE) up -d
	@$(MAKE) health

stop: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(NC)"
	$(COMPOSE) down

restart: ## Restart all services
	@echo "$(YELLOW)Restarting services...$(NC)"
	$(COMPOSE) restart
	@$(MAKE) health

logs: ## Follow logs from all services
	$(COMPOSE) logs -f

logs-backend: ## Follow backend logs only
	$(COMPOSE) logs -f backend

logs-db: ## Follow postgres logs only
	$(COMPOSE) logs -f postgres

build: ## Build/rebuild Docker images
	@echo "$(GREEN)Building Docker images...$(NC)"
	$(COMPOSE) build --no-cache

clean: ## Stop services and remove volumes (WARNING: deletes data)
	@echo "$(YELLOW)⚠ This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(COMPOSE) down -v; \
		echo "$(GREEN)Cleanup complete$(NC)"; \
	else \
		echo "Cancelled"; \
	fi

health: ## Run health checks
	@./healthcheck.sh

dev: ## Start services in development mode
	@echo "$(GREEN)Starting services in development mode...$(NC)"
	$(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up -d
	@$(MAKE) health

prod: ## Start services in production mode (alias for start)
	@$(MAKE) start

migrate: ## Run database migrations
	@echo "$(GREEN)Running database migrations...$(NC)"
	$(COMPOSE) exec backend alembic upgrade head

migrate-create: ## Create new migration (usage: make migrate-create MSG="description")
	@if [ -z "$(MSG)" ]; then \
		echo "$(YELLOW)Usage: make migrate-create MSG=\"description\"$(NC)"; \
		exit 1; \
	fi
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(MSG)"

backup: ## Backup database to backups/backup-TIMESTAMP.sql
	@echo "$(GREEN)Creating database backup...$(NC)"
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	$(COMPOSE) exec -T postgres pg_dump -U fitness fitness > backups/backup-$$TIMESTAMP.sql; \
	echo "$(GREEN)Backup saved to backups/backup-$$TIMESTAMP.sql$(NC)"

restore: ## Restore database from backup (usage: make restore FILE=backups/backup.sql)
	@if [ -z "$(FILE)" ]; then \
		echo "$(YELLOW)Usage: make restore FILE=backups/backup.sql$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)⚠ This will overwrite the current database!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cat $(FILE) | $(COMPOSE) exec -T postgres psql -U fitness fitness; \
		echo "$(GREEN)Database restored from $(FILE)$(NC)"; \
	else \
		echo "Cancelled"; \
	fi

shell-backend: ## Open shell in backend container
	$(COMPOSE) exec backend sh

shell-db: ## Open PostgreSQL shell
	$(COMPOSE) exec postgres psql -U fitness fitness

ps: ## Show running containers
	$(COMPOSE) ps

stats: ## Show resource usage statistics
	docker stats --no-stream $$($(COMPOSE) ps -q)

config: ## Validate and view docker-compose configuration
	$(COMPOSE) config

pull: ## Pull latest images
	$(COMPOSE) pull

update: ## Update services (pull + build + restart)
	@echo "$(GREEN)Updating services...$(NC)"
	@$(MAKE) pull
	@$(MAKE) build
	@$(MAKE) restart
	@echo "$(GREEN)Update complete!$(NC)"

test: ## Test API endpoints
	@echo "$(GREEN)Testing API endpoints...$(NC)"
	@curl -sf http://localhost:8000/health && echo "$(GREEN)✓ Health check passed$(NC)" || echo "$(YELLOW)✗ Health check failed$(NC)"
	@curl -sf http://localhost:8000/health/ready && echo "$(GREEN)✓ Readiness check passed$(NC)" || echo "$(YELLOW)✗ Readiness check failed$(NC)"
	@curl -sf http://localhost:8000/ | jq . && echo "$(GREEN)✓ API responding$(NC)" || echo "$(YELLOW)✗ API not responding$(NC)"

.DEFAULT_GOAL := help
