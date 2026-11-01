"""Cuentas, contraseñas y sesiones (F7.1, ADR-0028)."""

from datetime import UTC, datetime, timedelta

import pytest

psycopg = pytest.importorskip("psycopg")

NOW = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)
PASSWORD = "una frase larga de prueba"


@pytest.fixture
def conn(migrated_database):
    with psycopg.connect(migrated_database) as c:
        yield c


@pytest.mark.db
def test_alta_enlace_contrasena_y_sesion(conn):
    from housefinder.accounts.service import create_account, log_in, session, set_password

    account_id, token = create_account(conn, " Ana@Ejemplo.es ", "Asesoría Ana", "profesional",
                                       NOW)
    stored = conn.execute("SELECT email, password_hash FROM accounts WHERE id = %s",
                          (account_id,)).fetchone()
    assert stored == ("ana@ejemplo.es", None)  # en minúsculas y sin contraseña hasta el enlace
    assert token not in str(conn.execute("SELECT * FROM account_tokens").fetchall())
    set_password(conn, token, PASSWORD, NOW)
    password_hash = conn.execute("SELECT password_hash FROM accounts WHERE id = %s",
                                 (account_id,)).fetchone()[0]
    assert password_hash.startswith("$argon2id$") and PASSWORD not in password_hash
    cookie, opened = log_in(conn, "ana@ejemplo.es", PASSWORD, NOW)
    assert opened.role == "profesional"
    current = session(conn, cookie, NOW + timedelta(days=13))
    assert current is not None and current.org_id == opened.org_id
    # Catorce días sin uso desde el último: caduca
    assert session(conn, cookie, NOW + timedelta(days=13 + 15)) is None


@pytest.mark.db
def test_el_enlace_es_de_un_solo_uso_y_caduca(conn):
    from housefinder.accounts.service import AccountError, create_account, set_password

    _, token = create_account(conn, "luis@ejemplo.es", "Luis", "profesional", NOW)
    with pytest.raises(AccountError, match="al menos"):
        set_password(conn, token, "corta", NOW)
    set_password(conn, token, PASSWORD, NOW)
    with pytest.raises(AccountError, match="no es válido"):
        set_password(conn, token, PASSWORD, NOW)
    _, late = create_account(conn, "eva@ejemplo.es", "Eva", "profesional", NOW)
    with pytest.raises(AccountError, match="caducado"):
        set_password(conn, late, PASSWORD, NOW + timedelta(days=8))


@pytest.mark.db
def test_mismo_error_exista_o_no_y_bloqueo(conn):
    from housefinder.accounts.service import (
        MAX_ATTEMPTS,
        AccountError,
        create_account,
        log_in,
        set_password,
    )

    _, token = create_account(conn, "mar@ejemplo.es", "Mar", "profesional", NOW)
    set_password(conn, token, PASSWORD, NOW)
    errors = set()
    for email in ("mar@ejemplo.es", "nadie@ejemplo.es"):
        with pytest.raises(AccountError) as exc:
            log_in(conn, email, "mal mal mal mal", NOW)
        errors.add(str(exc.value))
    assert errors == {"Correo o contraseña incorrectos"}
    for _ in range(MAX_ATTEMPTS - 1):
        with pytest.raises(AccountError):
            log_in(conn, "mar@ejemplo.es", "mal mal mal mal", NOW)
    with pytest.raises(AccountError, match="Demasiados intentos"):
        log_in(conn, "mar@ejemplo.es", PASSWORD, NOW + timedelta(minutes=5))
    log_in(conn, "mar@ejemplo.es", PASSWORD, NOW + timedelta(minutes=16))  # ya desbloqueada


@pytest.mark.db
def test_cambiar_la_contrasena_cierra_las_sesiones(conn):
    from housefinder.accounts.service import (
        create_account,
        log_in,
        log_out,
        reset_link,
        session,
        set_password,
    )

    _, token = create_account(conn, "sol@ejemplo.es", "Sol", "admin", NOW)
    set_password(conn, token, PASSWORD, NOW)
    first, _ = log_in(conn, "sol@ejemplo.es", PASSWORD, NOW)
    second, _ = log_in(conn, "sol@ejemplo.es", PASSWORD, NOW)
    log_out(conn, first)
    assert session(conn, first, NOW) is None and session(conn, second, NOW) is not None
    set_password(conn, reset_link(conn, "SOL@ejemplo.es", NOW), "otra frase bastante larga",
                 NOW)
    assert session(conn, second, NOW) is None
