"""API del enlace pegado (F4.1) contra la base temporal, sin red: la descarga va contra un sitio
simulado y la extracción, con un LLM falso a través del trabajo `extract_link`."""

from datetime import date
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from conftest import add_section
from fastapi.testclient import TestClient

from housefinder.agent.extraction import ListingExtraction, Quoted
from housefinder.agent.llm import FakeLLMClient
from housefinder.api.deps import (
    get_db,
    get_foral_finder,
    get_geocoder,
    get_link_client,
    get_municipality_finder,
    get_parcel_finder,
    get_resolver,
)
from housefinder.api.main import app
from housefinder.geo.cartociudad import Geocoded
from housefinder.geo.catastro import ParcelNotFound

pytestmark = pytest.mark.db
psycopg = pytest.importorskip("psycopg")

HTML = (Path(__file__).parent / "fixtures" / "enlaces" / "anuncio-sintetico.html").read_text()
NONE = Quoted(value=None, evidence=None)
LISTING = ListingExtraction(
    operation="venta", operation_evidence="Piso en venta", property_type="vivienda",
    property_type_evidence="Piso en venta",
    price=Quoted(value="189500", evidence="189.500 €"),
    built_area_m2=Quoted(value="85", evidence="85 m² construidos"),
    usable_area_m2=NONE, rooms=Quoted(value="3", evidence="3 habitaciones"), bathrooms=NONE,
    floor=NONE, condition=NONE,
    address=Quoted(value="calle de Ejemplo, 12", evidence="en calle de Ejemplo, 12"),
    municipality=Quoted(value="Getafe", evidence="Getafe, Madrid"),
    cadastral_ref=NONE, year_built=NONE,
    community_fees=Quoted(value="70", evidence="Gastos de comunidad: 65 €/mes"),  # mal leído
)


@pytest.fixture
def client(migrated_database: str, monkeypatch):
    # El flujo de ofertas con la organización local de desarrollo; el acceso, en test_access.py
    monkeypatch.setenv("HOUSEFINDER_DEV_ORG", "1")
    pages: dict[str, httpx.Response] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        return pages.get(str(request.url), httpx.Response(404))

    def db():
        with psycopg.connect(migrated_database) as conn:
            yield conn

    def link_client():
        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            yield http

    def no_parcels(ref: str):
        raise ParcelNotFound("sin red en los tests")

    def no_foral(province: str, key: str):
        raise ParcelNotFound("sin red en los tests")

    def geocoder(address: str) -> Geocoded:
        return Geocoded(-3.7322, 40.3057, "portal", address, "28901", None)

    app.dependency_overrides[get_db] = db
    app.dependency_overrides[get_link_client] = link_client
    app.dependency_overrides[get_resolver] = lambda: (lambda host, port: ["93.184.216.34"])
    app.dependency_overrides[get_geocoder] = lambda: geocoder
    app.dependency_overrides[get_parcel_finder] = lambda: no_parcels
    app.dependency_overrides[get_municipality_finder] = lambda: (lambda name: frozenset())
    app.dependency_overrides[get_foral_finder] = lambda: no_foral
    try:
        yield TestClient(app), pages
    finally:
        app.dependency_overrides.clear()


def html(body: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, text=body, headers={"content-type": "text/html"})


def test_enlace_pegado_de_punta_a_punta(client, migrated_database: str):
    from housefinder.offers.run import extract_pasted

    http, pages = client
    url = f"https://portal.ejemplo.test/inmueble/{uuid4()}/"
    pages[url] = html(HTML)
    add_section(migrated_database, "2806597001", -3.7322, 40.3057)

    created = http.post("/offers/link", json={"url": url})
    assert created.status_code == 201
    offer = created.json()
    assert offer["status"] == "pendiente" and offer["source"] == "enlace"
    assert offer["title"] == "Piso en venta en calle de Ejemplo, 12, Getafe"
    assert len(offer["images"]) == 2
    assert all(f["status"] is None for f in offer["fields"])  # aún sin extraer

    # El worker ejecuta el trabajo encolado.
    result = extract_pasted(migrated_database, FakeLLMClient(lambda *a: LISTING),
                            offer["id"])
    assert result == {"extracted": True, "rejected_fields": 1}

    offer = http.get(f"/offers/{offer['id']}").json()
    assert offer["status"] == "extraida" and offer["operation"] == "venta"
    fields = {f["name"]: f for f in offer["fields"]}
    assert fields["price"]["proposed"] == "189500"
    assert fields["price"]["evidence"] == "189.500 €"
    assert fields["community_fees"]["proposed"] is None  # 70 no está en su cita
    assert fields["community_fees"]["reason"] == "el número no aparece en la cita"

    bad = http.post(f"/offers/{offer['id']}/confirm", json={"values": {"rooms": "tres"}})
    assert bad.status_code == 422

    confirmed = http.post(f"/offers/{offer['id']}/confirm", json={
        "operation": "venta",
        "values": {"price": "189500", "built_area_m2": "85", "rooms": "3",
                   "address": "calle de Ejemplo, 12", "municipality": "Getafe",
                   "community_fees": "65"},
    })
    assert confirmed.status_code == 200
    offer = confirmed.json()
    fields = {f["name"]: f for f in offer["fields"]}
    assert offer["status"] == "confirmada" and offer["located"]
    assert offer["location_source"] == "cartociudad"
    assert offer["attribution"].startswith("CC BY 4.0")
    assert fields["price"]["origin"] == "extraido"
    assert fields["community_fees"] == {**fields["community_fees"], "confirmed": "65",
                                        "origin": "usuario"}
    assert offer["id"] in [o["id"] for o in http.get("/offers").json()]


def test_sitio_que_no_deja_descargar_pide_el_texto(client):
    http, pages = client
    url = f"https://portal.ejemplo.test/inmueble/{uuid4()}/"
    pages[url] = html("Acceso denegado", 403)
    refused = http.post("/offers/link", json={"url": url})
    assert refused.status_code == 422
    assert refused.json()["detail"]["paste_text"] is True

    pasted = http.post("/offers/text", json={"text": "Piso en venta en Getafe, 189.500 €, 85 m²",
                                             "url": url})
    assert pasted.status_code == 201
    assert pasted.json()["source"] == "texto" and pasted.json()["url"] == url


def test_oferta_de_otra_organizacion_o_inexistente(client, migrated_database: str):
    from housefinder.db.profiles import create_organization
    from housefinder.offers.pasted import submit_text

    http, _ = client
    with psycopg.connect(migrated_database) as conn:
        other = create_organization(conn, f"Otra {uuid4()}", "profesional")
        foreign = submit_text(conn, other, "Piso en venta en Móstoles por 150.000 euros")
    assert http.get(f"/offers/{foreign.offer_id}").status_code == 404
    assert http.post(f"/offers/{foreign.offer_id}/confirm",
                     json={"values": {"price": "1"}}).status_code == 404
    assert http.get(f"/offers/{uuid4()}").status_code == 404


def test_avisos_de_subastas_de_madrid(client, migrated_database: str):
    from test_boe_auctions import boe_client

    from housefinder.offers.run import run_boe_auctions

    http, _ = client
    with psycopg.connect(migrated_database, autocommit=True) as conn:
        conn.execute("DELETE FROM watch_issues WHERE source = 'offers_boe_subastas'")
    run_boe_auctions(migrated_database, boe_client([]), date(2026, 10, 28), days=2)
    notices = {n["portal_id"]: n for n in http.get("/offers/auctions").json()}
    notice = notices["SUB-JA-2026-267866"]
    assert notice["portal_url"] == "https://subastas.boe.es/ds.php?id=SUB-JA-2026-267866"
    assert notice["court"] == "Sección Civil TI Madrid. Plz.n 31"
    assert notice["published_on"] == "2026-10-27"
    assert notice["boe_url"].endswith("BOE-B-2026-35002")
    assert notice["attribution"].startswith("Fuente: Agencia Estatal")
