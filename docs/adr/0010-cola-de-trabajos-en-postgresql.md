# ADR-0010: Cola de trabajos en PostgreSQL

**Estado:** Aceptada (D7 del plan de diseño, F4.7) · **Fecha:** 2026-10-29 · **Decide:** Rodrigo

## Contexto
Hay cargas que deben ejecutarse solas y repetirse: la cartografía y el Atlas de renta del INE cada
año, el sumario del BOE y del BOCM cada día (F2.6, F4.2) y, más adelante, la ingesta de oferta. Si
fallan, tienen que reintentarse y, si siguen fallando, alguien tiene que enterarse (F4.7). Hoy solo
existen como comandos que se lanzan a mano.

## Decisión
- **La cola es una tabla de PostgreSQL** (`jobs`), la misma base que el resto. Un trabajo tiene
  tipo (`kind`), parámetros (`payload`, JSON sin datos personales), estado (`pendiente`,
  `en_curso`, `hecho`, `fallido`), intentos y `run_after` (cuándo puede ejecutarse).
- **Reservar un trabajo** es una sola sentencia: `UPDATE … WHERE id = (SELECT … FOR UPDATE SKIP
  LOCKED LIMIT 1) RETURNING …`. Dos workers nunca reservan el mismo trabajo y no se bloquean entre sí.
  El trabajo se ejecuta fuera de esa transacción; el estado `en_curso` con `locked_at` hace de
  préstamo.
- **Préstamos caducados:** un trabajo `en_curso` desde hace más de una hora (worker caído) vuelve a
  `pendiente` y cuenta como intento fallido.
- **Reintentos con espera creciente:** 1, 2, 4, 8… minutos, con un máximo de una hora, hasta
  `max_attempts` (5 por defecto). Agotados, el trabajo queda `fallido` y salta la alerta.
- **Cada intento** queda en `job_runs`: inicio, fin, si salió bien, resultado (JSON) o error.
- **Programación:** tabla `job_schedules` con un nombre, el trabajo que crea y un intervalo en
  segundos. El worker encola los vencidos y mueve `next_run_at`. Sin expresiones cron mientras basten
  los intervalos (diario, anual). Las programaciones se declaran en
  `data/jobs/programaciones.yaml` con su primera hora en hora de Madrid; `make schedules` las aplica
  y desactiva las que ya no están (2026-10-29). El intervalo es fijo: con el cambio de hora la
  ejecución se desplaza una hora hasta volver a aplicar el fichero.
- **No duplicar:** `dedupe_key` opcional, único entre los trabajos `pendiente` o `en_curso`. Una
  programación usa su nombre como clave, así que no se acumulan copias si el worker estuvo parado.
- **Alertas:** al principio, un registro de nivel ERROR en el logger `housefinder.alertas` con el
  identificador, el tipo, los intentos y el error, nunca el `payload`. El correo llegará con el
  despliegue (F7).
- **Trabajos idempotentes:** repetir un trabajo no puede duplicar datos. Los cargadores del INE ya lo
  son (`ON CONFLICT … DO UPDATE`).
- Código en `housefinder/jobs/` (worker, registro de tipos, esperas, alertas) y el SQL en
  `housefinder/db/jobs.py`. `make worker` arranca el worker.

## Opciones consideradas
- **Celery + Redis:** potente, pero otra pieza que operar y vigilar. Descartada.
- **AWS EventBridge + Lambda:** ata el diseño a AWS antes de F7. Descartada por ahora.
- **cron del sistema:** sin reintentos, sin historial y sin alertas. Descartado.
- **Tabla en PostgreSQL con `SKIP LOCKED` (elegida).**

## Consecuencias
- Un solo proceso más (el worker), del mismo código y la misma base.
- Revisar si se superan decenas de miles de trabajos al día o hace falta paralelismo entre máquinas.
- Un trabajo largo que pase de una hora se reintentaría por error: el préstamo es configurable por
  worker y habrá que subirlo si aparece uno así.
