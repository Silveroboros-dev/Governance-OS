.PHONY: help up down logs migrate seed demo-kernel test clean ps replay mcp evals scenarios

help:
	@echo "Governance OS - Development Commands"
	@echo ""
	@echo "Core Commands:"
	@echo "  make up           - Start all services (docker compose up)"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - Tail logs from all services"
	@echo "  make ps           - Show running containers"
	@echo "  make migrate      - Run database migrations"
	@echo "  make seed         - Load treasury fixtures"
	@echo "  make scenarios    - Load demo scenarios"
	@echo "  make demo-kernel  - Run end-to-end kernel demo"
	@echo "  make test         - Run pytest test suite"
	@echo "  make shell        - Open backend container shell"
	@echo "  make db           - Open postgres shell"
	@echo "  make clean        - Remove all containers and volumes"
	@echo ""
	@echo "Sprint 2 Commands:"
	@echo "  make replay       - Run replay harness (PACK=treasury FROM=2025-01-01 TO=2025-03-31)"
	@echo "  make mcp          - Start MCP server (for Claude Desktop)"
	@echo "  make evals        - Run evaluations (CI gate - exits 1 on failure)"

up:
	docker compose up --build -d
	@echo ""
	@echo "Services starting..."
	@echo "API: http://localhost:8000/docs"
	@echo "Postgres: localhost:5432"
	@echo ""
	@echo "Run 'make logs' to see output"

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python -m core.scripts.seed_fixtures

demo-kernel:
	docker compose exec backend python -m core.scripts.demo_kernel

test:
	docker compose exec backend pytest -v

test-critical:
	docker compose exec backend pytest -v -m critical

test-cov:
	docker compose exec backend pytest --cov=core --cov-report=term-missing

test-local:
	cd core && .venv/bin/pytest -v

shell:
	docker compose exec backend /bin/bash

db:
	docker compose exec postgres psql -U govos -d governance_os

clean:
	docker compose down -v
	@echo "Removed all containers and volumes"

# Sprint 2: Replay harness
# Usage: make replay PACK=treasury FROM=2025-01-01 TO=2025-03-31
replay:
	@echo "Running replay harness..."
	python -m replay.cli run --pack=$(or $(PACK),treasury) $(if $(FROM),--from $(FROM)) $(if $(TO),--to $(TO)) -v

# Sprint 2: MCP Server
mcp:
	@echo "Starting MCP server (governance-os)..."
	@echo "Configure in Claude Desktop: ~/.config/claude/claude_desktop_config.json"
	python -m mcp.server

# Sprint 2: Evaluations (CI gate)
evals:
	@echo "Running evaluations..."
	python -m evals.runner -v
	@echo "Evaluations complete."

# Load demo scenarios
scenarios:
	docker compose exec backend python -m core.scripts.seed_fixtures --scenarios
