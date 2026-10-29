"""Ejecutor de migraciones (ADR-0008).

Aplica `db/migrations/NNNN_nombre.sql` en orden, cada fichero en su transacción, y apunta
cada uno en `schema_migrations` con el sha256 del fichero. Una migración aplicada no se
edita: si su huella cambia, para. Uso: `python -m housefinder.db.migrate` con `DATABASE_URL`.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg

FILE_NAME = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")
# Identificador del bloqueo consultivo: el mismo para todos los procesos que migran.
LOCK_ID = 7413002

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    checksum    TEXT NOT NULL,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    path: Path
    checksum: str  # sha256 del fichero

    @property
    def sql(self) -> str:
        return self.path.read_text(encoding="utf-8")


def default_migrations_dir() -> Path:
    """db/migrations en la raíz del repositorio."""
    return Path(__file__).resolve().parents[5] / "db" / "migrations"


def discover(directory: Path) -> list[Migration]:
    """Migraciones del directorio, en orden. Un .sql con otro nombre es un error."""
    found: dict[str, Migration] = {}
    for path in sorted(directory.glob("*.sql")):
        match = FILE_NAME.match(path.name)
        if match is None:
            raise ValueError(f"Nombre de migración no válido (NNNN_nombre.sql): {path.name}")
        version, name = match.groups()
        if version in found:
            raise ValueError(f"Versión repetida: {found[version].path.name} y {path.name}")
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        found[version] = Migration(version, name, path, checksum)
    return [found[v] for v in sorted(found)]


def pending(migrations: list[Migration], applied: dict[str, str]) -> list[Migration]:
    """Migraciones por aplicar, comprobando lo aplicado.

    `applied`: versión → sha256 apuntado en `schema_migrations`. Para si una migración
    aplicada ha cambiado o ya no existe, o si una nueva queda antes de la última aplicada.
    """
    by_version = {m.version: m for m in migrations}
    for version, checksum in applied.items():
        migration = by_version.get(version)
        if migration is None:
            raise ValueError(f"La migración {version} está aplicada pero no existe su fichero")
        if migration.checksum != checksum:
            raise ValueError(
                f"La migración {migration.path.name} ha cambiado después de aplicarse: "
                "escribe una migración nueva en lugar de editarla"
            )
    todo = [m for m in migrations if m.version not in applied]
    if todo and applied and todo[0].version < max(applied):
        raise ValueError(
            f"La migración {todo[0].path.name} va antes de la última aplicada ({max(applied)})"
        )
    return todo


def migrate(conninfo: str, directory: Path | None = None) -> list[Migration]:
    """Aplica las migraciones pendientes y devuelve las aplicadas en esta ejecución."""
    migrations = discover(directory or default_migrations_dir())
    with psycopg.connect(conninfo, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (LOCK_ID,))
        try:
            conn.execute(CREATE_TABLE)
            rows = conn.execute("SELECT version, checksum FROM schema_migrations").fetchall()
            todo = pending(migrations, dict(rows))
            for migration in todo:
                with conn.transaction():
                    conn.execute(migration.sql.encode("utf-8"))
                    conn.execute(
                        "INSERT INTO schema_migrations (version, name, checksum) "
                        "VALUES (%s, %s, %s)",
                        (migration.version, migration.name, migration.checksum),
                    )
            return todo
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("Falta DATABASE_URL (ver .env.example)")
    return url


def main() -> int:
    try:
        applied = migrate(database_url())
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if applied:
        for migration in applied:
            print(f"Aplicada {migration.path.name}")
    else:
        print("Sin migraciones pendientes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
