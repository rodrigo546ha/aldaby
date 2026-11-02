#!/usr/bin/env bash
# Preparación del servidor de la beta, una sola vez y como root, en Ubuntu 24.04 (ADR-0040).
#   bash preparar-servidor.sh [USUARIO_STORAGE_BOX] [--sin-gpu]
# Se sube con la carpeta infra/produccion (ver docs/DESPLIEGUE.md). Sin probar en el servidor
# real hasta contratarlo: el paso de la GPU se comprueba con `nvidia-smi` tras reiniciar.
set -euo pipefail

storagebox=""
gpu=1
for arg in "$@"; do
    case "$arg" in
        --sin-gpu) gpu=0 ;;
        *) storagebox="$arg" ;;
    esac
done
[[ "$(id -u)" == 0 ]] || { echo "Ejecutar como root" >&2; exit 1; }
. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || { echo "Pensado para Ubuntu 24.04" >&2; exit 1; }
aqui="$(cd "$(dirname "$0")" && pwd)"
raiz=/srv/housefinder
export DEBIAN_FRONTEND=noninteractive

echo "== Paquetes y actualizaciones de seguridad automáticas"
apt-get update
apt-get -y upgrade
apt-get install -y ca-certificates curl gnupg ufw unattended-upgrades openssl
cat >/etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

echo "== Usuario housefinder (uid 10001, el mismo que dentro de la imagen de la API)"
if ! id housefinder >/dev/null 2>&1; then
    useradd --uid 10001 --create-home --shell /bin/bash housefinder
fi
install -d -m 700 -o housefinder -g housefinder /home/housefinder/.ssh
if [[ -f /root/.ssh/authorized_keys ]]; then
    install -m 600 -o housefinder -g housefinder /root/.ssh/authorized_keys \
        /home/housefinder/.ssh/authorized_keys
fi

echo "== SSH solo con clave"
cat >/etc/ssh/sshd_config.d/10-housefinder.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
EOF
sshd -t
systemctl reload ssh

echo "== Cortafuegos: SSH, HTTP y HTTPS"
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable

echo "== Docker (repositorio oficial de Docker)"
if ! command -v docker >/dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" \
        >/etc/apt/sources.list.d/docker.list
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin \
        docker-compose-plugin
fi
# Quien está en el grupo docker equivale a root: solo housefinder
usermod -aG docker housefinder

if [[ "$gpu" == 1 ]]; then
    echo "== Controlador de NVIDIA y NVIDIA Container Toolkit (comprobar con nvidia-smi al reiniciar)"
    apt-get install -y ubuntu-drivers-common
    ubuntu-drivers install --gpgpu
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
        | gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
        | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
        >/etc/apt/sources.list.d/nvidia-container-toolkit.list
    apt-get update
    apt-get install -y nvidia-container-toolkit
    nvidia-ctk runtime configure --runtime=docker
    systemctl restart docker
fi

echo "== Carpetas y secretos"
install -d -m 755 -o housefinder -g housefinder "$raiz" "$raiz/versiones" "$raiz/estado"
install -d -m 700 -o housefinder -g housefinder "$raiz/secretos"
# ssh dentro del contenedor de copias corre como root y exige ficheros de root
install -d -m 700 -o root -g root "$raiz/secretos/ssh"
if [[ ! -f "$raiz/config.env" ]]; then
    sed "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 32)|" \
        "$aqui/env.ejemplo" >"$raiz/config.env"
    chown housefinder:housefinder "$raiz/config.env"
    chmod 600 "$raiz/config.env"
fi
if [[ ! -f "$raiz/secretos/restic.pass" ]]; then
    openssl rand -base64 32 >"$raiz/secretos/restic.pass"
    chown housefinder:housefinder "$raiz/secretos/restic.pass"
    chmod 400 "$raiz/secretos/restic.pass"
fi
if [[ ! -f "$raiz/secretos/ssh/id_ed25519" ]]; then
    ssh-keygen -q -t ed25519 -N "" -C "housefinder-copias" -f "$raiz/secretos/ssh/id_ed25519"
fi
if [[ -n "$storagebox" && ! -f "$raiz/secretos/ssh/config" ]]; then
    cat >"$raiz/secretos/ssh/config" <<EOF
Host storagebox
    HostName $storagebox.your-storagebox.de
    User $storagebox
    Port 23
    IdentityFile /root/.ssh/id_ed25519
    StrictHostKeyChecking yes
EOF
    chmod 600 "$raiz/secretos/ssh/config"
    ssh-keyscan -p 23 "$storagebox.your-storagebox.de" >"$raiz/secretos/ssh/known_hosts"
fi

echo "== Temporizadores de copia y vigilancia"
install -m 644 "$aqui"/systemd/housefinder-*.service "$aqui"/systemd/housefinder-*.timer \
    /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now housefinder-copia.timer housefinder-vigilancia.timer

cat <<EOF

Hecho. Pendiente (docs/DESPLIEGUE.md):
  - Reiniciar si se instaló el controlador de NVIDIA y comprobar: nvidia-smi
  - Completar $raiz/config.env (dominio, URL de Healthchecks.io)
  - Dar al Storage Box esta clave pública: $(cat "$raiz/secretos/ssh/id_ed25519.pub")
  - Guardar en el gestor de contraseñas: $raiz/secretos/restic.pass
  - Desplegar desde el Mac y crear la clave maestra
EOF
