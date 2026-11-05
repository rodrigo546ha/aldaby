"""Conexión a la base de datos para la API y los trabajos (ADR-0008).

La API toma sus conexiones de un pool (`pooled`, ADR-0058): abrir una costaba unos 280 ms por
petición. Los trabajos, las órdenes de terminal y las ingestas abren la suya (`connect`).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from threading import Lock

import psycopg
from psycopg_pool import ConnectionPool, PoolTimeout

Connection = psycopg.Connection


class DatabaseUnavailable(RuntimeError):
    """No hay DATABASE_URL o la base no responde."""


@contextmanager
def connect(
    conninfo: str | None = None, autocommit: bool = False
) -> Iterator[psycopg.Connection]:
    """Conexión a `conninfo` o, si no se da, a `DATABASE_URL`."""
    url = conninfo or os.environ.get("DATABASE_URL")
    if not url:
        raise DatabaseUnavailable("Falta DATABASE_URL")
    try:
        conn = psycopg.connect(url, connect_timeout=5, autocommit=autocommit)
    except psycopg.OperationalError as exc:
        raise DatabaseUnavailable("La base de datos no responde") from exc
    with conn:
        yield conn


POOL_TIMEOUT = 10.0  # segundos esperando una conexión libre antes de responder 503
_POOLS: dict[str, ConnectionPool] = {}
_POOLS_LOCK = Lock()


def reset_session(conn: psycopg.Connection) -> None:
    """Lo que una petición deja en su sesión no pasa a la siguiente: ni el rol ni la organización
    con la que filtra Row-Level Security (`app.org_id`, ADR-0028). El pool lo ejecuta al devolver
    cada conexión; si falla, la descarta."""
    conn.execute("RESET ROLE")
    conn.execute("RESET ALL")
    conn.commit()


def _pool(url: str) -> ConnectionPool:
    with _POOLS_LOCK:
        pool = _POOLS.get(url)
        if pool is None or pool.closed:
            pool = ConnectionPool(
                url,
                min_size=1,
                max_size=int(os.environ.get("DB_POOL_MAX", "10")),
                kwargs={"connect_timeout": 5},
                reset=reset_session,
                check=ConnectionPool.check_connection,  # fuera las que la base haya cerrado
                timeout=POOL_TIMEOUT,
                name="api",
                open=True,
            )
            _POOLS[url] = pool
        return pool


@contextmanager
def pooled(conninfo: str | None = None) -> Iterator[psycopg.Connection]:
    """Una conexión del pool de `conninfo` o de `DATABASE_URL`. Al salir se confirma (o se deshace
    si hubo una excepción), se limpia la sesión y vuelve al pool."""
    url = conninfo or os.environ.get("DATABASE_URL")
    if not url:
        raise DatabaseUnavailable("Falta DATABASE_URL")
    try:
        with _pool(url).connection() as conn:
            yield conn
    except PoolTimeout as exc:
        raise DatabaseUnavailable("La base de datos no responde") from exc


def close_pools() -> None:
    """Al parar la API."""
    with _POOLS_LOCK:
        for pool in _POOLS.values():
            pool.close()
        _POOLS.clear()
