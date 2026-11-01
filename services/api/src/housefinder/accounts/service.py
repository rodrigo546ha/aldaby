"""Cuentas, contraseñas y sesiones (F7.1, ADR-0028).

- Contraseñas con argon2id; nunca se guardan ni se registran en claro.
- Altas por el administrador: la cuenta nace sin contraseña y con un enlace de un solo uso para
  elegirla (el mismo sirve para restablecerla).
- Sesiones con un token aleatorio en una cookie; en la base, solo su hash SHA-256.
- Cinco fallos seguidos bloquean la cuenta quince minutos; el error es el mismo exista o no.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from housefinder.db import accounts as sql
from housefinder.db.connection import Connection
from housefinder.db.profiles import get_or_create_organization

MIN_PASSWORD = 12
SESSION_DAYS = 14  # sin uso
LINK_DAYS = 7
MAX_ATTEMPTS = 5
LOCK_MINUTES = 15
ROLES = ("admin", "profesional")
HASHER = PasswordHasher()  # argon2id con los parámetros por defecto de argon2-cffi
# Para que una cuenta que no existe tarde lo mismo que una que sí (no se distinguen)
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(16))


class AccountError(ValueError):
    """Error que se puede enseñar al usuario: no dice si la cuenta existe."""


@dataclass(frozen=True)
class Session:
    account_id: UUID
    org_id: UUID
    email: str
    role: str


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@") or " " in email:
        raise AccountError("Escribe un correo válido")
    return email


def create_account(conn: Connection, email: str, organization: str, role: str,
                   now: datetime | None = None) -> tuple[UUID, str]:
    """Da de alta una cuenta sin contraseña; devuelve su id y el token del enlace para elegirla."""
    if role not in ROLES:
        raise AccountError(f"Rol desconocido: {role} ({', '.join(ROLES)})")
    email = normalize_email(email)
    if sql.account_by_email(conn, email) is not None:
        raise AccountError("Ya hay una cuenta con ese correo")
    org_id = get_or_create_organization(conn, organization, "profesional")
    account_id = sql.create_account(conn, org_id, email, role)
    return account_id, password_link(conn, account_id, now)


def password_link(conn: Connection, account_id: UUID, now: datetime | None = None) -> str:
    """Token de un solo uso para elegir o restablecer la contraseña."""
    token = secrets.token_urlsafe(32)
    sql.create_token(conn, _hash(token), account_id,
                     (now or _now()) + timedelta(days=LINK_DAYS))
    return token


def reset_link(conn: Connection, email: str, now: datetime | None = None) -> str:
    account = sql.account_by_email(conn, normalize_email(email))
    if account is None:
        raise AccountError("No hay ninguna cuenta con ese correo")
    return password_link(conn, account.id, now)


def set_password(conn: Connection, token: str, password: str,
                 now: datetime | None = None) -> None:
    """Fija la contraseña con un enlace válido y cierra las sesiones abiertas de la cuenta."""
    check_password(password)
    account_id = sql.use_token(conn, _hash(token), now or _now())
    if account_id is None:
        raise AccountError("El enlace no es válido o ha caducado: pide otro")
    sql.set_password_hash(conn, account_id, HASHER.hash(password))
    sql.delete_sessions_of(conn, account_id)


def check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise AccountError(f"La contraseña tiene que tener al menos {MIN_PASSWORD} caracteres")


def log_in(conn: Connection, email: str, password: str,
           now: datetime | None = None) -> tuple[str, Session]:
    """Comprueba la contraseña y abre una sesión; devuelve el token de la cookie."""
    now = now or _now()
    wrong = AccountError("Correo o contraseña incorrectos")
    try:
        email = normalize_email(email)
    except AccountError:
        raise wrong from None
    account = sql.account_by_email(conn, email)
    if account is None or account.password_hash is None:
        _verify(DUMMY_HASH, password)
        raise wrong
    if account.locked_until is not None and account.locked_until > now:
        raise AccountError("Demasiados intentos: espera unos minutos y vuelve a probar")
    if not _verify(account.password_hash, password):
        sql.record_failure(conn, account.id, MAX_ATTEMPTS, now + timedelta(minutes=LOCK_MINUTES))
        raise wrong
    sql.record_success(conn, account.id)
    if HASHER.check_needs_rehash(account.password_hash):
        sql.set_password_hash(conn, account.id, HASHER.hash(password))
    token = secrets.token_urlsafe(32)
    sql.create_session(conn, _hash(token), account.id, now + timedelta(days=SESSION_DAYS))
    return token, Session(account.id, account.org_id, account.email, account.role)


def session(conn: Connection, token: str | None, now: datetime | None = None) -> Session | None:
    """La sesión de una cookie, si sigue vigente (y se alarga)."""
    if not token:
        return None
    now = now or _now()
    account_id = sql.touch_session(conn, _hash(token), now, now + timedelta(days=SESSION_DAYS))
    if account_id is None:
        return None
    account = sql.account_by_id(conn, account_id)
    if account is None:
        return None
    return Session(account.id, account.org_id, account.email, account.role)


def log_out(conn: Connection, token: str | None) -> None:
    if token:
        sql.delete_session(conn, _hash(token))


def _verify(password_hash: str, password: str) -> bool:
    try:
        return HASHER.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)
