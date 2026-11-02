"""Textos legales versionados y su aceptación (F7.4, ADR-0039)."""

from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest

from housefinder.legal.documents import fill, load, parse, pending, to_accept

DOC = """---
id: prueba
title: Prueba de {{servicio}}
version: 3
effective_from: 2026-11-02
requires_acceptance: true
verified: false
---
Titular: {{titular}}. Correo: {{correo}}. Otra vez: {{titular}}.
"""


def test_los_huecos_sin_dato_quedan_pendientes_y_no_se_inventan():
    text, missing = fill("{{servicio}} de {{titular}}",
                         {"servicio": "HouseFinder", "titular": None})
    assert text == "HouseFinder de [pendiente: razón social del titular]"
    assert missing == ("titular",)
    doc = parse(DOC, {"servicio": "HouseFinder", "correo": "hola@ejemplo.es"})
    assert doc.title == "Prueba de HouseFinder" and doc.version == 3
    assert doc.effective_from == date(2026, 11, 2) and not doc.verified
    assert doc.text.count("[pendiente: razón social del titular]") == 2
    assert "hola@ejemplo.es" in doc.text and doc.missing == ("titular",)


def test_los_textos_del_repositorio():
    docs = load()
    assert set(docs) == {"aviso-legal", "condiciones", "condiciones-particulares", "privacidad",
                         "encargo", "cookies", "clausula-clientes"}
    assert to_accept(docs) == {"condiciones": 1, "privacidad": 3, "encargo": 1}
    # El particular no firma el encargo: Aldaby es el responsable de sus datos (ADR-0041).
    assert to_accept(docs, "particular") == {"condiciones-particulares": 1, "privacidad": 3}
    assert to_accept(docs, "admin") == to_accept(docs, "profesional")
    assert not any(d.verified for d in docs.values())  # hasta que los revise el abogado
    # Lo que dicen tiene que ser lo que hace el código: las dos cookies y sus duraciones.
    from housefinder.accounts.service import SESSION_DAYS
    from housefinder.api.clients import COOKIE_DAYS
    from housefinder.api.deps import CLIENT_COOKIE, SESSION_COOKIE

    cookies = docs["cookies"].text
    assert f"`{SESSION_COOKIE}`" in cookies and f"{SESSION_DAYS} días" in cookies
    assert f"`{CLIENT_COOKIE}`" in cookies and f"{COOKIE_DAYS} días" in cookies
    assert f"{SESSION_DAYS} días" in docs["privacidad"].text


def test_que_falta_por_aceptar():
    docs = load()
    assert pending(docs, {}) == ["condiciones", "encargo", "privacidad"]
    assert pending(docs, {"condiciones": 1, "encargo": 1, "privacidad": 3}) == []
    assert pending(docs, {"condiciones": 1, "encargo": 1, "privacidad": 2}) == ["privacidad"]
    assert pending(docs, {"condiciones": 1, "privacidad": 3}, "particular") == [
        "condiciones-particulares"]


def test_el_id_tiene_que_coincidir_con_el_fichero(tmp_path: Path):
    (tmp_path / "titular.yaml").write_text("servicio: X\n", encoding="utf-8")
    (tmp_path / "otro.md").write_text(DOC, encoding="utf-8")
    with pytest.raises(ValueError, match="no coincide"):
        load.__wrapped__(tmp_path)


# --- Contra la base -----------------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")


@pytest.fixture
def client(migrated_database: str, monkeypatch):
    from fastapi.testclient import TestClient

    from housefinder.api.deps import API_ROLE, get_db
    from housefinder.api.main import app

    monkeypatch.delenv("HOUSEFINDER_DEV_ORG", raising=False)

    def db():
        with psycopg.connect(migrated_database) as conn:
            conn.execute(f"SET ROLE {API_ROLE}")
            yield conn

    app.dependency_overrides[get_db] = db
    try:
        yield TestClient(app, base_url="https://testserver")
    finally:
        app.dependency_overrides.clear()


@pytest.mark.db
def test_sin_aceptar_no_se_entra_en_los_datos(client, migrated_database: str):
    from test_access import PASSWORD, account

    _, email = account(migrated_database, f"l-{uuid4().hex[:6]}@ejemplo.es", accept=False)
    # Los textos se leen sin sesión.
    assert client.get("/legal/privacidad").json()["verified"] is False
    assert client.get("/legal/no-existe").status_code == 404
    assert client.post("/legal/accept", json={"documents": {"condiciones": 1}}).status_code == 401

    login = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert login.json()["pending_legal"] == ["condiciones", "encargo", "privacidad"]
    blocked = client.get("/offers")
    assert blocked.status_code == 403 and "condiciones" in blocked.json()["detail"]

    stale = client.post("/legal/accept", json={"documents": {"condiciones": 0}})
    assert stale.status_code == 409  # una versión que no es la vigente
    assert client.post("/legal/accept",
                       json={"documents": {"cookies": 1}}).status_code == 422
    partial = client.post("/legal/accept", json={"documents": {"condiciones": 1}})
    assert partial.json() == {"pending": ["encargo", "privacidad"]}
    assert client.get("/offers").status_code == 403
    done = client.post("/legal/accept", json={"documents": {"encargo": 1, "privacidad": 3}})
    assert done.json() == {"pending": []}
    assert client.get("/offers").status_code == 200
    assert client.get("/auth/me").json()["pending_legal"] == []
    with psycopg.connect(migrated_database) as conn:
        columns = {r[0] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'legal_acceptances'").fetchall()}
    assert columns == {"account_id", "document", "version", "accepted_at"}  # ni IP ni navegador
