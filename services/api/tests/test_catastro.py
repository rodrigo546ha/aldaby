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
    DNPPP_URL,
    DNPRC_URL,
    CatastroUnavailable,
    Parcel,
    ParcelNotFound,
    find_parcel,
    find_rustic_parcel,
    find_unit,
    parcel_ref,
    parse_cpmrc,
    parse_dnppp,
    parse_dnprc,
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
    with pytest.raises(CatastroUnavailable, match="^El Catastro no responde: HTTP 503$"):
        find_parcel(down, "7744401VK6874N")


# Consulta_DNPPP real del 2026-11-01: Sahagún (León), polígono 501, parcela 14 (BOE-B-2026-34360).
RUSTIC = json.loads((FIXTURES / "dnppp-sahagun-501-14.json").read_text())
NO_RUSTIC = json.loads((FIXTURES / "dnppp-no-existe.json").read_text())


def test_referencia_de_una_finca_rustica_por_poligono_y_parcela():
    assert parse_dnppp(RUSTIC) == "24142A50100014"
    with pytest.raises(ParcelNotFound, match="NO EXISTE NINGÚN INMUEBLE"):
        parse_dnppp(NO_RUSTIC)
    two = {"consulta_dnpppResult": {"lrcdnp": {"rcdnp": [
        {"rc": {"pc1": "24142A5", "pc2": "0100014"}},
        {"rc": {"pc1": "24142A5", "pc2": "0100015"}}]}}}
    with pytest.raises(ParcelNotFound, match="2 parcelas"):
        parse_dnppp(two)


def test_peticion_por_poligono_y_parcela():
    seen: list[httpx.Request] = []

    def ok(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=RUSTIC)

    client = httpx.Client(transport=httpx.MockTransport(ok))
    assert find_rustic_parcel(client, "León", "Sahagún", "501", "14") == "24142A50100014"
    assert str(seen[0].url).startswith(DNPPP_URL)
    assert dict(seen[0].url.params) == {"Provincia": "León", "Municipio": "Sahagún",
                                        "Poligono": "501", "Parcela": "14"}
    down = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    with pytest.raises(CatastroUnavailable, match="HTTP 500"):
        find_rustic_parcel(down, "León", "Sahagún", "501", "14")


@pytest.mark.parametrize("expected, address, same", [
    ("Alcalá de Henares", "CR CAMARMA 21 ALCALA DE HENARES (MADRID)", True),
    ("Sahagún (León)", "Polígono 501 Parcela 14 C GALLEGUILLOS. SAHAGUN (LEÓN)", True),
    ("alcala de henares", "CR CAMARMA 21 ALCALA DE HENARES (MADRID)", True),
    ("Madrid", "CR CAMARMA 21 ALCALA DE HENARES (MADRID)", False),  # la provincia no cuenta
    ("Alcalá de Henares", "CL ALCALA DE HENARES 3 MADRID (MADRID)", False),  # la calle tampoco
    ("Madrid", None, False),
    # BOE-B-2026-31848: el anuncio dice «Cangas de Narcea».
    ("Cangas de Narcea", "Polígono 1 Parcela 96 CALDEVILLA DE RENGOS. CANGAS DEL NARCEA "
                         "(ASTURIAS)", True),
    # BOE-B-2026-32556: en castellano el anuncio, en valenciano el Catastro.
    ("Algimia de Alfara", "Polígono 10 Parcela 199 HIELOS. ALGIMIA D'ALFARA (VALENCIA)", True),
    # BOE-B-2026-32777: un paraje entre dos municipios; la parcela es de uno de ellos.
    ("Monforte de Lemos e Pobra de Brollón",
     "Polígono 506 Parcela 773 ALON, AS. A POBRA DO BROLLON (LUGO)", True),
    ("Alcalá de Henares", "Polígono 1 Parcela 2 ALCALA DEL JUCAR (ALBACETE)", False),
])
def test_municipio_de_la_direccion_catastral(expected, address, same):
    assert parcel_in_municipality(expected, address) is same


# --- Localizador: primero el Catastro, después la dirección ------------------------------------

psycopg = pytest.importorskip("psycopg")


@pytest.mark.db
def test_el_catastro_va_primero_y_la_direccion_es_la_reserva(migrated_database: str):
    from housefinder.geo.cartociudad import Geocoded
    from housefinder.offers.ingest import Unlocated
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
        # Sin dirección, sin ubicar, con el motivo; no se reintenta.
        assert locate(offer("9999999XX9999X")) == Unlocated(
            "9999999XX9999X: LA REFERENCIA CATASTRAL NO EXISTE", retry=False)


# --- Superficie y uso del inmueble (Consulta_DNPRC, ADR-0053), respuestas reales del 2026-11-04 ---


def test_superficie_y_uso_del_inmueble():
    unit = parse_dnprc(json.loads((FIXTURES / "dnprc-9402504VK3790C0005KT.json").read_text()))
    assert unit.ref == "9402504VK3790C0005KT"
    assert str(unit.built_area_m2) == "60" and unit.use == "Residencial"
    assert unit.built_year == 1960
    with pytest.raises(ParcelNotFound, match="CORRECTAMENTE FORMADA"):
        parse_dnprc(json.loads((FIXTURES / "dnprc-no-existe.json").read_text()))


def test_la_superficie_pide_la_referencia_completa():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=(FIXTURES / "dnprc-9402504VK3790C0005KT.json"
                                            ).read_bytes())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(ParcelNotFound, match="20 caracteres"):
        find_unit(client, "9402504VK3790C")  # solo la parcela: no se pregunta
    assert not seen
    assert find_unit(client, "9402504 VK3790C 0005 KT").use == "Residencial"
    assert str(seen[0].url).startswith(DNPRC_URL)
    assert seen[0].url.params["RefCat"] == "9402504VK3790C0005KT"

