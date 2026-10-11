# =============================================================================
# GhostGoat - Unified Build & Orchestration
# =============================================================================
#
#   make install      → pip install -e ".[full]" (supported install route)
#   make install-core → pip install -e . (core runtime only)
#   make run          → python main.py (canonical entry point)
#   make test         → run test suite locally
#   make start        → Docker: build + start + health check
#   make start-full   → Docker: includes neo4j + ollama
#   make start-prod   → Docker: production stack
#
# =============================================================================
.PHONY: help install install-core run run-api run-dash \
        start start-full start-prod \
        build build-prod build-all \
        up up-full down restart logs logs-ghost status \
        prod-up shell redis-cli \
        test test-docker smoke \
        clean clean-data \
        health-wait

COMPOSE := docker compose
IMAGE   := ghostgoat
HEALTH_URL := http://localhost:8420/api/health
HEALTH_TIMEOUT := 60

# Uses whichever Python is active (venv, conda, system). Override: make PYTHON=python3.11
PYTHON  ?= python
PIP     ?= $(PYTHON) -m pip
PYTEST  ?= $(PYTHON) -m pytest

# ---------------------------------------------------------------------------
# First-time install (no Docker required)
# ---------------------------------------------------------------------------
install: ## Install core + all extras (pip install -e ".[full]")
	$(PIP) install -e ".[full]"

install-core: ## Install core runtime only (pip install -e .)
	$(PIP) install -e .

# ---------------------------------------------------------------------------
# Local run (no Docker required) — canonical entry point is main.py
# ---------------------------------------------------------------------------
run: ## Start API server + dashboard
	$(PYTHON) main.py

run-api: ## Start API server only
	$(PYTHON) main.py --api-only

run-dash: ## Start dashboard only
	$(PYTHON) main.py --dash-only

# ---------------------------------------------------------------------------
# Default target — unified start
# ---------------------------------------------------------------------------
start: build up health-wait smoke ## Docker: build, start, verify health, smoke test
	@echo ""
	@echo "============================================================"
	@echo "  GhostGoat is running"
	@echo "  API:      $(HEALTH_URL)"
	@echo "  Logs:     make logs"
	@echo "  Stop:     make down"
	@echo "============================================================"

start-full: build up-full health-wait smoke ## Full stack (+ neo4j + ollama)
	@echo ""
	@echo "  GhostGoat (full) is running"

start-prod: build-prod prod-up health-wait ## Production stack
	@echo ""
	@echo "  GhostGoat (production) is running"

# ---------------------------------------------------------------------------
# Health gate — blocks until the orchestrator is ready
# ---------------------------------------------------------------------------
health-wait:
	@echo "Waiting for orchestrator health ($(HEALTH_TIMEOUT)s timeout) ..."
	@elapsed=0; \
	while [ $$elapsed -lt $(HEALTH_TIMEOUT) ]; do \
		if curl -sf $(HEALTH_URL) > /dev/null 2>&1; then \
			echo "  Orchestrator healthy ($$elapsed""s)"; \
			exit 0; \
		fi; \
		sleep 2; \
		elapsed=$$((elapsed + 2)); \
	done; \
	echo "  WARN: health endpoint not reachable after $(HEALTH_TIMEOUT)s"; \
	echo "  The orchestrator may still be starting — check: make logs"; \
	exit 1

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
build: ## Build development image
	$(COMPOSE) build ghostgoat

build-prod: ## Build production image
	$(COMPOSE) build ghostgoat-prod

build-all: ## Build all images
	$(COMPOSE) --profile full --profile prod build

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
up: ## Start core services (ghostgoat + redis + chromadb)
	$(COMPOSE) up -d

up-full: ## Start all services including neo4j and ollama
	$(COMPOSE) --profile full up -d

down: ## Stop all services
	$(COMPOSE) --profile full --profile prod down

restart: ## Restart all running services
	$(COMPOSE) restart

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

logs-ghost: ## Tail logs from ghostgoat only
	$(COMPOSE) logs -f ghostgoat

status: ## Show status of all services
	$(COMPOSE) ps -a

# ---------------------------------------------------------------------------
# Production
# ---------------------------------------------------------------------------
prod-up: ## Start production stack
	$(COMPOSE) --profile prod up -d ghostgoat-prod redis chromadb

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------
shell: ## Open a shell in the ghostgoat container
	$(COMPOSE) exec ghostgoat bash

redis-cli: ## Open redis-cli
	$(COMPOSE) exec redis redis-cli

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------
test: ## Run full test suite locally (no Docker)
	$(PYTEST) tests/ -v

smoke: ## Run smoke tests inside running container
	$(COMPOSE) exec ghostgoat python tests/smoke_test.py

test-docker: smoke ## Alias for smoke

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
clean: ## Remove containers, volumes, and built images
	$(COMPOSE) --profile full --profile prod down -v --rmi local
	@echo "Cleaned up containers, volumes, and local images."

clean-data: ## Remove persistent data volumes (destructive!)
	@echo "WARNING: This will delete all persistent data!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	$(COMPOSE) --profile full --profile prod down -v

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
