# ADR-0008: Migraciones con un ejecutor propio y acceso a datos con psycopg 3

**Estado:** Aceptada (D5 y D6 del plan de diseño) · **Fecha:** 2026-10-29 · **Decide:** Rodrigo

## Contexto
El esquema se aplica hoy montando `db/migrations/` en `docker-entrypoint-initdb.d`: PostgreSQL solo
ejecuta esos ficheros al crear un volumen vacío. Una migración nueva (`0002`) no llega nunca a una
base que ya existe, así que `make db` no sirve en cuanto haya datos. G4 necesita varias migraciones
seguidas (secciones censales con cartografía versionada, `org_id`, reproducibilidad de los planes,
cola de trabajos, perfiles cifrados) y tests contra una base real en CI.

Las consultas importantes de G4 y G5 son de PostGIS (punto en polígono, cercanía para detectar
duplicados): con un ORM acabarían en SQL igualmente (D5 y D6 de `docs/PLAN_DISENO.md`).

## Decisión
- **Ejecutor propio** (`housefinder/db/migrate.py`, `python -m housefinder.db.migrate`):
  - aplica `db/migrations/NNNN_nombre.sql` en orden numérico, cada fichero en su transacción;
  - apunta cada uno en `schema_migrations` (versión, nombre, sha256 del fichero, fecha);
  - una migración aplicada no se edita: si su sha256 cambia, el ejecutor para con un error;
  - toma un `pg_advisory_lock` para que dos procesos no migren a la vez;
  - lee la conexión de `DATABASE_URL`.
- `make db` arranca el contenedor, espera a que acepte conexiones y ejecuta el ejecutor. El montaje
  en `docker-entrypoint-initdb.d` desaparece: hay un solo camino para el esquema.
- **psycopg 3** como única dependencia de acceso a datos, con SQL explícito en funciones de
  repositorio pequeñas y tipadas por dominio, dentro de `housefinder/db/`.
- Los motores, la normativa, los parámetros y la planificación no importan `db/` ni psycopg: la base
  de datos entra por la API y por los trabajos (test de dirección de dependencias).
- Tests de integración contra PostgreSQL + PostGIS: cada ejecución crea una base temporal, aplica
  las migraciones y la borra. En CI, un servicio `postgis`; en local, se saltan si no hay base.
- La base local escucha solo en `127.0.0.1`, en el puerto `HOUSEFINDER_DB_PORT` (por defecto
  5442, para no chocar con otros PostgreSQL de la máquina).

## Opciones consideradas
- **Alembic:** el estándar en Python, pero arrastra SQLAlchemy y su modelo cuando aquí el SQL es
  explícito y las migraciones son ficheros SQL. Descartada.
- **yoyo-migrations o sqitch:** dependencias pequeñas que hacen lo mismo, con otra herramienta y
  otro formato que aprender. Descartadas por ahora.
- **Ejecutor propio (elegida):** unas decenas de líneas con tests; revisar si aparecen migraciones
  de datos complejas o migraciones hacia atrás.
- **SQLAlchemy u otro ORM para el acceso:** descartado por la razón de PostGIS de arriba.

## Consecuencias
- `make db` aplica las migraciones nuevas sobre un volumen existente (criterio de G4).
- Corregir una migración ya aplicada = escribir otra nueva. No hay migraciones hacia atrás.
- Más SQL escrito a mano; a cambio, ninguna capa entre la consulta y la cifra.
- `psycopg[binary]` pasa a ser dependencia de la API.
