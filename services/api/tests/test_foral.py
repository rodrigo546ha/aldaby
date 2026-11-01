"""Catastros forales (ADR-0032), con respuestas reales del 2026-11-01: la parcela del lote
BOE-B-2026-34912#1 en Azpeitia (Gipuzkoa, cuatro versiones), una de Abadiño (Bizkaia), una de
Álava y la parcela 339 del polígono 1 de Abáigar (Navarra, IDENA)."""

import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from conftest import add_section

from housefinder.geo.catastro import CatastroUnavailable, ParcelNotFound
from housefinder.geo.foral import (
    ARABA,
    BIZKAIA,
    GIPUZKOA,
    NAVARRA,
    find_foral_parcel,
    foral_key,
    point_on_surface,
)

FIXTURES = Path(__file__).parent / "fixtures" / "foral"
NAVARRA_JSON = json.loads((FIXTURES / "navarra-1-1-339.json").read_text())


def serve(name: str, seen: list[httpx.Request] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(200, content=(FIXTURES / name).read_bytes())

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.mark.parametrize("province, ref, key", [
    ("20", "2001860840226144403E", ("20", "018-6084022")),  # el lote de Azpeitia
    (None, "2001860840226144403E", ("20", "018-6084022")),  # su forma basta
    (None, "48.001.1055.99082", ("48", "48.001.1055.99082")),
    ("48", "48001105599082", ("48", "48.001.1055.99082")),
    ("01", "64010007", ("01", "64010007")),
    (None, "64010007", None),  # 8 cifras solo con la provincia
    (None, "7744401VK6874N0001FJ", None),  # Dirección General del Catastro
    (None, "24142A50100014", None),
    ("20", "7744401VK6874N0001FJ", None),
    ("20", "82950960147121N", ("20", "-8295096")),  # Donostia, sin provincia ni municipio
    (None, "82950960147121N", None),  # esa forma, solo si la oferta es de Gipuzkoa
])
def test_forma_de_las_referencias_forales(province, ref, key):
    assert foral_key(province, ref) == key


def test_gipuzkoa_la_version_vigente_de_la_parcela_del_municipio():
    seen: list[httpx.Request] = []
    parcel = find_foral_parcel(serve("gipuzkoa-018-6084022.xml", seen), "20", "018-6084022")
    assert (parcel.lon, parcel.lat) == (-2.254271, 43.21035)  # (lat, lon) en EPSG:4258
    assert parcel.parcel_ref == "018-6084022"
    assert str(seen[0].url).startswith(GIPUZKOA.url)
    assert "<fes:Literal>6084022</fes:Literal>" in seen[0].url.params["FILTER"]
    # La misma parcela en otro municipio no vale.
    with pytest.raises(ParcelNotFound, match="0 parcelas vigentes"):
        find_foral_parcel(serve("gipuzkoa-018-6084022.xml"), "20", "016-6084022")


def test_gipuzkoa_sin_municipio_la_unica_parcela_vigente_con_ese_numero():
    """BOE-B-2026-33449: «82950960147121N». El WFS da tres versiones de la parcela 8295096 de
    Donostia (069); una vigente."""
    parcel = find_foral_parcel(serve("gipuzkoa-8295096.xml"), "20", "-8295096")
    assert (parcel.lon, parcel.lat) == (-1.981216, 43.309551)


def test_bizkaia_y_alava_por_su_referencia():
    bizkaia = find_foral_parcel(serve("bizkaia-48.001.1055.99082.xml"), "48",
                                "48.001.1055.99082")
    assert (bizkaia.lon, bizkaia.lat) == (-2.605134499, 43.169572999)
    seen: list[httpx.Request] = []
    araba = find_foral_parcel(serve("araba-64010007.xml", seen), "01", "64010007")
    assert (araba.lon, araba.lat) == (-2.65383126, 42.63649752)  # «epsg.xml#4258»: (lon, lat)
    assert str(seen[0].url).startswith(ARABA.url) and seen[0].url.params["SRSNAME"] == "EPSG:4258"
    assert BIZKAIA.province == "48"


def test_navarra_por_municipio_poligono_y_parcela():
    seen: list[httpx.Request] = []
    parcel = find_foral_parcel(serve("navarra-1-1-339.json", seen), "31", "31001-1-339")
    assert parcel.address == "Polígono 1 Parcela 339 ABÁIGAR (NAVARRA)"
    assert str(seen[0].url).startswith(NAVARRA.url)
    assert seen[0].url.params["CQL_FILTER"] == "CMUNICIPIO=1 AND POLIGONO=1 AND PARCELA=339"
    ring = NAVARRA_JSON["features"][0]["geometry"]["coordinates"][0][0]
    assert inside(parcel.lon, parcel.lat, ring)


def test_un_punto_dentro_aunque_el_centroide_caiga_fuera():
    # Una «U»: su centroide cae en el hueco.
    u = [[0, 0], [3, 0], [3, 3], [2, 3], [2, 1], [1, 1], [1, 3], [0, 3], [0, 0]]
    lon, lat = point_on_surface({"type": "Polygon", "coordinates": [u]})
    assert inside(lon, lat, u)


def test_servicio_foral_caido():
    down = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with pytest.raises(CatastroUnavailable, match="Gipuzkoa no responde: HTTP 503"):
        find_foral_parcel(down, "20", "018-6084022")
    with pytest.raises(CatastroUnavailable, match="Navarra no responde"):
        find_foral_parcel(down, "31", "31001-1-339")


def inside(x: float, y: float, ring: list[list[float]]) -> bool:
    crossings = 0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            crossings += 1
    return crossings % 2 == 1


# --- En el localizador ---------------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")


@pytest.mark.db
def test_los_lotes_forales_se_ubican_con_su_catastro(migrated_database: str):
    from housefinder.geo.foral import find_foral_parcel as real
    from housefinder.offers.ingest import Point
    from housefinder.offers.locate import offer_locator
    from housefinder.offers.model import NormalizedOffer

    add_section(migrated_database, "2001801001", -2.2543, 43.2103)
    add_section(migrated_database, "3100101001", -2.1259, 42.6435)
    asked: list[tuple[str, str]] = []

    def foral(province, key):
        asked.append((province, key))
        name = "gipuzkoa-018-6084022.xml" if province == "20" else "navarra-1-1-339.json"
        return real(serve(name), province, key)

    def no_catastro(*args):
        raise AssertionError("la Dirección General del Catastro no cubre estos territorios")

    codes = {"Azpeitia": frozenset({"20018"}), "Abáigar": frozenset({"31001"})}
    with psycopg.connect(migrated_database) as conn:
        conn.execute("DELETE FROM geocode_cache WHERE query LIKE 'foral:%'")
        conn.commit()
        locate = offer_locator(conn, no_catastro, no_catastro, no_catastro,
                               municipalities=lambda name: codes.get(name, frozenset()),
                               foral=foral)
        azpeitia = locate(NormalizedOffer(
            external_id="BOE-B-2026-34912#1", kind="lote", url="", municipality="Azpeitia",
            province="Gipuzkoa", cadastral_ref="2001860840226144403E"))
        abaigar = locate(NormalizedOffer(
            external_id=f"n-{uuid4()}", kind="lote", url="", municipality="Abáigar",
            province="Navarra", address="Paraje San Miguel, polígono 1, parcela 339"))
        locate(NormalizedOffer(  # de la caché: no se vuelve a preguntar
            external_id="otra", kind="lote", url="", municipality="Azpeitia",
            province="Gipuzkoa", cadastral_ref="2001860840226144403E"))
    assert azpeitia == Point(-2.254271, 43.21035, "gipuzkoa-catastro-wfs")
    assert isinstance(abaigar, Point) and abaigar.source == "idena-catastro-navarra"
    assert asked == [("20", "018-6084022"), ("31", "31001-1-339")]
