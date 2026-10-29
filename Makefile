.PHONY: setup db migrate sections adrh worker schedules test lint rules-check api web openapi

# Configuración local (copia de .env.example, fuera de git): LLM, base de datos, claves…
-include .env
export $(shell sed -n 's/^\([A-Z_][A-Z0-9_]*\)=.*/\1/p' .env 2>/dev/null)

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

# Atlas de renta del INE por sección, 2015–2024 (F3.3). Necesita las cartografías de 2016 en
# adelante: cada año t va sobre el seccionado de t+1.
adrh:
	cd services/api && $(VENV)/python -m housefinder.ingestion.ine_adrh --province $(PROVINCE)

# Worker de la cola de trabajos (ADR-0010). Encolar: python -m housefinder.jobs enqueue …
worker:
	cd services/api && $(VENV)/python -m housefinder.jobs worker

# Programaciones diarias de data/jobs/programaciones.yaml (ADR-0010). Hace falta un worker en marcha.
schedules:
	cd services/api && $(VENV)/python -m housefinder.jobs programar

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
