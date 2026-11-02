#!/usr/bin/env bash
# Despliega el commit actual en el servidor (ADR-0040), desde el Mac:
#   infra/produccion/desplegar.sh housefinder@IP_O_DOMINIO
# Sube solo lo versionado (git archive: nunca .env ni tests/fixtures/private), lo deja en
# /srv/housefinder/versiones/COMMIT, apunta /srv/housefinder/actual ahí y ejecuta arrancar.sh.
# Guarda las cinco últimas versiones; volver a una anterior está en docs/DESPLIEGUE.md.
set -euo pipefail

destino="${1:?Uso: desplegar.sh usuario@servidor}"
cd "$(git rev-parse --show-toplevel)"
if [[ -n "$(git status --porcelain)" ]]; then
    echo "Hay cambios sin commit: solo se despliega lo que está en un commit." >&2
    exit 1
fi
commit="$(git rev-parse --short=12 HEAD)"
version="/srv/housefinder/versiones/$commit"
echo "Desplegando $commit en $destino"

git archive --format=tar HEAD \
    | ssh "$destino" "rm -rf '$version' && mkdir -p '$version' && tar -x -C '$version'"

ssh "$destino" bash -s -- "$commit" <<'REMOTO'
set -euo pipefail
commit="$1"
raiz=/srv/housefinder
version="$raiz/versiones/$commit"
echo "$commit" >"$version/infra/produccion/.commit"
# La configuración y el estado de la vigilancia viven fuera de las versiones
ln -sfn "$raiz/config.env" "$version/infra/produccion/.env"
mkdir -p "$raiz/estado"
ln -sfn "$version" "$raiz/actual"
"$version/infra/produccion/arrancar.sh"

# Limpieza: las cinco versiones más recientes y sus imágenes
cd "$raiz/versiones"
ls -1t | tail -n +6 | while read -r vieja; do rm -rf "${vieja:?}"; done
guardar="$(ls -1 | paste -sd'|' -)"
docker image ls --format '{{.Repository}}:{{.Tag}}' \
    | grep -E '^housefinder-(api|web):' | grep -vE ":($guardar)\$" \
    | xargs -r docker image rm >/dev/null || true
REMOTO
echo "Desplegado $commit"
