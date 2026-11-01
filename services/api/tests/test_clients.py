"""Clientes de un profesional (F7.2, ADR-0029): nombre cifrado, perfil por cliente y borrado."""

import os
from decimal import Decimal
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

D = Decimal


@pytest.fixture
def keys():
    from housefinder.crypto.envelope import LocalKeyProvider

    return LocalKeyProvider({"prueba": os.urandom(32)}, "prueba")


@pytest.fixture
def org(migrated_database):
    from housefinder.db.profiles import create_organization

    with psycopg.connect(migrated_database) as conn:
        org_id = create_organization(conn, f"Clientes {uuid4()}", "profesional")
        conn.commit()
    return org_id


def profile(**changes):
    from housefinder.profiles.model import UserProfile

    return UserProfile(**({"net_monthly_income": D(3000), "available_savings": D(50000),
                           "birth_year": 1980, "residence": "ES-13"} | changes))


@pytest.mark.db
def test_nombre_cifrado_y_perfil_por_cliente(migrated_database, org, keys):
    from housefinder.db.profiles import latest_profile_id
    from housefinder.profiles import clients, store

    with psycopg.connect(migrated_database) as conn:
        maria = clients.create(conn, keys, org, "  María   López ")
        luis = clients.create(conn, keys, org, "Luis")
        stored = conn.execute("SELECT name_enc FROM clients WHERE id = %s", (maria,)).fetchone()
        assert b"Mar" not in bytes(stored[0])  # cifrado
        listed = clients.list_all(conn, keys, org)
        assert [(c.name, c.has_profile) for c in listed] == [("María López", False),
                                                             ("Luis", False)]
        assert "María" not in repr(listed[0])
        first = store.save_new(conn, keys, org, maria, profile())
        conn.commit()  # cada versión en su petición: la hora de la transacción las ordena
        second = store.save_new(conn, keys, org, maria, profile(birth_year=1981))
        assert latest_profile_id(conn, org, maria) == second != first
        assert latest_profile_id(conn, org, luis) is None
        assert [c.has_profile for c in clients.list_all(conn, keys, org)] == [True, False]


@pytest.mark.db
def test_borrar_un_cliente_borra_sus_perfiles_y_su_entrevista(migrated_database, org, keys):
    from housefinder.profiles import clients, interview, store

    with psycopg.connect(migrated_database) as conn:
        client_id = clients.create(conn, keys, org, "Ana")
        store.save_new(conn, keys, org, client_id, profile())
        started = interview.start(conn, keys, org, client_id)
        assert interview.current(conn, keys, org, client_id).id == started.id
        clients.delete(conn, client_id, org)
        assert conn.execute("SELECT count(*) FROM user_profiles WHERE client_id = %s",
                            (client_id,)).fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM profile_interviews WHERE client_id = %s",
                            (client_id,)).fetchone()[0] == 0
        with pytest.raises(clients.ClientError):
            clients.delete(conn, client_id, org)


@pytest.mark.db
def test_la_entrevista_confirma_el_perfil_de_su_cliente(migrated_database, org, keys):
    from housefinder.db.profiles import latest_profile_id
    from housefinder.profiles import clients, interview

    with psycopg.connect(migrated_database) as conn:
        a = clients.create(conn, keys, org, "A")
        b = clients.create(conn, keys, org, "B")
        started = interview.start(conn, keys, org, b)
        assert interview.current(conn, keys, org, a) is None
        values = {"net_monthly_income": "3000", "available_savings": "50000",
                  "birth_year": 1980, "residence": "ES-13"}
        profile_id = interview.confirm(conn, keys, started.id, org, "local", values)
        assert latest_profile_id(conn, org, b) == profile_id
        assert latest_profile_id(conn, org, a) is None


@pytest.mark.db
def test_api_de_clientes_y_cliente_activo(migrated_database, keys):
    from fastapi.testclient import TestClient

    from housefinder.api.deps import get_db, get_keys, get_org
    from housefinder.api.main import app
    from housefinder.db.profiles import create_organization
    from housefinder.profiles import store

    with psycopg.connect(migrated_database) as conn:
        mine = create_organization(conn, f"Mía {uuid4()}", "profesional")
        other = create_organization(conn, f"Otra {uuid4()}", "profesional")
        conn.commit()
    current = {"org": mine}

    def db():
        with psycopg.connect(migrated_database) as conn:
            yield conn

    app.dependency_overrides.update({get_db: db, get_keys: lambda: keys,
                                     get_org: lambda: current["org"]})
    try:
        api = TestClient(app, base_url="https://testserver")
        assert api.get("/profile/current").json()["detail"] == "Crea primero un cliente en Clientes"
        ana = api.post("/clients", json={"name": "Ana"}).json()
        assert ana["active"] is True and api.cookies.get("hf_cliente") == ana["id"]
        luis = api.post("/clients", json={"name": "  Luis  "}).json()
        assert luis["name"] == "Luis"
        with psycopg.connect(migrated_database) as conn:
            store.save_new(conn, keys, mine, ana["id"], profile())
            conn.commit()
        assert api.get("/profile/current").status_code == 404  # Luis, el activo, sin perfil
        assert api.put("/clients/active", json={"client_id": ana["id"]}).status_code == 204
        assert api.get("/profile/current").status_code == 200
        listed = api.get("/clients").json()
        assert [(c["name"], c["active"], c["has_profile"]) for c in listed] == [
            ("Ana", True, True), ("Luis", False, False)]
        # Sin cookie y con dos clientes, hay que elegir
        api.cookies.clear()
        assert api.get("/profile/current").status_code == 409
        # Otra organización no puede elegir ni borrar un cliente que no es suyo
        current["org"] = other
        assert api.put("/clients/active", json={"client_id": ana["id"]}).status_code == 404
        assert api.delete(f"/clients/{ana['id']}").status_code == 404
        current["org"] = mine
        api.put("/clients/active", json={"client_id": ana["id"]})
        assert api.delete(f"/clients/{ana['id']}").status_code == 204
        assert "hf_cliente" not in api.cookies
        assert [c["name"] for c in api.get("/clients").json()] == ["Luis"]
    finally:
        app.dependency_overrides.clear()
