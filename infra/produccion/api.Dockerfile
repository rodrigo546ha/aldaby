# Imagen de la API, el worker y la tarea `preparar` (ADR-0040). Contexto: la raíz del repositorio.
# El código busca data/ y db/migrations/ junto a sus fuentes, así que se copia con la misma forma
# del repositorio y se usa por PYTHONPATH, sin instalar el paquete.
FROM python:3.12-slim-bookworm

# Tesseract en español para los documentos (ADR-0021) y pango para el PDF del plan (ADR-0026)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-spa \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/services/api
COPY services/api/pyproject.toml infra/produccion/requisitos-api.txt ./
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" > dependencias.txt \
    && pip install --no-cache-dir -r dependencias.txt -c requisitos-api.txt \
    && rm dependencias.txt

COPY db/migrations /app/db/migrations
COPY services/api/data ./data
COPY services/api/src ./src
# Los permisos llegan del árbol de origen (en el Mac, solo del propietario): lectura para todos
RUN chmod -R a+rX /app

ARG HOUSEFINDER_COMMIT=desconocido
ENV PYTHONPATH=/app/services/api/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOUSEFINDER_COMMIT=${HOUSEFINDER_COMMIT}

# Con carpeta personal: las cargas de datos públicos guardan su caché en ~/.cache
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin housefinder
USER housefinder

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "housefinder.api.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
