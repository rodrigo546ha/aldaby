"""Cola de trabajos (ADR-0010): esperas, reserva concurrente, reintentos, préstamos caducados,
programaciones y alertas. Cada test usa sus propios tipos de trabajo para no pisarse."""

import uuid
from datetime import timedelta

import pytest

from housefinder.db.jobs import claim, enqueue, enqueue_due, upsert_schedule
from housefinder.jobs.retry import backoff
from housefinder.jobs.worker import Worker


@pytest.mark.parametrize(("attempt", "minutes"), [(1, 1), (2, 2), (3, 4), (6, 32), (7, 60),
                                                  (20, 60)])
def test_espera_creciente_con_tope(attempt, minutes):
    assert backoff(attempt) == timedelta(minutes=minutes)


def test_los_intentos_empiezan_en_uno():
    with pytest.raises(ValueError):
        backoff(0)


# --- Contra la base de datos -------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")


def kind() -> str:
    return f"prueba_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def conn(migrated_database: str):
    with psycopg.connect(migrated_database, autocommit=True) as connection:
        yield connection


def job_row(conn, job_id):
    return conn.execute(
        "SELECT status, attempts, last_error, payload FROM jobs WHERE id = %s", (job_id,)
    ).fetchone()


def runs(conn, job_id):
    return conn.execute(
        "SELECT attempt, ok, result, error FROM job_runs WHERE job_id = %s ORDER BY id",
        (job_id,),
    ).fetchall()


@pytest.mark.db
def test_una_sola_copia_viva_por_clave(conn):
    k, key = kind(), f"clave-{uuid.uuid4().hex[:8]}"
    first = enqueue(conn, k, {"a": 1}, dedupe_key=key)
    assert first is not None
    assert enqueue(conn, k, {"a": 2}, dedupe_key=key) is None
    conn.execute("UPDATE jobs SET status = 'hecho' WHERE id = %s", (first,))
    assert enqueue(conn, k, {"a": 3}, dedupe_key=key) is not None  # la anterior ya terminó


@pytest.mark.db
def test_dos_workers_no_reservan_el_mismo_trabajo(migrated_database: str):
    k = kind()
    with psycopg.connect(migrated_database, autocommit=True) as a, \
            psycopg.connect(migrated_database, autocommit=True) as b:
        ids = {enqueue(a, k), enqueue(a, k)}
        b.execute("SET statement_timeout = '3s'")  # si SKIP LOCKED fallara, b se bloquearía
        with a.transaction():
            first = claim(a, "worker-a", [k])  # fila bloqueada hasta el final de la transacción
            second = claim(b, "worker-b", [k])
            third = claim(b, "worker-b", [k])
        assert first is not None and second is not None
        assert {first.id, second.id} == ids
        assert third is None


@pytest.mark.db
def test_no_reserva_trabajos_futuros_ni_de_otros_tipos(conn):
    k = kind()
    conn.execute("INSERT INTO jobs (kind, run_after) VALUES (%s, now() + interval '1 hour')",
                 (k,))
    assert claim(conn, "w", [k]) is None
    assert claim(conn, "w", [kind()]) is None


@pytest.mark.db
def test_trabajo_que_sale_bien(conn, migrated_database):
    k = kind()
    job_id = enqueue(conn, k, {"year": 2025})
    seen = []
    worker = Worker(migrated_database, {k: lambda p: seen.append(p) or {"filas": 3}},
                    name="w-ok")
    assert worker.run_once().id == job_id
    assert seen == [{"year": 2025}]
    assert job_row(conn, job_id)[:2] == ("hecho", 1)
    assert runs(conn, job_id) == [(1, True, {"filas": 3}, None)]
    assert worker.run_once() is None  # ya no queda nada de ese tipo


@pytest.mark.db
def test_reintentos_y_alerta_al_agotarlos(conn, migrated_database):
    k = kind()
    job_id = enqueue(conn, k, {}, max_attempts=3)
    alerts = []

    def broken(payload):
        raise RuntimeError("el INE no responde")

    worker = Worker(migrated_database, {k: broken}, name="w-ko",
                    retry_delay=lambda attempt: timedelta(0),  # sin esperar en el test
                    alert=lambda job, error: alerts.append((job.id, job.attempts, error)))
    for attempt in (1, 2):
        worker.run_once()
        status, attempts, error, _ = job_row(conn, job_id)
        assert (status, attempts) == ("pendiente", attempt)
        assert error == "RuntimeError: el INE no responde"
        assert alerts == []
    worker.run_once()
    assert job_row(conn, job_id)[:2] == ("fallido", 3)
    assert alerts == [(job_id, 3, "RuntimeError: el INE no responde")]
    assert [ok for _, ok, _, _ in runs(conn, job_id)] == [False, False, False]


@pytest.mark.db
def test_la_espera_retrasa_el_reintento(conn, migrated_database):
    k = kind()
    job_id = enqueue(conn, k)
    worker = Worker(migrated_database, {k: lambda p: 1 / 0}, name="w-espera")
    worker.run_once()
    delay = conn.execute("SELECT run_after - now() FROM jobs WHERE id = %s",
                         (job_id,)).fetchone()[0]
    assert timedelta(seconds=50) < delay <= timedelta(minutes=1)  # backoff(1) = 1 minuto
    assert worker.run_once() is None  # todavía no toca


@pytest.mark.db
def test_prestamo_caducado(conn, migrated_database):
    k = kind()
    retried = enqueue(conn, k, max_attempts=2)
    exhausted = enqueue(conn, k, max_attempts=1)
    for job_id in (retried, exhausted):
        conn.execute(
            "UPDATE jobs SET status = 'en_curso', attempts = 1, locked_by = 'caido', "
            "locked_at = now() - interval '2 hours' WHERE id = %s", (job_id,))
    alerts = []
    worker = Worker(migrated_database, {}, name="w-rescate",
                    alert=lambda job, error: alerts.append(job.id))
    worker.run_once()
    assert job_row(conn, retried)[0] == "pendiente"
    assert job_row(conn, exhausted)[0] == "fallido"
    assert alerts == [exhausted]
    assert runs(conn, retried)[0][1:] == (False, None, "préstamo caducado: el worker no "
                                                       "terminó el trabajo")


@pytest.mark.db
def test_programacion_vencida_encola_una_sola_copia(conn):
    k, name = kind(), f"diaria-{uuid.uuid4().hex[:8]}"
    upsert_schedule(conn, name, k, {"province": "28"}, 86400)
    # El worker estuvo parado tres días.
    conn.execute("UPDATE job_schedules SET next_run_at = now() - interval '3 days 1 hour' "
                 "WHERE name = %s", (name,))
    assert name in enqueue_due(conn)
    pending = conn.execute("SELECT count(*), min(payload::text) FROM jobs WHERE kind = %s",
                           (k,)).fetchone()
    assert pending == (1, '{"province": "28"}')
    next_run = conn.execute("SELECT next_run_at - now() FROM job_schedules WHERE name = %s",
                            (name,)).fetchone()[0]
    assert timedelta(0) < next_run <= timedelta(days=1)  # mantiene la hora del día
    assert name not in enqueue_due(conn)  # ya no está vencida
