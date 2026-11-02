"""API de las ventas directas del Patrimonio (ADR-0037) y de los feeds de agencias (ADR-0038),
contra la base temporal y sin red."""

import os

import pytest
from fastapi.testclient import TestClient
from test_agency_feeds import URL, feed_client
from test_patrimonio import LOT_SHEET, clear_channel, hacienda_client

from housefinder.api.deps import get_db, get_keys
from housefinder.api.main import app

pytestmark = pytest.mark.db
psycopg = pytest.importorskip("psycopg")


@pytest.fixture
def keys():
    from housefinder.crypto.envelope import LocalKeyProvider

    return LocalKeyProvider({"prueba": os.urandom(32)}, "prueba")


@pytest.fixture
def client(migrated_database: str, monkeypatch, keys):
    monkeypatch.setenv("HOUSEFINDER_DEV_ORG", "1")

    def db():
        with psycopg.connect(migrated_database) as conn:
            yield conn

    app.dependency_overrides[get_db] = db
    app.dependency_overrides[get_keys] = lambda: keys
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_ventas_directas_del_patrimonio(client: TestClient, migrated_database: str):
    from housefinder.offers.run import run_patrimonio

    with psycopg.connect(migrated_database, autocommit=True) as conn:
        clear_channel(conn)
    run_patrimonio(migrated_database, hacienda_client([]), lambda content: LOT_SHEET)
    sales = client.get("/patrimonio/sales").json()
    assert len(sales) == 5
    ourense = next(s for s in sales if "Parcela-757" in s["id"])
    assert ourense["delegation"] == "OURENSE"
    assert ourense["deadline"] == "23/03/2027" and ourense["price"] == "1.344,49"
    assert ourense["status"] == "pendiente" and ourense["lots"] == 0
    detail = client.get(f"/patrimonio/sales/{ourense['id']}").json()
    assert detail["url"].startswith("https://www.hacienda.gob.es/")
    assert detail["paragraphs"][0].startswith("Lote 34: parcela n.º 757")
    assert detail["attribution"].startswith("Origen de los datos: Ministerio de Hacienda")
    assert client.get("/patrimonio/sales/VentasDirectas/no-existe.aspx").status_code == 404


def test_alta_lista_cartera_y_baja_de_un_feed(client: TestClient, migrated_database: str, keys):
    from housefinder.feeds.registry import active_feeds
    from housefinder.feeds.run import run_feed

    body = {"agency_name": "Agencia Inventada", "url": URL, "scope": "organizacion",
            "consent_on": "2026-11-01", "consent_ref": "Contrato de alta",
            "consent_confirmed": False}
    refused = client.post("/feeds", json=body)
    assert refused.status_code == 422 and "consentimiento" in refused.json()["detail"]
    bad = client.post("/feeds", json={**body, "url": "ftp://x", "consent_confirmed": True})
    assert bad.status_code == 422
    created = client.post("/feeds", json={**body, "consent_confirmed": True})
    assert created.status_code == 201
    feed = created.json()
    assert "secreto" not in created.text and "crm.example" not in created.text
    assert feed["last_run_at"] is None and feed["scope"] == "organizacion"
    assert feed["id"] in {f["id"] for f in client.get("/feeds").json()}

    # El trabajo diario lee el feed (aquí, a mano y sin red).
    with psycopg.connect(migrated_database) as conn:
        stored = next(f for f in active_feeds(conn, keys)[0] if str(f.id) == feed["id"])
        run_feed(conn, feed_client([]), stored, lambda offer: None)
    after = next(f for f in client.get("/feeds").json() if f["id"] == feed["id"])
    assert (after["listings"], after["without_location"], after["error"]) == (3, 1, None)
    # Las de la organización; otros tests dejan inmuebles cedidos a todos con el mismo nombre.
    own = [x for x in client.get("/feeds/listings").json()
           if x["agency"] == "Feed de Agencia Inventada" and not x["public"]]
    piso = next(x for x in own if x["title"] == "Piso en Getafe")
    assert piso["asking_price"] == "189000" and piso["property_type"] == "vivienda"
    assert piso["located"]
    # La cartera de la agencia no se mezcla con los enlaces pegados de «Ofertas».
    assert piso["id"] not in {o["id"] for o in client.get("/offers").json()}

    assert client.delete(f"/feeds/{feed['id']}").status_code == 204
    assert feed["id"] not in {f["id"] for f in client.get("/feeds").json()}
    assert piso["id"] not in {x["id"] for x in client.get("/feeds/listings").json()}
    assert client.delete(f"/feeds/{feed['id']}").status_code == 404
