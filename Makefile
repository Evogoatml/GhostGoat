# =============================================================================
# GhostGoat - Unified Build & Orchestration
# =============================================================================
#
#   make install      → bootstrap everything (first-time setup)
#   make run          → start API + dashboard locally (no Docker)
#   make test         → run test suite locally
#   make start        → Docker: build + start + health check
#   make start-full   → Docker: includes neo4j + ollama
#   make start-prod   → Docker: production stack
#
# =============================================================================
.PHONY: help install run run-api run-dash agents _check_venv \
        start start-full start-prod \
        build build-prod build-all \
        up up-full down restart logs logs-ghost status \
        prod-up shell redis-cli \
        test test-docker smoke \
        clean clean-data \
        health-wait debug

COMPOSE := docker compose
IMAGE   := ghostgoat
HEALTH_URL := http://localhost:8420/api/health
HEALTH_TIMEOUT := 60

# Always use the venv Python — no manual activation needed
PYTHON  := ./venv/bin/python
PIP     := ./venv/bin/pip
PYTEST  := ./venv/bin/pytest

# Guard: abort with a clear message if venv doesn't exist yet
_check_venv:
	@test -f $(PYTHON) || { \
		echo ""; \
		echo "  venv not found. Run:  make install"; \
		echo ""; \
		exit 1; \
	}

# ---------------------------------------------------------------------------
# First-time install (no Docker required)
# ---------------------------------------------------------------------------
install: ## Bootstrap everything: system deps → venv → Python packages → dashboard → .env
	bash setup.sh

# ---------------------------------------------------------------------------
# Local run (no Docker required) — venv is used automatically
# ---------------------------------------------------------------------------
run: _check_venv ## Start API server + dashboard
	$(PYTHON) main.py

run-api: _check_venv ## Start API server only
	$(PYTHON) main.py --api-only

run-dash: _check_venv ## Start dashboard only
	$(PYTHON) main.py --dash-only

# ---------------------------------------------------------------------------
# Agent system — generate AGENT.md in every folder
# ---------------------------------------------------------------------------
agents: _check_venv ## Scan codebase and regenerate all AGENT.md files
	$(PYTHON) core/distributed_agent_system.py

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
debug: ## Run debug bootstrap: validate full system end-to-end and report failures
	python3 debug_bootstrap.py

test: _check_venv ## Run full test suite locally (no Docker)
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
