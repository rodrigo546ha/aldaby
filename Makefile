.PHONY: setup db migrate sections adrh serpavi valor-tasado ipv ipc-alquiler backtest worker schedules worker-install worker-uninstall worker-logs test lint rules-check api web openapi

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
REGION ?= 13
sections:
	cd services/api && $(VENV)/python -m housefinder.ingestion.ine_sections --year $(YEAR) --province $(PROVINCE)

# Atlas de renta del INE por sección, 2015–2024 (F3.3). Necesita las cartografías de 2016 en
# adelante: cada año t va sobre el seccionado de t+1.
adrh:
	cd services/api && $(VENV)/python -m housefinder.ingestion.ine_adrh --province $(PROVINCE)

# Referencias de alquiler del SERPAVI 2011–2024 (ADR-0018); el Excel se guarda en ~/.cache/housefinder
serpavi:
	cd services/api && $(VENV)/python -m housefinder.ingestion.serpavi --province $(PROVINCE)

# Valor tasado por municipio (Comunidad de Madrid) e IPV del INE por comunidad (ADR-0018)
valor-tasado:
	cd services/api && $(VENV)/python -m housefinder.ingestion.valor_tasado

ipv:
	cd services/api && $(VENV)/python -m housefinder.ingestion.ine_ipv --region $(REGION)

ipc-alquiler:
	cd services/api && $(VENV)/python -m housefinder.ingestion.ine_ipc_alquiler --region $(REGION)

# Backtesting del modelo de renta y precio (F5.6)
backtest:
	cd services/api && $(VENV)/python -m housefinder.valuation.backtest --province $(PROVINCE) --region $(REGION)

# Worker de la cola de trabajos (ADR-0010). Encolar: python -m housefinder.jobs enqueue …
worker:
	cd services/api && $(VENV)/python -m housefinder.jobs worker

# Programaciones diarias de data/jobs/programaciones.yaml (ADR-0010). Hace falta un worker en marcha.
schedules:
	cd services/api && $(VENV)/python -m housefinder.jobs programar

# Worker siempre en marcha en este Mac con launchd (infra/launchd/). Logs en ~/Library/Logs/housefinder.
WORKER_LABEL := com.housefinder.worker
WORKER_PLIST := $(HOME)/Library/LaunchAgents/$(WORKER_LABEL).plist
WORKER_LOGS := $(HOME)/Library/Logs/housefinder

worker-install:
	mkdir -p $(WORKER_LOGS) $(HOME)/Library/LaunchAgents
	sed -e 's|__REPO__|$(CURDIR)|g' -e 's|__LOGS__|$(WORKER_LOGS)|g' \
		infra/launchd/$(WORKER_LABEL).plist > $(WORKER_PLIST)
	plutil -lint $(WORKER_PLIST)
	-launchctl bootout gui/$$(id -u)/$(WORKER_LABEL) 2>/dev/null
	launchctl bootstrap gui/$$(id -u) $(WORKER_PLIST)
	@echo "Worker instalado. Logs: make worker-logs"
	@echo "Si el repositorio está en Documentos, el Python que necesita «Acceso total al disco» es:"
	@cd services/api && $(VENV)/python -c "import os; print(os.path.realpath('$(VENV)/python'))"

worker-uninstall:
	-launchctl bootout gui/$$(id -u)/$(WORKER_LABEL)
	rm -f $(WORKER_PLIST)

worker-logs:
	tail -n 50 -f $(WORKER_LOGS)/worker.log

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
