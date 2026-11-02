"""Programaciones declaradas en data/jobs/programaciones.yaml (ADR-0010)."""

from datetime import UTC, datetime, time
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from housefinder.jobs import schedules
from housefinder.jobs.handlers import build_handlers

MADRID = ZoneInfo("Europe/Madrid")
LLM_ENV = {"LLM_PROVIDER": "openai_compatible", "LLM_BASE_URL": "http://llm.test/v1",
           "LLM_MODEL_ID": "qwen3:8b"}


def test_el_fichero_solo_usa_trabajos_que_existen():
    loaded = schedules.load()
    kinds = set(build_handlers("postgresql://sin-conexion"))
    assert loaded.timezone == MADRID
    assert {s.kind for s in loaded.schedules} <= kinds
    names = {s.name for s in loaded.schedules}
    assert {"oferta-boe-seccion-v", "oferta-boe-subastas-judiciales",
            "oferta-extraccion-boe"} <= names
    extraction = next(s for s in loaded.schedules if s.kind == "extract_offers")
    assert set(extraction.requires_env) == set(LLM_ENV)


@pytest.mark.parametrize("now, expected", [
    # 29/10/2026, horario de invierno (UTC+1): a las 8:00 de Madrid toca hoy a las 9:00.
    (datetime(2026, 10, 29, 7, 0, tzinfo=UTC), datetime(2026, 10, 29, 8, 0, tzinfo=UTC)),
    # A las 9:30 de Madrid ya pasó: mañana.
    (datetime(2026, 10, 29, 8, 30, tzinfo=UTC), datetime(2026, 10, 30, 8, 0, tzinfo=UTC)),
    # 28/03/2027 cambia a verano (UTC+2): las 9:00 de Madrid son las 7:00 UTC.
    (datetime(2027, 3, 27, 12, 0, tzinfo=UTC), datetime(2027, 3, 28, 7, 0, tzinfo=UTC)),
])
def test_primera_ejecucion_en_hora_de_madrid(now, expected):
    assert schedules.first_run(time(9, 0), MADRID, now) == expected


# --- Contra la base -----------------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")


@pytest.mark.db
def test_aplicar_el_fichero(migrated_database: str):
    from housefinder.db.jobs import upsert_schedule

    loaded = schedules.load()
    kinds = set(build_handlers(migrated_database))
    now = datetime(2026, 10, 29, 7, 0, tzinfo=UTC)
    old = f"programacion-retirada-{uuid4()}"
    with psycopg.connect(migrated_database, autocommit=True) as conn:
        upsert_schedule(conn, old, "watch_boe", {}, 3600)

        without_llm = schedules.sync(conn, loaded, kinds, {}, now)
        assert "oferta-extraccion-boe" not in without_llm.programmed
        assert without_llm.skipped["oferta-extraccion-boe"].startswith("falta LLM_")
        assert old in without_llm.disabled
        rows = dict(conn.execute(
            "SELECT name, next_run_at FROM job_schedules WHERE name = ANY(%s)",
            (without_llm.programmed,)).fetchall())
        assert rows["oferta-boe-seccion-v"] == datetime(2026, 10, 29, 8, 0, tzinfo=UTC)

        with_llm = schedules.sync(conn, loaded, kinds, LLM_ENV, now)
        assert "oferta-extraccion-boe" in with_llm.programmed and not with_llm.skipped
        enabled = conn.execute(
            "SELECT count(*) FROM job_schedules WHERE enabled AND name = ANY(%s)",
            ([s.name for s in loaded.schedules],)).fetchone()[0]
        assert enabled == len(loaded.schedules)
        # Sin el LLM otra vez: la extracción se desactiva en vez de fallar cada día.
        again = schedules.sync(conn, loaded, kinds, {}, now)
        assert sorted(again.disabled) == ["oferta-extraccion-boe", "oferta-extraccion-patrimonio"]


def test_un_tipo_desconocido_no_se_programa():
    spec = schedules.ScheduleSpec("x", "no_existe", time(9, 0), 24)
    unknown = schedules.ScheduleFile(MADRID, [spec])
    with pytest.raises(ValueError, match="desconocido"):
        schedules.sync(None, unknown, {"watch_boe"}, {},  # type: ignore[arg-type]
                       datetime(2026, 10, 29, tzinfo=UTC))
