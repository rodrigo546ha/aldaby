#!/usr/bin/env bash
# Construye las imágenes de esta versión y levanta los servicios (ADR-0040). Lo llama desplegar.sh
# en el servidor; en el Mac sirve para la prueba local. `preparar` aplica migraciones y
# programaciones antes de que arranquen la API y el worker.
. "$(dirname "$0")/comun.sh"

export HOUSEFINDER_COMMIT
compose build
compose up -d --remove-orphans --wait
compose ps
