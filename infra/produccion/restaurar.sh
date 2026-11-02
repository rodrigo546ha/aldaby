#!/usr/bin/env bash
# Recupera una copia en una base NUEVA del mismo servidor, sin tocar la de producción (ADR-0040).
#   ./restaurar.sh                    # la última copia, en restaurada_AAAAMMDD_HHMM
#   ./restaurar.sh ID [NOMBRE_BASE]   # una copia concreta (`compose run --rm copias restic snapshots`)
# Al terminar compara el número de filas con la base en uso. Para pasar a usarla, ver
# docs/DESPLIEGUE.md («Recuperar una copia»). Los perfiles solo se descifran con la clave maestra.
SILENCIO=1
. "$(dirname "$0")/comun.sh"

copia="${1:-latest}"
destino="${2:-restaurada_$(date +%Y%m%d_%H%M)}"
if [[ ! "$destino" =~ ^[a-z][a-z0-9_]*$ || "$destino" == housefinder ]]; then
    echo "Nombre de base no válido: $destino" >&2
    exit 1
fi

compose run --rm -T copias sh -euc '
    createdb "$1"
    restic dump --tag base --host housefinder "$2" /housefinder.dump \
        | pg_restore --no-owner --exit-on-error -d "$1"
' sh "$destino" "$copia"

consulta="SELECT t, n FROM (VALUES
    ('schema_migrations', (SELECT count(*) FROM schema_migrations)),
    ('organizations', (SELECT count(*) FROM organizations)),
    ('accounts', (SELECT count(*) FROM accounts)),
    ('clients', (SELECT count(*) FROM clients)),
    ('user_profiles', (SELECT count(*) FROM user_profiles)),
    ('offers', (SELECT count(*) FROM offers)),
    ('census_sections', (SELECT count(*) FROM census_sections)),
    ('jobs', (SELECT count(*) FROM jobs))) AS f(t, n)"
echo "Filas por tabla (en uso | restaurada $destino):"
paste \
    <(compose exec -T db psql -U housefinder -d housefinder -tAF ' ' -c "$consulta") \
    <(compose exec -T db psql -U housefinder -d "$destino" -tA -c "SELECT n FROM ($consulta) x") \
    | column -t
