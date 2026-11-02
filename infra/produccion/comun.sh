# Funciones comunes de los scripts del servidor (ADR-0040). Se carga con `. ./comun.sh`.
set -euo pipefail

PRODUCCION="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -f "$PRODUCCION/.env" ]]; then
    echo "Falta $PRODUCCION/.env (copiar env.ejemplo)" >&2
    exit 1
fi
set -a
# shellcheck disable=SC1091
. "$PRODUCCION/.env"
set +a

# Versión desplegada: la escribe desplegar.sh; en el Mac, el commit actual de git
if [[ -z "${HOUSEFINDER_COMMIT:-}" ]]; then
    HOUSEFINDER_COMMIT="$(cat "$PRODUCCION/.commit" 2>/dev/null \
        || git -C "$PRODUCCION" rev-parse --short=12 HEAD 2>/dev/null || echo desconocido)"
fi
export HOUSEFINDER_COMMIT

# Con SILENCIO=1, sin las líneas de estado de los contenedores (copia, restauración y vigilancia)
compose() {
    docker compose ${SILENCIO:+--progress quiet} --project-directory "$PRODUCCION" -f "$PRODUCCION/compose.yml" "$@"
}

# ping_hc URL [start|fail|""] [texto]: avisa a Healthchecks.io. Sin URL, lo escribe en pantalla.
# El texto nunca lleva datos personales: solo nombres de comprobación, identificadores y tipos.
ping_hc() {
    local url="$1" estado="${2:-}" texto="${3:-}"
    if [[ -z "$url" ]]; then
        echo "[aviso${estado:+ $estado}] ${texto:-ok}"
        return 0
    fi
    curl -fsS -m 10 --retry 5 -o /dev/null --data-raw "$texto" "$url${estado:+/$estado}" \
        || echo "No se pudo avisar a Healthchecks.io" >&2
}
