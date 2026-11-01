"""SQL de cuentas, enlaces de contraseña y sesiones (F7.1, ADR-0028). Solo hashes de tokens."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import psycopg


@dataclass(frozen=True)
class AccountRow:
    id: UUID
    org_id: UUID
    email: str
    password_hash: str | None
    role: str
    failed_attempts: int
    locked_until: datetime | None


_ACCOUNT = ("SELECT id, org_id, email, password_hash, role, failed_attempts, locked_until "
            "FROM accounts")


def create_account(conn: psycopg.Connection, org_id: UUID, email: str, role: str) -> UUID:
    row = conn.execute(
        "INSERT INTO accounts (org_id, email, role) VALUES (%s, %s, %s) RETURNING id",
        (org_id, email, role),
    ).fetchone()
    assert row is not None
    return row[0]


def account_by_email(conn: psycopg.Connection, email: str) -> AccountRow | None:
    row = conn.execute(_ACCOUNT + " WHERE email = %s", (email,)).fetchone()
    return AccountRow(*row) if row else None


def account_by_id(conn: psycopg.Connection, account_id: UUID) -> AccountRow | None:
    row = conn.execute(_ACCOUNT + " WHERE id = %s", (account_id,)).fetchone()
    return AccountRow(*row) if row else None


def set_password_hash(conn: psycopg.Connection, account_id: UUID, password_hash: str) -> None:
    conn.execute(
        "UPDATE accounts SET password_hash = %s, failed_attempts = 0, locked_until = NULL "
        "WHERE id = %s",
        (password_hash, account_id),
    )


def record_failure(conn: psycopg.Connection, account_id: UUID, max_attempts: int,
                   lock_until: datetime) -> None:
    """Un fallo más; al llegar a `max_attempts`, la cuenta se bloquea hasta `lock_until`."""
    conn.execute(
        """
        UPDATE accounts SET
            failed_attempts = CASE WHEN failed_attempts + 1 >= %s THEN 0
                                   ELSE failed_attempts + 1 END,
            locked_until = CASE WHEN failed_attempts + 1 >= %s THEN %s ELSE locked_until END
        WHERE id = %s
        """,
        (max_attempts, max_attempts, lock_until, account_id),
    )


def record_success(conn: psycopg.Connection, account_id: UUID) -> None:
    conn.execute(
        "UPDATE accounts SET failed_attempts = 0, locked_until = NULL WHERE id = %s",
        (account_id,),
    )


def create_token(conn: psycopg.Connection, token_hash: str, account_id: UUID,
                 expires_at: datetime) -> None:
    conn.execute(
        "INSERT INTO account_tokens (token_hash, account_id, expires_at) VALUES (%s, %s, %s)",
        (token_hash, account_id, expires_at),
    )


def use_token(conn: psycopg.Connection, token_hash: str, now: datetime) -> UUID | None:
    """La cuenta del enlace, si es válido; lo marca usado (un solo uso)."""
    row = conn.execute(
        """
        UPDATE account_tokens SET used_at = %s
        WHERE token_hash = %s AND used_at IS NULL AND expires_at > %s
        RETURNING account_id
        """,
        (now, token_hash, now),
    ).fetchone()
    return row[0] if row else None


def create_session(conn: psycopg.Connection, token_hash: str, account_id: UUID,
                   expires_at: datetime) -> None:
    conn.execute(
        "INSERT INTO sessions (token_hash, account_id, expires_at) VALUES (%s, %s, %s)",
        (token_hash, account_id, expires_at),
    )


def touch_session(conn: psycopg.Connection, token_hash: str, now: datetime,
                  expires_at: datetime) -> UUID | None:
    """La cuenta de una sesión vigente, alargando su caducidad; None si caducó o no existe."""
    row = conn.execute(
        """
        UPDATE sessions SET last_seen = %s, expires_at = %s
        WHERE token_hash = %s AND expires_at > %s
        RETURNING account_id
        """,
        (now, expires_at, token_hash, now),
    ).fetchone()
    return row[0] if row else None


def delete_session(conn: psycopg.Connection, token_hash: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token_hash = %s", (token_hash,))


def delete_sessions_of(conn: psycopg.Connection, account_id: UUID) -> None:
    """Cierra todas las sesiones de una cuenta (al cambiar la contraseña)."""
    conn.execute("DELETE FROM sessions WHERE account_id = %s", (account_id,))
