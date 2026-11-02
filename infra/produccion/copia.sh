#!/usr/bin/env bash
# Copia diaria de la base con restic (ADR-0040); la lanza housefinder-copia.timer a las 03:30.
# pg_dump va directo a restic, que cifra antes de salir del servidor. Si pg_dump falla, restic no
# guarda la copia. Retención: 7 diarias, 4 semanales y 6 mensuales; los domingos, `restic check`.
SILENCIO=1
. "$(dirname "$0")/comun.sh"

registro="$(mktemp)"
trap 'rm -f "$registro"' EXIT

ping_hc "${HC_COPIA_URL:-}" start
if {
    compose run --rm -T copias restic backup --tag base --host housefinder \
        --stdin-filename housefinder.dump --stdin-from-command -- pg_dump -Fc
    compose run --rm -T copias restic forget --tag base --host housefinder \
        --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
    if [[ "$(date +%u)" == 7 || "${COMPROBAR:-}" == 1 ]]; then
        compose run --rm -T copias restic check
    fi
} >"$registro" 2>&1; then
    cat "$registro"
    ping_hc "${HC_COPIA_URL:-}" "" "$(tail -c 2000 "$registro")"
else
    cat "$registro" >&2
    ping_hc "${HC_COPIA_URL:-}" fail "$(tail -c 2000 "$registro")"
    exit 1
fi
