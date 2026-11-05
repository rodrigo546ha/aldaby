.PHONY: setup db migrate sections adrh serpavi valor-tasado ipv ipc-alquiler supuestos backtest worker schedules worker-install worker-uninstall worker-logs test lint rules-check api web openapi evaluar requisitos-api mapa

# Configuración local (copia de .env.example, fuera de git): LLM, base de datos, claves…
-include .env
export $(shell sed -n 's/^\([A-Z_][A-Z0-9_]*\)=.*/\1/p' .env 2>/dev/null)

PYTHON ?= python3
VENV := .venv/bin
HOUSEFINDER_DB_PORT ?= 5442
DATABASE_URL ?= postgresql://housefinder:housefinder@127.0.0.1:$(HOUSEFINDER_DB_PORT)/housefinder
export HOUSEFINDER_DB_PORT DATABASE_URL

# WeasyPrint (PDF del plan, ADR-0026) carga pango y cairo de Homebrew. macOS no pasa DYLD_* a
# través de /bin/sh, así que va delante de cada orden que puede generar un PDF.
PDF_LIBS := $(if $(wildcard /opt/homebrew/lib/libpango-1.0.dylib),DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib,)

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

# Valor tasado por municipio: CSV descargado a mano (FICHERO=…), el portal prohíbe el acceso
# automático. IPV del INE por comunidad (ADR-0018)
valor-tasado:
	cd services/api && $(VENV)/python -m housefinder.ingestion.valor_tasado --fichero "$(FICHERO)"

ipv:
	cd services/api && $(VENV)/python -m housefinder.ingestion.ine_ipv --region $(REGION)

ipc-alquiler:
	cd services/api && $(VENV)/python -m housefinder.ingestion.ine_ipc_alquiler --region $(REGION)

# Backtesting del modelo de renta y precio (F5.6)
# Supuestos del plan desde fuentes públicas (ADR-0022): tipos del Banco de España y del INE,
# estadísticas del Catastro, gasto de la vivienda de la EPF y reglas del IBI y de la plusvalía
# de Hacienda (ADR-0044).
CATASTRO_YEAR ?= 2026
IBI_YEAR ?= 2026
supuestos:
	cd services/api && $(VENV)/python -m housefinder.ingestion.bde_tipos
	cd services/api && $(VENV)/python -m housefinder.ingestion.ine_hipotecas
	cd services/api && $(VENV)/python -m housefinder.ingestion.catastro_urbana --year $(CATASTRO_YEAR) --province $(PROVINCE)
	cd services/api && $(VENV)/python -m housefinder.ingestion.ine_epf
	cd services/api && $(VENV)/python -m housefinder.ingestion.hacienda_ibi --year $(IBI_YEAR)
	cd services/api && $(VENV)/python -m housefinder.ingestion.hacienda_plusvalia --year $(IBI_YEAR)

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
	cd services/api && $(PDF_LIBS) $(VENV)/python -m pytest -q

# Evaluaciones con el modelo de .env (ADR-0027): extracción, asesor y coherencia del plan.
# Compara con data/evaluation/linea_base.json; BASE=1 guarda la nueva línea base.
evaluar:
	cd services/api && $(PDF_LIBS) $(VENV)/python -m housefinder.evaluations $(if $(BASE),--guardar-base,) $(if $(SALIDA),--salida $(abspath $(SALIDA)),)

lint:
	cd services/api && $(VENV)/ruff check src tests

rules-check:
	cd services/api && $(VENV)/python -m housefinder.regulation.check

api:
	cd services/api && $(PDF_LIBS) $(VENV)/python -m uvicorn housefinder.api.main:app --reload --app-dir src

web:
	cd apps/web && npm run dev

# Mapa base (ADR-0051): extracto de OpenStreetMap de un build de Protomaps, leído por partes (HTTP
# Range). pmtiles es go-pmtiles (github.com/protomaps/go-pmtiles); en el Mac, en .herramientas/. Por
# defecto, la Comunidad de Madrid hasta zoom 15 (unos 120 MB). España con Canarias:
# MAPA_BBOX=-18.4,27.5,4.6,44.0 MAPA_DESTINO=/srv/housefinder/mapa/teselas.pmtiles
PMTILES ?= $(if $(wildcard .herramientas/pmtiles),.herramientas/pmtiles,pmtiles)
MAPA_BUILD ?= 20261103
MAPA_BBOX ?= -4.58,39.88,-3.05,41.17
MAPA_ZOOM ?= 15
MAPA_DESTINO ?= apps/web/public/mapa/teselas.pmtiles

mapa:
	mkdir -p $(dir $(MAPA_DESTINO))
	$(PMTILES) extract https://build.protomaps.com/$(MAPA_BUILD).pmtiles $(MAPA_DESTINO) \
		--bbox=$(MAPA_BBOX) --maxzoom=$(MAPA_ZOOM)

# Tipos de la web generados desde el OpenAPI de la API (D11), sin arrancar el servidor.
openapi:
	cd services/api && $(VENV)/python -c "import json; from housefinder.api.main import app; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))" > ../../apps/web/lib/openapi.json
	cd apps/web && npx openapi-typescript lib/openapi.json -o lib/api-types.ts

# Versiones de la imagen de la API (ADR-0040): las del entorno de desarrollo, sin las herramientas.
requisitos-api:
	{ echo "# Versiones probadas en el Mac (pip freeze del entorno de desarrollo), como restricciones de la"; \
	  echo "# imagen de la API (ADR-0040). Regenerar con: make requisitos-api"; \
	  cd services/api && $(VENV)/python -m pip freeze --exclude-editable \
	  | grep -viE '^(pytest|ruff|mypy|mypy_extensions|iniconfig|pluggy|pygments|librt|ast_serialize|boto3|botocore|s3transfer|jmespath|opentelemetry-api|docstring_parser|httpx2|httpcore2|jiter|truststore|python-dotenv|pathspec)=='; \
	} > infra/produccion/requisitos-api.txt
