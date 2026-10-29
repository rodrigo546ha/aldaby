"""Ejecutor de migraciones (ADR-0008): orden, huellas y comprobaciones, sin base de datos."""

from pathlib import Path

import pytest

from housefinder.db.migrate import default_migrations_dir, discover, pending


def write(directory: Path, name: str, sql: str = "SELECT 1;") -> None:
    (directory / name).write_text(sql, encoding="utf-8")


def test_las_migraciones_del_repositorio_se_descubren_en_orden():
    versions = [m.version for m in discover(default_migrations_dir())]
    assert versions[:2] == ["0001", "0002"]
    assert versions == sorted(versions)


def test_orden_numerico(tmp_path: Path):
    write(tmp_path, "0010_b.sql")
    write(tmp_path, "0002_a.sql")
    assert [m.name for m in discover(tmp_path)] == ["a", "b"]


def test_nombre_no_valido(tmp_path: Path):
    write(tmp_path, "2_sin_ceros.sql")
    with pytest.raises(ValueError, match="NNNN_nombre"):
        discover(tmp_path)


def test_version_repetida(tmp_path: Path):
    write(tmp_path, "0001_a.sql")
    write(tmp_path, "0001_b.sql")
    with pytest.raises(ValueError, match="repetida"):
        discover(tmp_path)


def test_pendientes(tmp_path: Path):
    write(tmp_path, "0001_a.sql")
    write(tmp_path, "0002_b.sql")
    migrations = discover(tmp_path)
    applied = {"0001": migrations[0].checksum}
    assert [m.version for m in pending(migrations, applied)] == ["0002"]


def test_migracion_aplicada_editada(tmp_path: Path):
    write(tmp_path, "0001_a.sql")
    migrations = discover(tmp_path)
    with pytest.raises(ValueError, match="ha cambiado"):
        pending(migrations, {"0001": "otra-huella"})


def test_migracion_aplicada_sin_fichero(tmp_path: Path):
    write(tmp_path, "0001_a.sql")
    with pytest.raises(ValueError, match="no existe su fichero"):
        pending(discover(tmp_path), {"0001": discover(tmp_path)[0].checksum, "0002": "x"})


def test_migracion_nueva_antes_de_la_ultima_aplicada(tmp_path: Path):
    write(tmp_path, "0001_a.sql")
    write(tmp_path, "0003_c.sql")
    applied = {m.version: m.checksum for m in discover(tmp_path)}
    write(tmp_path, "0002_b.sql")
    with pytest.raises(ValueError, match="va antes"):
        pending(discover(tmp_path), applied)
