"""Conexión a la base de datos para la API y los trabajos (ADR-0008)."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

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
