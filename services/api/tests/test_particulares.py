"""Particulares (F8.1 y F8.2, ADR-0041): lista de espera, cuenta propia y nivel gratuito."""

import os
from uuid import uuid4

import pytest
from fastapi import HTTPException

from housefinder.accounts.tiers import FreeTier, free_tier, plans_left

psycopg = pytest.importorskip("psycopg")


def test_el_limite_del_nivel_gratuito_es_un_dato():
    assert free_tier() == FreeTier(full_plans=3)
    assert plans_left(0, FreeTier(3)) == 3 and plans_left(5, FreeTier(3)) == 0


@pytest.fixture
def keys():
    from housefinder.crypto.envelope import LocalKeyProvider

    return LocalKeyProvider({"prueba": os.urandom(32)}, "prueba")


@pytest.fixture
def client(migrated_database: str, monkeypatch, keys):
    from fastapi.testclient import TestClient

    from housefinder.api.deps import API_ROLE, get_db, get_keys
    from housefinder.api.main import app

    monkeypatch.delenv("HOUSEFINDER_DEV_ORG", raising=False)

    def db():
        with psycopg.connect(migrated_database) as conn:
            conn.execute(f"SET ROLE {API_ROLE}")
            yield conn

    app.dependency_overrides[get_db] = db
    app.dependency_overrides[get_keys] = lambda: keys
    try:
        yield TestClient(app, base_url="https://testserver")
    finally:
        app.dependency_overrides.clear()


@pytest.mark.db
def test_lista_de_espera(client, migrated_database: str):
    email = f"Espera-{uuid4().hex[:6]}@Ejemplo.es"
    body = {"email": email, "kind": "particular", "consent": False}
    assert client.post("/waitlist", json=body).status_code == 422
    assert client.post("/waitlist", json={**body, "email": "sin-arroba",
                                          "consent": True}).status_code == 422
    first = client.post("/waitlist", json={**body, "consent": True})
    again = client.post("/waitlist", json={**body, "kind": "profesional", "consent": True})
    assert first.status_code == again.status_code == 201
    assert first.json() == again.json()  # no dice si ya estaba
    with psycopg.connect(migrated_database) as conn:
        row = conn.execute("SELECT kind, privacy_version, invited_at FROM waitlist "
                           "WHERE email = %s", (email.lower(),)).fetchone()
        columns = {r[0] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'waitlist'").fetchall()}
    assert row == ("particular", 3, None)  # el primero manda; privacidad vigente
    assert columns == {"email", "kind", "privacy_version", "created_at", "invited_at"}


@pytest.mark.db
def test_alta_de_un_particular_desde_la_lista(client, migrated_database: str):
    from housefinder.accounts.service import create_account

    email = f"luis-{uuid4().hex[:6]}@ejemplo.es"
    client.post("/waitlist", json={"email": email, "kind": "particular", "consent": True})
    with psycopg.connect(migrated_database) as conn:
        create_account(conn, email, email, "particular")
        conn.commit()
        kind = conn.execute("SELECT o.kind FROM organizations o JOIN accounts a "
                            "ON a.org_id = o.id WHERE a.email = %s", (email,)).fetchone()[0]
        invited = conn.execute("SELECT invited_at FROM waitlist WHERE email = %s",
                               (email,)).fetchone()[0]
    assert kind == "particular" and invited is not None


@pytest.mark.db
def test_un_particular_tiene_su_perfil_y_tres_planes(client, migrated_database: str):
    from test_access import PASSWORD, account

    from housefinder.api.deps import check_full_plan

    org, email = account(migrated_database, f"p-{uuid4().hex[:6]}@ejemplo.es", accept=False,
                         role="particular")
    login = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()
    # Acepta sus condiciones y la privacidad; el encargo no es para él.
    assert login["pending_legal"] == ["condiciones-particulares", "privacidad"]
    assert login["free_plans_left"] == 3
    client.post("/legal/accept",
                json={"documents": {"condiciones-particulares": 1, "privacidad": 3}})

    # Su perfil se crea solo, sin pasar por Clientes.
    missing = client.get("/profile/current")
    assert missing.status_code == 404 and "perfil" in missing.json()["detail"]  # sin confirmar
    clients = client.get("/clients").json()
    assert [c["name"] for c in clients] == ["Mi perfil"]

    with psycopg.connect(migrated_database) as conn:
        offers = [conn.execute(
            "INSERT INTO offers (channel, external_id, kind, raw, raw_sha256) "
            "VALUES ('prueba', %s, 'lote', '{}', '') RETURNING id", (str(uuid4()),)
        ).fetchone()[0] for _ in range(4)]
        for offer in offers[:3]:
            assert check_full_plan(conn, org, offer, particular=True)
            conn.execute("INSERT INTO plan_uses (org_id, offer_id) VALUES (%s, %s)", (org, offer))
        assert not check_full_plan(conn, org, offers[0], particular=True)  # ya abierta: no gasta
        with pytest.raises(HTTPException) as exhausted:
            check_full_plan(conn, org, offers[3], particular=True)
        assert exhausted.value.status_code == 402
        assert not check_full_plan(conn, org, offers[3], particular=False)  # profesional
        # El asesor (herramienta plan_completo) gasta el mismo cupo: sin planes libres, solo las ya
        # abiertas; a un profesional no se le limita
        from housefinder.api.deps import plan_gate
        gate = plan_gate(conn, org, particular=True)
        assert gate is not None and gate(offers[0]) is None
        refusal = gate(offers[3])
        assert refusal is not None and "planes completos" in refusal
        assert plan_gate(conn, org, particular=False) is None
        conn.commit()
    assert client.get("/auth/me").json()["free_plans_left"] == 0


def test_el_asesor_anota_el_plan_que_cuenta(migrated_database: str):
    # Con planes libres, el plan completo de otra oferta que cuenta el asesor queda anotado
    from test_access import account

    from housefinder.api.deps import plan_gate

    org, _ = account(migrated_database, f"p-{uuid4().hex[:6]}@ejemplo.es", role="particular")
    with psycopg.connect(migrated_database) as conn:
        offer = conn.execute(
            "INSERT INTO offers (channel, external_id, kind, raw, raw_sha256) "
            "VALUES ('prueba', %s, 'lote', '{}', '') RETURNING id", (str(uuid4()),)
        ).fetchone()[0]
        conn.commit()
        gate = plan_gate(conn, org, particular=True)
        assert gate is not None and gate(offer) is None
        used = conn.execute("SELECT offer_id FROM plan_uses WHERE org_id = %s", (org,)).fetchall()
    assert used == [(offer,)]
