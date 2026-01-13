.PHONY: help up down logs migrate seed demo-kernel test clean ps

help:
	@echo "Governance OS - Development Commands"
	@echo ""
	@echo "  make up           - Start all services (docker compose up)"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - Tail logs from all services"
	@echo "  make ps           - Show running containers"
	@echo "  make migrate      - Run database migrations"
	@echo "  make seed         - Load treasury fixtures"
	@echo "  make demo-kernel  - Run end-to-end kernel demo (Sprint 1)"
	@echo "  make test         - Run pytest test suite"
	@echo "  make shell        - Open backend container shell"
	@echo "  make db           - Open postgres shell"
	@echo "  make clean        - Remove all containers and volumes"

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
	docker compose exec backend python -m scripts.seed_fixtures

demo-kernel:
	docker compose exec backend python -m scripts.demo_kernel

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
