"""SQL de la lista de espera de la página de presentación (ADR-0040). Sin IP ni navegador."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import psycopg


@dataclass(frozen=True)
class WaitlistRow:
    email: str
    kind: str
    privacy_version: int
    created_at: datetime
    invited_at: datetime | None


def join_waitlist(conn: psycopg.Connection, email: str, kind: str, privacy_version: int) -> None:
    """Apunta el correo. Si ya estaba, no cambia nada: la respuesta es la misma en los dos casos."""
    conn.execute(
        "INSERT INTO waitlist (email, kind, privacy_version) VALUES (%s, %s, %s) "
        "ON CONFLICT (email) DO NOTHING",
        (email, kind, privacy_version),
    )


def list_waitlist(conn: psycopg.Connection) -> list[WaitlistRow]:
    rows = conn.execute(
        "SELECT email, kind, privacy_version, created_at, invited_at FROM waitlist "
        "ORDER BY created_at"
    ).fetchall()
    return [WaitlistRow(*r) for r in rows]


def mark_invited(conn: psycopg.Connection, email: str) -> None:
    conn.execute("UPDATE waitlist SET invited_at = now() WHERE email = %s AND invited_at IS NULL",
                 (email,))
