"""Canal del Portal de Subastas del BOE (ADR-0053), con las páginas del Portal guardadas en
`fixtures/boe/portal` y un Catastro falso."""

from decimal import Decimal
from pathlib import Path

import httpx
import psycopg
import pytest

from housefinder.geo.cartociudad import AddressNotFound
from housefinder.geo.catastro import CadastralUnit, ParcelNotFound
from housefinder.offers.boe_portal import offer_from_record, property_type
from housefinder.offers.channels.subastas_portal import PortalAuctions

FIXTURES = Path(__file__).parent / "fixtures" / "boe" / "portal"
REF = "9402504VK3790C0005KT"  # la de la vivienda de single_ver3.html


def portal(searches: list[str] | None = None) -> httpx.Client:
    """Todas las subastas de la búsqueda devuelven las pestañas de la misma subasta."""
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "subastas_ava.php" in url:
            if searches is not None:
                searches.append(request.content.decode())
            return httpx.Response(200, content=(FIXTURES / "search_madrid.html").read_bytes())
        for ver in range(1, 6):
            if f"ver={ver}" in url:
                return httpx.Response(
                    200, content=(FIXTURES / f"single_ver{ver}.html").read_bytes())
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def residential(ref: str) -> CadastralUnit:
    if ref != REF:
        raise ParcelNotFound("no está")
    return CadastralUnit(ref, Decimal("60"), "Residencial", 1960)


def test_cada_subasta_nueva_se_descarga_y_sus_lotes_son_ofertas():
    searches: list[str] = []
    channel = PortalAuctions({}, units=residential, pause_s=0, limit=2)
    items = list(channel.fetch(portal(searches)))
    assert len(items) == 2 and channel.postponed == 36  # 38 en la búsqueda, dos por ejecución
    assert len(searches) == 2  # celebrándose y próxima apertura
    assert "BIEN.COD_PROVINCIA" in searches[0] and "page_hits=500" in searches[0]
    raw = items[0].raw
    assert raw["search"]["state"].startswith("Celebrándose")
    assert raw["catastro"][REF]["built_area_m2"] == "60"
    assert set(raw["html"]) >= {"ver1", "ver3"}  # lo recibido, tal cual
    (offer,) = channel.parse(items[0])
    assert offer.kind == "lote" and offer.asking_price is None
    assert offer.auction_min_bid == Decimal("130560.00")
    assert offer.built_area_m2 == Decimal("60")
    assert offer.extraction_status == "no_aplica"
    assert offer.extracted["catastro"]["use"] == "Residencial"
    assert offer.extracted["portal"]["status"].startswith("Celebrándose")


def test_lo_que_no_cambia_en_la_busqueda_no_se_vuelve_a_bajar():
    first = list(PortalAuctions({}, units=residential, pause_s=0, limit=1).fetch(portal()))
    known = {first[0].raw["search"]["portal_id"]: first[0].raw["search"]["state"]}
    channel = PortalAuctions(known, units=residential, pause_s=0, limit=1)
    again = list(channel.fetch(portal()))
    assert channel.unchanged == 1
    assert again[0].external_id != first[0].external_id


def test_la_superficie_de_otro_uso_no_vale_para_una_vivienda():
    record = {"external_id": "SUB-JA-1", "url": "u", "portal_id": "SUB-JA-2026-1", "lot": 1,
              "title": None, "auction_value": "100000.00", "deposit": None, "address": "x",
              "cadastral_ref": REF, "property_kind": "Inmueble (Vivienda)"}
    garage = {"built_area_m2": "12", "use": "Almacen-Estacionamiento"}
    assert offer_from_record(record, garage).built_area_m2 is None
    assert offer_from_record(record, {"built_area_m2": "60", "use": "Residencial"}
                             ).built_area_m2 == Decimal("60")
    assert property_type("Inmueble (Garaje)") == "garaje"
    assert property_type("Inmueble (Nave industrial)") == "otro"
    assert property_type(None) is None


@pytest.mark.db
def test_canal_de_punta_a_punta(migrated_database: str):
    from housefinder.offers.run import run_boe_portal

    with psycopg.connect(migrated_database, autocommit=True) as conn:
        conn.execute("DELETE FROM offer_raw_versions WHERE offer_id IN "
                     "(SELECT id FROM offers WHERE channel = 'boe_subasta_portal')")
        conn.execute("DELETE FROM offers WHERE channel = 'boe_subasta_portal'")

    def nowhere(_query):
        raise ParcelNotFound("sin red en los tests")

    def no_address(_query):
        raise AddressNotFound("sin red en los tests")

    # Las 38 de la búsqueda (con las pestañas de la misma subasta de ejemplo): 38 lotes
    first = run_boe_portal(migrated_database, portal(), geocoder=no_address,
                           parcels=nowhere, units=residential, pause_s=0)
    assert first["items"] == 38 and first["offers_new"] == 38 and not first["failed"]
    again = run_boe_portal(migrated_database, portal(), geocoder=no_address,
                           parcels=nowhere, units=residential, pause_s=0)
    assert again["items"] == 0 and again["unchanged"] == 38
    with psycopg.connect(migrated_database) as conn:
        rows = conn.execute(
            "SELECT DISTINCT kind, org_id, asking_price, auction_min_bid, built_area_m2, "
            "extracted->>'property_type', source_id FROM offers "
            "WHERE channel = 'boe_subasta_portal'").fetchall()
    assert rows == [("lote", None, None, Decimal("130560.00"), Decimal("60"), "vivienda",
                   "boe-portal-subastas")]
