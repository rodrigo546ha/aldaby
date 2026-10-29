"""Migraciones contra PostgreSQL + PostGIS reales (ADR-0008)."""

from pathlib import Path
from shutil import copytree

import pytest

from housefinder.db.migrate import default_migrations_dir, discover, migrate

pytestmark = pytest.mark.db
psycopg = pytest.importorskip("psycopg")


@pytest.fixture(scope="module")
def migrated(migrated_database: str) -> str:
    return migrated_database


def test_aplica_todas_y_una_segunda_vez_ninguna(migrated: str):
    with psycopg.connect(migrated) as conn:
        versions = [r[0] for r in conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version")]
    assert versions == [m.version for m in discover(default_migrations_dir())]
    assert migrate(migrated) == []


def test_una_seccion_tiene_una_fila_por_cartografia(migrated: str):
    square = "MULTIPOLYGON(((-3.70 40.41, -3.69 40.41, -3.69 40.42, -3.70 40.42, -3.70 40.41)))"
    with psycopg.connect(migrated) as conn:
        for vintage in (2023, 2024):
            conn.execute(
                "INSERT INTO census_sections (code, municipality, geom, vintage) "
                "VALUES ('2807901001', '28079', ST_GeomFromText(%s, 4326), %s)",
                (square, vintage),
            )
        found = conn.execute(
            "SELECT vintage FROM census_sections "
            "WHERE ST_Contains(geom, ST_SetSRID(ST_Point(-3.695, 40.415), 4326)) "
            "ORDER BY vintage"
        ).fetchall()
        conn.rollback()
    assert [r[0] for r in found] == [2023, 2024]


def test_un_perfil_exige_organizacion(migrated: str):
    with psycopg.connect(migrated) as conn, pytest.raises(psycopg.errors.NotNullViolation):
        conn.execute("INSERT INTO user_profiles (owner_id, data) VALUES ('u1', '{}')")


def test_editar_una_migracion_aplicada_para_el_ejecutor(migrated: str, tmp_path: Path):
    copy = copytree(default_migrations_dir(), tmp_path / "migrations")
    first = sorted(copy.glob("0001_*.sql"))[0]
    first.write_text(first.read_text(encoding="utf-8") + "\n-- editada\n", encoding="utf-8")
    with pytest.raises(ValueError, match="ha cambiado"):
        migrate(migrated, copy)


def test_una_migracion_que_falla_no_deja_nada_a_medias(migrated: str, tmp_path: Path):
    copy = copytree(default_migrations_dir(), tmp_path / "migrations")
    (copy / "9999_rota.sql").write_text(
        "CREATE TABLE a_medias (id INT);\nSELECT * FROM tabla_que_no_existe;\n",
        encoding="utf-8",
    )
    with pytest.raises(psycopg.errors.UndefinedTable):
        migrate(migrated, copy)
    with psycopg.connect(migrated) as conn:
        assert conn.execute("SELECT to_regclass('a_medias')").fetchone() == (None,)
        assert conn.execute(
            "SELECT count(*) FROM schema_migrations WHERE version = '9999'"
        ).fetchone() == (0,)
