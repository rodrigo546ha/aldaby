#!/usr/bin/env bash
# Vigilancia cada 5 minutos (housefinder-vigilancia.timer, ADR-0040). Avisa a Healthchecks.io con
# éxito o con la lista de lo que falla; si el servidor se cae, el ping deja de llegar y avisa él.
# Solo nombres de comprobación, identificadores y tipos de trabajo: nunca contenidos ni datos.
SILENCIO=1
. "$(dirname "$0")/comun.sh"

ESTADO="${HOUSEFINDER_ESTADO:-$PRODUCCION/.estado}"
mkdir -p "$ESTADO"
problemas=()

sql() {
    compose exec -T db psql -U housefinder -d housefinder -tAX -c "$1"
}

# 1. La cadena completa: Caddy, la API y la base (/health consulta la base)
url="https://${HOUSEFINDER_DOMAIN}:${HOUSEFINDER_HTTPS_PORT:-443}/api/health"
inseguro=()
[[ "$HOUSEFINDER_DOMAIN" == localhost ]] && inseguro=(-k)  # autoridad propia de Caddy en el Mac
if ! curl -fsS -m 15 ${inseguro[@]+"${inseguro[@]}"} -o /dev/null "$url"; then
    problemas+=("web: $url no responde")
fi

# 2. El worker en marcha
if ! compose ps --status running --services | grep -qx worker; then
    problemas+=("worker: parado")
fi

# 3. La cola: trabajos con más de 30 minutos de retraso y fallidos nuevos desde la última vez
if retrasados="$(sql "SELECT count(*) FROM jobs WHERE status = 'pendiente'
                      AND run_after < now() - interval '30 minutes'")"; then
    [[ "$retrasados" -gt 0 ]] && problemas+=("cola: $retrasados trabajos con más de 30 min de retraso")
    ultimo="$(cat "$ESTADO/ultimo_fallido" 2>/dev/null || echo 0)"
    [[ "$ultimo" =~ ^[0-9]+$ ]] || ultimo=0
    fallidos="$(sql "SELECT id || ' ' || kind FROM jobs WHERE status = 'fallido' AND id > $ultimo
                     ORDER BY id")"
    if [[ -n "$fallidos" ]]; then
        problemas+=("cola: trabajos fallidos: $(tr '\n' ',' <<<"$fallidos" | sed 's/,$//')")
        tail -n 1 <<<"$fallidos" | cut -d' ' -f1 >"$ESTADO/ultimo_fallido"
    fi
else
    problemas+=("base: no responde a la consulta de la cola")
fi

# 4. Disco por debajo del 85 % (la raíz y la carpeta de Docker)
for ruta in / /var/lib/docker; do
    [[ -d "$ruta" ]] || continue
    uso="$(df -P "$ruta" | awk 'NR == 2 { sub("%", "", $5); print $5 }')"
    [[ "$uso" -ge 85 ]] && problemas+=("disco: $ruta al $uso %")
done

# 5. El modelo, si este servidor lo sirve
if [[ ",${COMPOSE_PROFILES:-}," == *,modelo,* ]]; then
    compose exec -T ollama ollama list >/dev/null 2>&1 || problemas+=("modelo: Ollama no responde")
fi

if [[ ${#problemas[@]} -eq 0 ]]; then
    ping_hc "${HC_VIGILANCIA_URL:-}" "" "todo en orden"
else
    ping_hc "${HC_VIGILANCIA_URL:-}" fail "$(printf '%s\n' "${problemas[@]}")"
    exit 1
fi
