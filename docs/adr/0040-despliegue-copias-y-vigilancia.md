# ADR-0040: Despliegue en el servidor, copias cifradas y vigilancia

- **Estado:** aceptada (decisiones de Rodrigo, 2026-11-02)
- **Fecha:** 2026-11-02
- **Tarea:** F7.5 (desarrolla ADR-0028)

## Contexto
ADR-0028 decidió un solo Hetzner GEX45 con Docker Compose, Caddy y Ollama, y dejó para F7.5 tres
cosas: cómo se monta y se actualiza, cómo se hacen las copias y quién avisa si algo se cae.

Rodrigo decide:
- **Preparar y probar en el Mac.** El servidor se contrata poco antes del piloto y el montaje es
  seguir la guía.
- **Copias con restic a un Storage Box de Hetzner.**
- **Avisos con Healthchecks.io gratuito.**
- **Dominio en una variable,** que se decide al confirmar la marca.

## Decisión

### Imágenes y Compose (`infra/produccion/`)
- **Imágenes propias:**
  - **API:** `python:3.12-slim-bookworm` con Tesseract en español y pango para WeasyPrint.
    - Corre como usuario sin privilegios (uid 10001).
    - La misma imagen sirve para la API, el worker y una tarea de un solo uso (`preparar`) que
      aplica las migraciones y las programaciones.
  - **Web:** `node:24-bookworm-slim` con `next build`.
- **Imágenes de terceros con versión fija:**
  - `caddy:2.10`, `postgis/postgis:16-3.4` (la misma que en desarrollo);
  - `ollama/ollama:0.34.4` (la del Mac).
- **Imagen de copias:** `postgres:16-bookworm` con el binario de `restic/restic:0.19.1`. Así
  `restic backup --stdin-from-command -- pg_dump …` no guarda una copia a medias si `pg_dump`
  falla.
- **Red:**
  - Solo Caddy publica puertos (80 y 443).
  - Caddy envía `/api/*` a la API, quitando el prefijo como hace la web en desarrollo, y lo demás
    a la web. Así las peticiones largas (entrevista, PDF) no dependen del proxy de Next.
  - La base y el modelo solo están en la red interna.
- **Cabeceras de seguridad en Caddy:**
  - HSTS, `nosniff`, `Referrer-Policy: same-origin` y `frame-ancestors 'none'`.
  - Sin registro de accesos: tendría las IP de los usuarios.
- **Modelo:**
  - Ollama con la GPU va en el perfil `modelo` de Compose, que solo se activa en el servidor.
  - En el Mac, la prueba usa el Ollama de Homebrew por `host.docker.internal`.
- **Secretos:**
  - La contraseña de la base, el dominio y las URL de aviso van en `infra/produccion/.env` del
    servidor, que crea el script de preparación y nunca entra en git.
  - La clave maestra (ADR-0011) se monta en solo lectura desde `/srv/housefinder/secretos/`, con
    permisos 0400 para el uid de la imagen. Ni la imagen ni las copias la llevan.
- **Registros:** de Docker (`json-file`), rotados a 5 ficheros de 10 MB por servicio.

### Montaje y actualización
- **`preparar-servidor.sh`,** una vez, como root, en Ubuntu 24.04:
  - usuario `housefinder`;
  - SSH solo con clave, sin contraseña;
  - cortafuegos con 22, 80 y 443;
  - actualizaciones de seguridad automáticas;
  - Docker y el controlador de NVIDIA con su `container-toolkit`;
  - generación de los secretos y temporizadores de systemd.

  El paso de la GPU no se puede probar sin el servidor: queda marcado para comprobarlo con
  `nvidia-smi` al contratar.
- **`desplegar.sh`,** desde el Mac:
  - Exige el árbol limpio y sube el commit actual con `git archive` (solo lo versionado: nunca
    `.env` ni `tests/fixtures/private/`).
  - Construye las imágenes en el servidor, ejecuta `preparar` y levanta los servicios.
  - El commit desplegado queda en las imágenes (`HOUSEFINDER_COMMIT`) y en `/health`.

  Sin registro de imágenes ni integración continua: no hay remoto de git y no compensan en la beta.
- **Datos públicos de partida** (secciones, renta, SERPAVI, supuestos): se cargan con las mismas
  órdenes dentro del contenedor (`compose run --rm api python -m …`), según la guía.

### Copias cifradas
- **Qué y cuándo:**
  - Cada día a las 03:30, `pg_dump -Fc` de la base va directo a restic, sin fichero intermedio
    (`--stdin-from-command`).
  - restic (licencia BSD) cifra antes de salir del servidor (AES-256 y Poly1305) y deduplica.
- **Destino:** un Storage Box BX11 de Hetzner por SFTP (puerto 23): 1 TB, 3,20 € al mes sin IVA
  (página oficial, 2026-11-02). Conviene en otra ubicación que el servidor (Falkenstein frente a
  Helsinki).
- **Retención:** 7 diarias, 4 semanales y 6 mensuales (`restic forget --prune`). Los domingos,
  `restic check` comprueba el repositorio.
  - Lo borrado (un cliente, ADR-0029) desaparece de las copias en seis meses como mucho. La
    política de privacidad (ADR-0039) tiene que decirlo: `plazo_copias` en `titular.yaml`.
- **Fuera de las copias, guardadas por Rodrigo en su gestor de contraseñas y no en el servidor:**
  - la contraseña del repositorio de restic;
  - la clave maestra.

  Sin la clave maestra, una copia no descifra los perfiles. Sin la contraseña de restic, no se
  abre.
- **`restaurar.sh`** recupera una copia en una base nueva. La prueba de restauración se hace al
  montar el servidor y después cada trimestre: está en la guía.

### Vigilancia y avisos (Healthchecks.io)
Healthchecks.io es pasivo: avisa por correo cuando un ping no llega a tiempo o llega como fallo. Así
avisa también si el servidor entero se cae. El plan gratuito permite 20 comprobaciones; usamos dos.
- **`copia`:** el script de copia envía `start` y luego éxito o fallo. Periodo de un día y 2 horas
  de gracia.
- **`vigilancia`:** un temporizador cada 5 minutos comprueba:
  - la cadena completa: `https://<dominio>/api/health`, que ahora también consulta la base;
  - que el worker está en marcha;
  - que no hay trabajos pendientes con más de 30 minutos de retraso (el worker no consume);
  - que no hay trabajos fallidos nuevos desde la comprobación anterior;
  - el disco por debajo del 85 %;
  - con el perfil `modelo`, que Ollama responde.

  Envía éxito, o fallo con la lista de lo que falla: solo nombres de comprobación, identificadores
  y tipos de trabajo, nunca su contenido ni datos personales. Periodo de 5 minutos y 10 de gracia.
- **Sin código de red nuevo en la API:** los pings los hacen los scripts del servidor con `curl`.
  Así se cumple lo que `jobs/alerts.py` dejaba para F7 («el correo llega en F7») sin servidor de
  correo.

## Opciones consideradas
- **`pg_dump` cifrado con age:** más simple, pero sin deduplicación ni comprobación del
  repositorio. Descartado.
- **Uptime Kuma en el propio servidor:** no avisa si cae el servidor y necesita correo saliente.
  Descartado.
- **Registro de imágenes e integración continua:** no hay remoto y sería otra pieza que mantener.
  Se puede añadir más adelante.
- **Contratar ya:** unos dos meses de servidor sin uso (≈ 430 € sin IVA).

## Consecuencias
- Coste fijo de la beta: 214 € del GEX45 y 3,20 € del Storage Box al mes, más 209 € de alta, sin
  IVA.
- Dos cuentas que crea Rodrigo: el Storage Box y Healthchecks.io.
- El paso de la GPU y el SFTP del Storage Box se comprueban al contratar. Todo lo demás se ha
  probado en el Mac con la misma configuración: Compose, Caddy, copia y restauración, y vigilancia.
- Quien tenga acceso de administrador al servidor tiene la clave maestra (ADR-0028). Revisar al
  pasar de la beta.
