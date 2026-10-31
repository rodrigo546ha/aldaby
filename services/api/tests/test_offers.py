"""Ofertas (G5): canal BOE sección V, versiones de lo recibido, ubicación y deduplicación.

El canal se prueba con un sumario y un anuncio reales (tests/fixtures/boe/); la deduplicación,
con un canal sintético y una sección inventada lejos de las de otros tests.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from housefinder.offers.channels.boe_v import BoeSectionV, is_property_sale, parse_announcement
from housefinder.offers.ingest import Point
from housefinder.offers.model import NormalizedOffer, RawItem

FIXTURES = Path(__file__).parent / "fixtures" / "boe"
ANNOUNCEMENT = (FIXTURES / "anuncio-BOE-B-2026-35273.xml").read_bytes()


def test_el_anuncio_se_guarda_entero_con_la_extraccion_pendiente():
    raw = parse_announcement(ANNOUNCEMENT)
    assert raw["metadatos"]["identificador"] == "BOE-B-2026-35273"
    assert raw["metadatos"]["seccion"] == "5"
    assert any("tipo de licitación" in p for p in raw["texto"])
    item = RawItem("BOE-B-2026-35273", "https://www.boe.es/x", date(2026, 10, 28), raw)
    [offer] = BoeSectionV([]).parse(item)
    assert offer.kind == "anuncio" and offer.extraction_status == "pendiente"
    assert offer.title.startswith("Resolución de la Dirección Provincial de la Tesorería")
    # Nada de precio ni ubicación por reglas: lo extraerá el LLM con su evidencia (F6.1).
    assert offer.auction_min_bid is None and not offer.locatable


def test_solo_ventas_o_subastas_de_inmuebles_en_la_seccion_v():
    assert is_property_sale("5B", "Resolución … por la que se anuncia subasta pública de "
                                  "inmuebles")
    assert not is_property_sale("3", "Subasta pública de inmuebles")
    # Filtro ampliado (docs/research/f4-filtro-seccion-v.md): «bienes patrimoniales» y en
    # cualquier orden; la venta de otras cosas sigue fuera.
    assert is_property_sale("5B", "… convoca subasta pública al alza … de bienes patrimoniales "
                                  "propiedad de la Administración General del Estado")
    assert is_property_sale("5B", "… exclusión de una finca rústica de la subasta pública …")
    assert not is_property_sale("5B", "… subasta pública de cuatro aeronaves en situación de "
                                      "presunción legal de abandono.")
    assert not is_property_sale("5B", "… enajenación por Subasta Pública de diverso material de "
                                      "chatarra.")
    assert not is_property_sale("5A", "Anuncio de licitación del servicio de limpieza")


def test_la_huella_no_depende_del_orden():
    a = RawItem("x", "u", None, {"a": 1, "b": [1, 2]})
    b = RawItem("x", "u", None, {"b": [1, 2], "a": 1})
    assert a.sha256 == b.sha256


# --- Contra la base de datos -------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")


class FakeChannel:
    name = "prueba"
    source_id = None

    def __init__(self, offers):
        self.offers = offers

    def fetch(self, client):
        return iter(())

    def parse(self, item):
        return self.offers[item.external_id]


def offer(external_id, **kw):
    return NormalizedOffer(external_id=external_id, kind="enlace", url=f"https://x/{external_id}",
                           **kw)


@pytest.fixture(scope="module")
def database(migrated_database: str) -> str:
    from housefinder.db.sections import SectionRow, upsert_sections

    ring = [[-3.40, 40.60], [-3.39, 40.60], [-3.39, 40.61], [-3.40, 40.61], [-3.40, 40.60]]
    with psycopg.connect(migrated_database) as conn:
        upsert_sections(conn, [SectionRow("2807998001", "28079", json.dumps(
            {"type": "MultiPolygon", "coordinates": [[ring]]}))], 2025, None)
        conn.commit()
    return migrated_database


@pytest.fixture
def conn(database):
    with psycopg.connect(database) as connection:
        yield connection


def ingest_one(conn, channel_offers, external_id, raw=None, locate=lambda o: None):
    from housefinder.offers.ingest import ingest

    channel = FakeChannel({external_id: channel_offers})
    return ingest(conn, channel, [RawItem(external_id, "u", None, raw or {"id": external_id})],
                  locate)


@pytest.mark.db
def test_inmueble_con_seccion_y_deduplicado_por_referencia_catastral(conn):
    ref = "1234567VK4713A0001XY"
    first = ingest_one(conn, [offer("a1", cadastral_ref=ref, lon=-3.395, lat=40.605,
                                    built_area_m2=Decimal(80))], "a1")
    assert (first.offers_new, first.properties_new) == (1, 1)
    # Otra oferta con el punto algo desplazado: misma referencia, mismo inmueble.
    second = ingest_one(conn, [offer("a2", cadastral_ref=ref, lon=-3.3949, lat=40.6052)], "a2")
    assert (second.properties_new, second.properties_matched) == (0, 1)
    rows = conn.execute(
        "SELECT o.external_id, p.section_code, p.section_vintage, o.location_source "
        "FROM offers o JOIN properties p ON p.id = o.property_id "
        "WHERE o.external_id IN ('a1', 'a2') ORDER BY 1").fetchall()
    assert rows == [("a1", "2807998001", 2025, "canal"), ("a2", "2807998001", 2025, "canal")]


@pytest.mark.db
def test_deduplicacion_por_cercania_y_superficie(conn):
    base = ingest_one(conn, [offer("b1", lon=-3.3920, lat=40.6080,
                                   built_area_m2=Decimal(100))], "b1")
    assert base.properties_new == 1
    # A unos 10 metros y con 103 m²: el mismo inmueble.
    near = ingest_one(conn, [offer("b2", lon=-3.39195, lat=40.60807,
                                   built_area_m2=Decimal(103))], "b2")
    assert near.properties_matched == 1
    # Mismo punto, 130 m²: otro inmueble (otra planta, otra vivienda).
    other = ingest_one(conn, [offer("b3", lon=-3.39195, lat=40.60807,
                                    built_area_m2=Decimal(130))], "b3")
    assert other.properties_new == 1


@pytest.mark.db
def test_versiones_de_lo_recibido(conn):
    o = [offer("c1")]
    assert ingest_one(conn, o, "c1", {"precio": 100}).offers_new == 1
    assert ingest_one(conn, o, "c1", {"precio": 100}).offers_unchanged == 1
    assert ingest_one(conn, o, "c1", {"precio": 95}).offers_changed == 1
    versions = conn.execute(
        "SELECT count(*) FROM offer_raw_versions v JOIN offers o ON o.id = v.offer_id "
        "WHERE o.external_id = 'c1'").fetchone()[0]
    assert versions == 2


@pytest.mark.db
def test_ubicacion_por_direccion_o_sin_ubicar(conn):
    found = ingest_one(conn, [offer("d1", address="Calle Falsa 1, Madrid")], "d1",
                       locate=lambda o: Point(-3.3955, 40.6055, "cartociudad"))
    assert found.located == 1
    lost = ingest_one(conn, [offer("d2", address="Calle Inexistente")], "d2")
    assert (lost.offers_new, lost.located) == (1, 0)
    assert conn.execute("SELECT property_id FROM offers WHERE external_id = 'd2'"
                        ).fetchone() == (None,)


@pytest.mark.db
def test_canal_boe_seccion_v_de_punta_a_punta(database):
    from housefinder.offers.run import run_boe_v

    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requests.append(url)
        if url.endswith("/sumario/20261028"):
            return httpx.Response(200, content=(FIXTURES / "sumario-20261028-5b.json").read_bytes())
        if "xml.php?id=BOE-B-2026-35273" in url:
            return httpx.Response(200, content=ANNOUNCEMENT)
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with psycopg.connect(database, autocommit=True) as conn:  # otros tests leen el mismo día
        conn.execute("DELETE FROM watch_issues WHERE source = 'offers_boe_v'")
    report = run_boe_v(database, client, date(2026, 10, 29), days=2)
    assert report["items"] == 1
    assert report["offers_new"] + report["offers_unchanged"] == 1
    # Solo se descarga el anuncio que es una venta de inmuebles, no los otros dos del sumario.
    assert sum("xml.php" in r for r in requests) == 1
    before = len(requests)
    again = run_boe_v(database, client, date(2026, 10, 29), days=2)
    assert again["items"] == 0
    assert len(requests) - before == 1  # solo vuelve a pedir el 29, que no tenía BOE
    with psycopg.connect(database) as conn:
        row = conn.execute(
            "SELECT o.kind, o.extraction_status, o.source_id, s.license FROM offers o "
            "JOIN sources s ON s.id = o.source_id WHERE o.external_id = 'BOE-B-2026-35273'"
        ).fetchone()
    assert row[0] == "anuncio" and row[2] == "boe-seccion-v"
    assert "citar la fuente" in row[3]


def cartociudad_down() -> httpx.Client:
    """CartoCiudad devuelve un 500, como el 2026-10-30 con una parcela de Sahagún (León)."""
    return httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(500)))


@pytest.mark.db
def test_un_500_de_cartociudad_deja_la_oferta_sin_ubicar_con_su_motivo(conn):
    from housefinder.geo.cartociudad import geocode
    from housefinder.offers.locate import offer_locator

    client = cartociudad_down()
    misses: list[tuple[str, str]] = []
    locate = offer_locator(conn, lambda address: geocode(client, address),
                           on_miss=lambda o, reason: misses.append((o.external_id, reason)))
    assert locate(offer("e1", address="Calle Mayor 1, Madrid", municipality="Madrid")) is None
    assert misses == [("e1", "CartoCiudad no responde: HTTP 500")]


def test_fuera_de_la_zona_no_se_pregunta_al_catastro_ni_a_cartociudad():
    from housefinder.offers.locate import Zone, offer_locator

    asked: list[str] = []

    def service(query):
        asked.append(query)
        raise AssertionError("no se tenía que preguntar")

    misses: list[tuple[str, str]] = []
    locate = offer_locator(None, service, service, lambda o, r: misses.append((o.external_id, r)),
                           zone=Zone.of(["Madrid"]))
    address = "parcela 14, polígono 501. Municipio: Sahagún (León), Sahagún (León), León"
    assert locate(offer("f1", address=address, municipality="Sahagún (León)",
                        province="León", cadastral_ref="24137A501000140000XX")) is None
    # Sin provincia, la del paréntesis del municipio.
    assert locate(offer("f2", address=address, municipality="Sahagún (León)")) is None
    assert asked == []
    assert misses == [("f1", "fuera de la zona cubierta: provincia «León»"),
                      ("f2", "fuera de la zona cubierta: provincia «León»")]


@pytest.mark.parametrize("province, municipality, outside", [
    ("Madrid", "Alcalá de Henares", None),
    ("provincia de Madrid", None, None),
    ("Comunidad de Madrid", "Alcalá de Henares (Madrid)", None),
    (None, "Alcalá de Henares (MADRID)", None),
    (None, None, None),  # no lo dice: se intenta y decide la cartografía
    ("León", "Sahagún", "León"),
    ("Toledo", "Seseña (Toledo)", "Toledo"),
])
def test_provincia_de_la_oferta_frente_a_la_zona(province, municipality, outside):
    from housefinder.offers.locate import Zone

    zone = Zone.of(["Madrid"])
    assert zone.outside(offer("g", province=province, municipality=municipality)) == outside


def test_la_zona_por_defecto_es_la_de_las_secciones_cargadas():
    from housefinder.offers.locate import load_zone

    assert load_zone().outside(offer("h", province="Madrid")) is None
    assert load_zone().outside(offer("h", province="León")) == "León"
