# Despliegue de la beta

Guía para montar y mantener el servidor de la beta (ADR-0028 y ADR-0040). Todo lo de
`infra/produccion/` se ha probado en el Mac con la misma configuración, salvo dos cosas que solo
existen en el servidor: la GPU y el SFTP del Storage Box. Esas se comprueban en los pasos 3 y 5.

## Qué se contrata (lo hace Rodrigo)

| Pieza | Producto | Precio sin IVA (2026-11) |
| --- | --- | --- |
| Servidor | Hetzner GEX45, Ubuntu 24.04 | 214 €/mes + 209 € de alta |
| Copias | Hetzner Storage Box BX11, en otra ubicación que el servidor | 3,20 €/mes |
| Avisos | Healthchecks.io, plan Hobbyist | gratis (20 comprobaciones) |
| Dominio | el que se elija con la marca | — |

Al pedir el servidor, añade tu clave SSH pública: Hetzner la deja en
`/root/.ssh/authorized_keys`.

## 1. Preparar el servidor (una vez)

Desde el Mac, en la raíz del repositorio:

```bash
git archive HEAD infra/produccion | ssh root@IP 'mkdir -p /root/hf && tar -x -C /root/hf'
```

```bash
ssh root@IP 'bash /root/hf/infra/produccion/preparar-servidor.sh uNNNNN'
```

`uNNNNN` es el usuario del Storage Box. El script hace esto:
- crea el usuario `housefinder` (uid 10001) con tu clave SSH;
- quita las contraseñas de SSH;
- abre solo los puertos 22, 80 y 443;
- activa las actualizaciones de seguridad automáticas;
- instala Docker, el controlador de NVIDIA y el NVIDIA Container Toolkit;
- crea `/srv/housefinder` con la contraseña de la base, la de restic y la clave SSH de las copias;
- instala los temporizadores de copia y vigilancia.

Al terminar, reinicia el servidor y comprueba la GPU:

```bash
ssh root@IP reboot
```

```bash
ssh root@IP nvidia-smi
```

Debe aparecer la RTX PRO 4000 con 24 GB. Si `ubuntu-drivers` no eligió un controlador que la
reconozca, instala la versión que indique `ubuntu-drivers list --gpgpu` y vuelve a reiniciar.

## 2. Configuración y secretos

- **Configuración:** en `/srv/housefinder/config.env` (la contraseña de la base ya está), rellena:
  - `HOUSEFINDER_DOMAIN` y `HOUSEFINDER_WEB_URL`;
  - las dos URL de Healthchecks.io (paso 6).

  El dominio tiene que apuntar ya a la IP del servidor (registro A), o Caddy no conseguirá el
  certificado.
- **Gestor de contraseñas:** guarda en él la contraseña de las copias. Sin ella, las copias no se
  abren:

  ```bash
  ssh root@IP cat /srv/housefinder/secretos/restic.pass
  ```

## 3. Storage Box

1. En la consola de Hetzner, activa en el Storage Box el acceso por SSH y añade la clave pública
   que imprimió el script (`/srv/housefinder/secretos/ssh/id_ed25519.pub`).
2. Después del primer despliegue (paso 4), crea el repositorio de copias. Esto comprueba también
   el SFTP por el puerto 23:

   ```bash
   ssh housefinder@IP 'cd /srv/housefinder/actual/infra/produccion && docker compose run --rm copias restic init'
   ```

## 4. Primer despliegue

Desde el Mac, con el árbol limpio:

```bash
infra/produccion/desplegar.sh housefinder@IP
```

La primera vez falla al arrancar la API: falta la clave maestra. Créala en el servidor. La crea
Rodrigo y nunca sale de ahí, salvo la copia en su gestor de contraseñas:

```bash
ssh housefinder@IP 'docker run --rm -u 10001 -v /srv/housefinder/secretos:/secretos -e HOUSEFINDER_KEYS_FILE=/secretos/master.keys housefinder-api:$(cat /srv/housefinder/actual/infra/produccion/.commit) python -m housefinder.crypto nueva-clave'
```

```bash
ssh housefinder@IP cat /srv/housefinder/secretos/master.keys
```

Guarda ese contenido en el gestor de contraseñas y vuelve a desplegar. Después:
- crea el repositorio de copias (paso 3);
- crea tu cuenta de administrador:

  ```bash
  ssh housefinder@IP 'cd /srv/housefinder/actual/infra/produccion && docker compose run --rm api python -m housefinder.accounts alta TU_CORREO --organizacion "Aldaby" --rol admin'
  ```

El enlace que devuelve sirve para elegir la contraseña.

## 5. Modelo y datos públicos

El modelo se descarga una vez en el volumen de Ollama:

```bash
ssh housefinder@IP 'cd /srv/housefinder/actual/infra/produccion && docker compose exec ollama ollama pull qwen3:14b && docker compose exec ollama ollama create qwen3-14b-hf -f /modelfiles/qwen3-14b-hf.Modelfile'
```

Los datos públicos de partida se cargan con las mismas órdenes que `make` usa en el Mac, dentro
del contenedor. Por ejemplo:

```bash
ssh housefinder@IP 'cd /srv/housefinder/actual/infra/produccion && docker compose run --rm api python -m housefinder.ingestion.ine_sections --year 2025 --province 28'
```

Las órdenes de cada carga están en el `Makefile` (`sections`, `adrh`, `serpavi`, `ipv`,
`ipc-alquiler`, `supuestos`).
- **El valor tasado** se descarga a mano: súbelo con `scp` y pásalo a `docker compose run` con
  `-v`.
- **`hacienda_ibi`** no carga la base: escribe reglas en `data/rules`. Se ejecuta en el Mac, se
  hace commit y se despliega.

**El mapa base** (ADR-0051) no va en la imagen: se genera en el Mac con el extracto de España y se
sube a la carpeta del mapa, que Caddy sirve en `/mapa/teselas.pmtiles`. Pesa varios GB.

```bash
make mapa MAPA_BBOX=-18.4,27.5,4.6,44.0 MAPA_DESTINO=espana.pmtiles
scp espana.pmtiles housefinder@IP:/srv/housefinder/mapa/teselas.pmtiles
```

## 6. Avisos (Healthchecks.io)

En Healthchecks.io, crea dos comprobaciones y pon sus URL de ping en `config.env`:

| Comprobación | Variable | Periodo | Gracia |
| --- | --- | --- | --- |
| copia | `HC_COPIA_URL` | 1 día | 2 horas |
| vigilancia | `HC_VIGILANCIA_URL` | 5 minutos | 10 minutos |

Los avisos llegan al correo de la cuenta. La vigilancia comprueba cinco cosas:
- que la web, la API y la base responden;
- que el worker está en marcha;
- que la cola no tiene trabajos con más de 30 minutos de retraso ni fallidos nuevos;
- que el disco está por debajo del 85 %;
- que el modelo responde.

Si algo falla, el correo trae la lista.

Para probarlo a mano:

```bash
ssh housefinder@IP /srv/housefinder/actual/infra/produccion/vigilar.sh
```

```bash
ssh housefinder@IP COMPROBAR=1 /srv/housefinder/actual/infra/produccion/copia.sh
```

## Día a día

- **Desplegar una versión:**

  ```bash
  infra/produccion/desplegar.sh housefinder@IP
  ```

  Aplica las migraciones y las programaciones antes de arrancar la API y el worker.
- **Ver los registros:** `docker compose logs -f api worker` en `/srv/housefinder/actual/infra/produccion`.
- **Volver a una versión anterior** (solo si no trae migraciones nuevas, que no se deshacen):

  ```bash
  ssh housefinder@IP 'ln -sfn /srv/housefinder/versiones/COMMIT /srv/housefinder/actual && /srv/housefinder/actual/infra/produccion/arrancar.sh'
  ```

- **Ver las copias:** `docker compose run --rm copias restic snapshots`.

## Recuperar una copia

`restaurar.sh` recupera una copia en una base nueva del mismo servidor y compara el número de filas
con la base en uso. No toca producción.

```bash
ssh housefinder@IP /srv/housefinder/actual/infra/produccion/restaurar.sh
```

**Prueba de restauración:** al montar el servidor y después cada trimestre. Comprueba que las filas
cuadran y borra la base de prueba con `docker compose exec db dropdb -U housefinder NOMBRE`.

**Para pasar a usarla** (pérdida de la base, error grave):
1. Para la API y el worker: `docker compose stop api worker`.
2. Renombra las bases con `docker compose exec db psql -U housefinder -d postgres`:

   ```sql
   ALTER DATABASE housefinder RENAME TO housefinder_rota;
   ALTER DATABASE restaurada_… RENAME TO housefinder;
   ```

3. Vuelve a arrancar con `arrancar.sh`.

**En un servidor nuevo:** antes de restaurar hacen falta las mismas contraseñas y claves:
- `restic.pass`, con la misma `RESTIC_REPOSITORY`;
- `master.keys`.

Los perfiles, los nombres de los clientes y las URL de los feeds solo se descifran con la clave
maestra con la que se cifraron.

## Lo que se guarda y dónde

| Qué | Dónde | Copia |
| --- | --- | --- |
| Base de datos | volumen `housefinder_pgdata` | diaria, cifrada, en el Storage Box |
| Clave maestra | `/srv/housefinder/secretos/master.keys` | solo en el gestor de contraseñas de Rodrigo |
| Contraseña de las copias | `/srv/housefinder/secretos/restic.pass` | solo en el gestor de contraseñas de Rodrigo |
| Configuración | `/srv/housefinder/config.env` | se rehace desde `env.ejemplo` |
| Modelo | volumen `housefinder_ollama` | se vuelve a descargar |

Retención de las copias: 7 diarias, 4 semanales y 6 mensuales. Un cliente borrado desaparece de
las copias en seis meses como mucho (`plazo_copias` en `data/legal/titular.yaml`).
