.PHONY: setup db test lint rules-check api web

PYTHON ?= python3
VENV := .venv/bin

setup:
	cd services/api && $(PYTHON) -m venv .venv && $(VENV)/pip install -e ".[dev]"
	cd apps/web && npm install

db:
	docker compose -f infra/docker-compose.yml up -d

test:
	cd services/api && $(VENV)/python -m pytest -q

lint:
	cd services/api && $(VENV)/ruff check src tests

rules-check:
	cd services/api && $(VENV)/python -m housefinder.regulation.check

api:
	cd services/api && $(VENV)/uvicorn housefinder.api.main:app --reload --app-dir src

web:
	cd apps/web && npm run dev
