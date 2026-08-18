.PHONY: help install test lint api web stack knowledge-plan

help:
	@echo "install         install backend dependencies (editable, with dev extras)"
	@echo "test            run the backend test suite"
	@echo "lint            ruff + mypy on the backend"
	@echo "api             run the FastAPI backend"
	@echo "web             run the Next.js frontend"
	@echo "stack           run mongo + api + web in Docker"
	@echo "knowledge-plan  dry-run the RAG pipeline (no provider calls)"

install:
	cd apps/api && pip install -e ".[dev]"

test:
	cd apps/api && python -m pytest

lint:
	cd apps/api && ruff check . && mypy libra

api:
	cd apps/api && python -m libra.main serve --reload

web:
	cd apps/web && npm run dev

stack:
	docker compose -f infra/docker/docker-compose.yml up --build

knowledge-plan:
	cd apps/api && python -m libra.main knowledge-plan
