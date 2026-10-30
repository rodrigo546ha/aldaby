"""Base de datos temporal para los tests marcados `db` (ADR-0008).

Cada sesión crea una base vacía con un nombre aleatorio en el servidor de `DATABASE_URL`, la
pasa a los tests y la borra al final. Sin servidor, los tests `db` se saltan en local; con
`HOUSEFINDER_REQUIRE_DB=1` (CI) fallan, para que no se salten sin que nadie lo vea.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest


@pytest.fixture(scope="session")
def empty_database() -> Iterator[str]:
    psycopg = pytest.importorskip("psycopg")
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    required = os.environ.get("HOUSEFINDER_REQUIRE_DB") == "1"
    url = os.environ.get("DATABASE_URL")
    if not url:
        if required:
            pytest.fail("HOUSEFINDER_REQUIRE_DB=1 sin DATABASE_URL")
        pytest.skip("Sin DATABASE_URL: tests de base de datos saltados")
    try:
        admin = psycopg.connect(url, autocommit=True, connect_timeout=3)
    except psycopg.OperationalError as exc:
        if required:
            raise
        pytest.skip(f"Sin base de datos ({exc.__class__.__name__}): tests saltados")
    name = f"hf_test_{uuid.uuid4().hex[:8]}"
    with admin:
        admin.execute(f'CREATE DATABASE "{name}"')
        try:
            params = conninfo_to_dict(url)
            params["dbname"] = name
            yield make_conninfo(**params)
        finally:
            admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture(scope="session")
def migrated_database(empty_database: str) -> str:
    """La base temporal con todas las migraciones aplicadas, una vez por sesión."""
    from housefinder.db.migrate import migrate

    migrate(empty_database)
    return empty_database


def add_section(conninfo: str, code: str, lon: float, lat: float, size: float = 0.01,
                vintage: int = 2025) -> None:
    """Sección censal sintética alrededor de un punto (cartografía 2025 por defecto), para que
    el localizador de ofertas lo acepte como dentro de la zona cubierta."""
    import json

    import psycopg

    from housefinder.db.sections import SectionRow, upsert_sections

    half = size / 2
    ring = [[lon - half, lat - half], [lon + half, lat - half], [lon + half, lat + half],
            [lon - half, lat + half], [lon - half, lat - half]]
    geometry = json.dumps({"type": "MultiPolygon", "coordinates": [[ring]]})
    with psycopg.connect(conninfo) as conn:
        upsert_sections(conn, [SectionRow(code, code[:5], geometry)], vintage, None)
        conn.commit()
