"""Ubicación por referencia catastral (ADR-0016), con las respuestas reales de Consulta_CPMRC
guardadas el 2026-10-29: la parcela 7744401VK6874N del anuncio BOE-B-2026-35273 (Alcalá de
Henares) y una referencia que no existe."""

import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from conftest import add_section

from housefinder.geo.catastro import (
    CPMRC_URL,
    Parcel,
    ParcelNotFound,
    find_parcel,
    parcel_ref,
    parse_cpmrc,
)
from housefinder.offers.locate import parcel_in_municipality

FIXTURES = Path(__file__).parent / "fixtures" / "catastro"
FOUND = json.loads((FIXTURES / "cpmrc-7744401VK6874N.json").read_text())
MISSING = json.loads((FIXTURES / "cpmrc-no-existe.json").read_text())


def test_centroide_y_direccion_de_la_parcela():
    parcel = parse_cpmrc(FOUND)
    assert parcel == Parcel(lon=-3.38292397305892, lat=40.5108798607498,
                            parcel_ref="7744401VK6874N",
                            address="CR CAMARMA 21 ALCALA DE HENARES (MADRID)")


def test_referencia_que_no_existe():
    with pytest.raises(ParcelNotFound, match="NO EXISTE"):
        parse_cpmrc(MISSING)


@pytest.mark.parametrize("ref, parcel", [
    ("7744401VK6874N0001FJ", "7744401VK6874N"),
    ("7744401 vk6874n 0001fj", "7744401VK6874N"),
    ("7744401VK6874N", "7744401VK6874N"),
])
def test_solo_se_envia_la_parcela(ref, parcel):
    assert parcel_ref(ref) == parcel


@pytest.mark.parametrize("ref", ["", "7744401", "7744401VK687-N"])
def test_referencia_mal_formada(ref):
    with pytest.raises(ParcelNotFound):
        parcel_ref(ref)


def test_peticion_y_caida_del_servicio():
    seen: list[httpx.Request] = []

    def ok(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=FOUND)

    client = httpx.Client(transport=httpx.MockTransport(ok))
    assert find_parcel(client, "7744401VK6874N0001FJ").parcel_ref == "7744401VK6874N"
    assert str(seen[0].url).startswith(CPMRC_URL)
    assert dict(seen[0].url.params) == {"SRS": "EPSG:4326", "RefCat": "7744401VK6874N"}

    down = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with pytest.raises(ParcelNotFound, match="no responde"):
        find_parcel(down, "7744401VK6874N")


@pytest.mark.parametrize("expected, address, same", [
    ("Alcalá de Henares", "CR CAMARMA 21 ALCALA DE HENARES (MADRID)", True),
    ("alcala de henares", "CR CAMARMA 21 ALCALA DE HENARES (MADRID)", True),
    ("Madrid", "CR CAMARMA 21 ALCALA DE HENARES (MADRID)", False),  # la provincia no cuenta
    ("Alcalá de Henares", "CL ALCALA DE HENARES 3 MADRID (MADRID)", False),  # la calle tampoco
    ("Madrid", None, False),
])
def test_municipio_de_la_direccion_catastral(expected, address, same):
    assert parcel_in_municipality(expected, address) is same


# --- Localizador: primero el Catastro, después la dirección ------------------------------------

psycopg = pytest.importorskip("psycopg")


@pytest.mark.db
def test_el_catastro_va_primero_y_la_direccion_es_la_reserva(migrated_database: str):
    from housefinder.geo.cartociudad import Geocoded
    from housefinder.offers.locate import offer_locator
    from housefinder.offers.model import NormalizedOffer

    add_section(migrated_database, "2800597003", -3.3829, 40.5109)
    add_section(migrated_database, "2800597004", -3.3500, 40.4800)
    parcel_calls: list[str] = []

    def parcels(ref: str) -> Parcel:
        parcel_calls.append(ref)
        if ref.startswith("77444"):
            return parse_cpmrc(FOUND)
        if ref.startswith("11111"):  # una parcela fuera de la zona cargada
            return Parcel(-0.8062, 37.8102, ref, "CL MAYOR 1 SAN JAVIER (MURCIA)")
        raise ParcelNotFound("LA REFERENCIA CATASTRAL NO EXISTE")

    def geocoder(address: str) -> Geocoded:
        return Geocoded(-3.3500, 40.4800, "portal", "CALLE MAYOR 1, 28801 Alcalá de Henares",
                        "28005", None)

    def offer(ref: str, address: str | None = None) -> NormalizedOffer:
        return NormalizedOffer(external_id="", kind="lote", url="", cadastral_ref=ref,
                               address=address, municipality="Alcalá de Henares")

    with psycopg.connect(migrated_database) as conn:
        conn.execute("DELETE FROM geocode_cache WHERE query LIKE 'rc:%'")
        conn.commit()
        locate = offer_locator(conn, geocoder, parcels)

        point = locate(offer("7744401VK6874N0001FJ", "porción de terreno sin portal"))
        assert (point.lon, point.lat, point.source) == (-3.38292397305892, 40.5108798607498,
                                                        "catastro")
        locate(offer("7744401VK6874N0002GK"))  # otro piso de la misma parcela: de la caché
        assert parcel_calls == ["7744401VK6874N"]

        # El Catastro no la tiene o la da fuera de la zona: se prueba con la dirección.
        for ref in ("9999999XX9999X", "1111111XX1111X"):
            fallback = locate(offer(ref, f"Calle Mayor 1 {uuid4()}"))
            assert fallback is not None and fallback.source == "cartociudad"
        assert locate(offer("9999999XX9999X")) is None  # sin dirección, sin ubicar
