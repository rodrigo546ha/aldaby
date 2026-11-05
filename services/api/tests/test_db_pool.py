"""Pool de conexiones de la API (ADR-0058): una conexión vuelve al pool sin el rol ni la
organización de la petición anterior, también si la petición acabó con error."""

from uuid import uuid4

import pytest

from housefinder.db import connection
from housefinder.db.connection import DatabaseUnavailable, pooled

psycopg = pytest.importorskip("psycopg")


@pytest.fixture
def one_connection(migrated_database, monkeypatch):
    """Un pool propio de una sola conexión: la segunda petición recibe la misma que la primera."""
    monkeypatch.setenv("DB_POOL_MAX", "1")
    monkeypatch.setattr(connection, "POOL_TIMEOUT", 0.5)
    from psycopg.conninfo import make_conninfo

    url = make_conninfo(migrated_database, application_name=f"prueba-pool-{uuid4().hex[:8]}")
    yield url
    pool = connection._POOLS.pop(url, None)
    if pool is not None:
        pool.close()


def session_state(conn) -> tuple[str, str, str | None]:
    return conn.execute(
        "SELECT current_user, session_user, current_setting('app.org_id', true)").fetchone()


@pytest.mark.db
def test_la_organizacion_y_el_rol_no_pasan_a_la_peticion_siguiente(one_connection):
    with pooled(one_connection) as conn:
        pid = conn.info.backend_pid
        conn.execute("SET ROLE housefinder_api")
        conn.execute("SELECT set_config('app.org_id', %s, false)", (str(uuid4()),))
        user, owner, org = session_state(conn)
        assert user == "housefinder_api" and org
    with pooled(one_connection) as conn:
        assert conn.info.backend_pid == pid  # la misma conexión, reutilizada
        user, owner, org = session_state(conn)
        assert user == owner  # sin el rol de la API
        assert not org  # sin organización: Row-Level Security no deja ver nada de nadie


@pytest.mark.db
def test_tampoco_si_la_peticion_acaba_con_error(one_connection):
    with pytest.raises(RuntimeError), pooled(one_connection) as conn:
        pid = conn.info.backend_pid
        conn.execute("SET ROLE housefinder_api")
        conn.execute("SELECT set_config('app.org_id', %s, false)", (str(uuid4()),))
        raise RuntimeError("la petición falla a medias")
    with pooled(one_connection) as conn:
        assert conn.info.backend_pid == pid
        user, owner, org = session_state(conn)
        assert user == owner and not org


@pytest.mark.db
def test_sin_conexiones_libres_la_base_no_responde(one_connection):
    with pooled(one_connection), pytest.raises(DatabaseUnavailable), pooled(one_connection):
        pass  # la única conexión está prestada: se espera POOL_TIMEOUT y se rinde


@pytest.mark.db
def test_una_conexion_cerrada_por_la_base_no_se_presta(one_connection):
    with pooled(one_connection) as conn:
        pid = conn.info.backend_pid
    with psycopg.connect(one_connection, autocommit=True) as admin:
        admin.execute("SELECT pg_terminate_backend(%s)", (pid,))
    with pooled(one_connection) as conn:  # el pool la comprueba, la descarta y abre otra
        assert conn.info.backend_pid != pid
        assert conn.execute("SELECT 1").fetchone() == (1,)
