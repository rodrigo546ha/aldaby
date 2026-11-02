"""Acceso y separación de datos por organización (F7.1, ADR-0028): la sesión decide la
organización y Row-Level Security es la segunda barrera."""

from uuid import uuid4

import pytest
from test_offer_valuation import database  # noqa: F401

psycopg = pytest.importorskip("psycopg")

PASSWORD = "una frase larga de prueba"


def account(db, email: str, accept: bool = True, role: str = "profesional") -> tuple:
    """Cuenta con contraseña en una organización nueva y, si `accept`, con los textos legales
    vigentes aceptados (ADR-0039): (org_id, correo)."""
    from housefinder.accounts.service import create_account, set_password
    from housefinder.db.legal import record_acceptance
    from housefinder.legal.documents import load, to_accept

    with psycopg.connect(db) as conn:
        account_id, token = create_account(conn, email, f"Org {uuid4()}", role)
        set_password(conn, token, PASSWORD)
        if accept:
            for document, version in to_accept(load(), role).items():
                record_acceptance(conn, account_id, document, version)
        org = conn.execute("SELECT org_id FROM accounts WHERE email = %s", (email,)).fetchone()[0]
        conn.commit()
    return org, email


@pytest.fixture
def client(database, monkeypatch):  # noqa: F811
    from fastapi.testclient import TestClient

    from housefinder.api.deps import API_ROLE, get_db
    from housefinder.api.main import app

    monkeypatch.delenv("HOUSEFINDER_DEV_ORG", raising=False)

    def db():
        with psycopg.connect(database) as conn:
            conn.execute(f"SET ROLE {API_ROLE}")  # como en la API: con las políticas
            yield conn

    app.dependency_overrides[get_db] = db
    try:
        yield TestClient(app, base_url="https://testserver")
    finally:
        app.dependency_overrides.clear()


@pytest.mark.db
def test_sin_sesion_no_hay_datos(client):
    assert client.get("/offers").status_code == 401
    assert client.get("/auth/me").status_code == 401


@pytest.mark.db
def test_cada_profesional_ve_solo_lo_suyo(client, database):  # noqa: F811
    from test_offer_valuation import confirmed_offer

    org_a, email_a = account(database, f"a-{uuid4().hex[:6]}@ejemplo.es")
    org_b, email_b = account(database, f"b-{uuid4().hex[:6]}@ejemplo.es")
    offer_a = confirmed_offer(database, org_a, "venta", "150000")

    login = client.post("/auth/login", json={"email": email_a, "password": PASSWORD})
    assert login.status_code == 200 and login.json() == {"email": email_a, "role": "profesional",
                                                          "pending_legal": [],
                                                          "free_plans_left": None}
    cookie = login.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
    assert [o["id"] for o in client.get("/offers").json()] == [str(offer_a)]
    assert client.get(f"/offers/{offer_a}").status_code == 200

    client.post("/auth/logout")
    assert client.get("/offers").status_code == 401
    client.post("/auth/login", json={"email": email_b, "password": PASSWORD})
    assert client.get("/offers").json() == []
    assert client.get(f"/offers/{offer_a}").status_code == 404


@pytest.mark.db
def test_row_level_security_aunque_el_codigo_no_filtre(database):  # noqa: F811
    from test_offer_valuation import confirmed_offer

    from housefinder.api.deps import API_ROLE

    org_a, _ = account(database, f"c-{uuid4().hex[:6]}@ejemplo.es")
    org_b, _ = account(database, f"d-{uuid4().hex[:6]}@ejemplo.es")
    offer_a = confirmed_offer(database, org_a, "venta", "150000")
    with psycopg.connect(database) as conn:
        conn.execute(f"SET ROLE {API_ROLE}")
        conn.execute("SELECT set_config('app.org_id', %s, false)", (str(org_b),))
        # Una consulta sin filtro por organización no ve la oferta de la otra
        assert conn.execute("SELECT count(*) FROM offers WHERE id = %s",
                            (offer_a,)).fetchone()[0] == 0
        conn.execute("SELECT set_config('app.org_id', %s, false)", (str(org_a),))
        assert conn.execute("SELECT count(*) FROM offers WHERE id = %s",
                            (offer_a,)).fetchone()[0] == 1
        # Y no puede escribir en nombre de otra organización
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("UPDATE offers SET org_id = %s WHERE id = %s", (org_b, offer_a))


@pytest.mark.db
def test_elegir_contrasena_con_el_enlace(client, database):  # noqa: F811
    from housefinder.accounts.service import create_account

    email = f"e-{uuid4().hex[:6]}@ejemplo.es"
    with psycopg.connect(database) as conn:
        _, token = create_account(conn, email, f"Org {uuid4()}", "profesional")
        conn.commit()
    short = client.post("/auth/password", json={"token": token, "password": "corta"})
    assert short.status_code == 400 and "al menos" in short.json()["detail"]
    assert client.post("/auth/password",
                       json={"token": token, "password": PASSWORD}).status_code == 204
    assert client.post("/auth/login",
                       json={"email": email, "password": PASSWORD}).status_code == 200
    assert client.get("/auth/me").json()["email"] == email
