.PHONY: setup db migrate sections test lint rules-check api web openapi

PYTHON ?= python3
VENV := .venv/bin
HOUSEFINDER_DB_PORT ?= 5442
DATABASE_URL ?= postgresql://housefinder:housefinder@127.0.0.1:$(HOUSEFINDER_DB_PORT)/housefinder
export HOUSEFINDER_DB_PORT DATABASE_URL

setup:
	cd services/api && $(PYTHON) -m venv .venv && $(VENV)/pip install -e ".[dev]"
	cd apps/web && npm install

# Arranca PostgreSQL + PostGIS y aplica las migraciones pendientes, también sobre un volumen
# que ya existe (ADR-0008).
db:
	docker compose -f infra/docker-compose.yml up -d --wait
	$(MAKE) migrate

migrate:
	cd services/api && $(VENV)/python -m housefinder.db.migrate

# Cartografía de secciones censales del INE (F3.2). Descarga ~50 MB por provincia.
YEAR ?= 2025
PROVINCE ?= 28
sections:
	cd services/api && $(VENV)/python -m housefinder.ingestion.ine_sections --year $(YEAR) --province $(PROVINCE)

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

# Tipos de la web generados desde el OpenAPI de la API (D11), sin arrancar el servidor.
openapi:
	cd services/api && $(VENV)/python -c "import json; from housefinder.api.main import app; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))" > ../../apps/web/lib/openapi.json
	cd apps/web && npx openapi-typescript lib/openapi.json -o lib/api-types.ts
