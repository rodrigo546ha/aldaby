"""Ofertas (G5): canal BOE sección V, versiones de lo recibido, ubicación y deduplicación.

El canal se prueba con un sumario y un anuncio reales (tests/fixtures/boe/); la deduplicación,
con un canal sintético y una sección inventada lejos de las de otros tests.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from housefinder.geo.cartociudad import AddressNotFound
from housefinder.offers.channels.boe_v import BoeSectionV, is_property_sale, parse_announcement
from housefinder.offers.ingest import Point
from housefinder.offers.model import NormalizedOffer, RawItem

FIXTURES = Path(__file__).parent / "fixtures" / "boe"
CATASTRO = Path(__file__).parent / "fixtures" / "catastro"
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



# --- Sin ubicar, con su motivo; zona según las secciones cargadas (ADR-0031) -------------------


def cartociudad_down() -> httpx.Client:
    """CartoCiudad devuelve un 500, como el 2026-10-30 con una parcela de Sahagún (León)."""
    return httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(500)))


@pytest.mark.db
def test_un_500_de_cartociudad_deja_la_oferta_sin_ubicar_con_su_motivo(conn):
    from housefinder.geo.cartociudad import geocode
    from housefinder.offers.ingest import Unlocated
    from housefinder.offers.locate import offer_locator

    client = cartociudad_down()
    locate = offer_locator(conn, lambda address: geocode(client, address))
    assert locate(offer("e1", address=f"Calle Mayor 1 {uuid4()}, Madrid", municipality="Madrid")
                  ) == Unlocated("CartoCiudad no responde: HTTP 500", retry=True)
    # Lo que no se encuentra no se reintenta.
    missing = offer_locator(conn, lambda address: (_ for _ in ()).throw(AddressNotFound("no")))
    assert missing(offer("e2", address=f"Calle Inexistente {uuid4()}")) == Unlocated(
        "CartoCiudad no encuentra la dirección", retry=False)


@pytest.mark.db
def test_el_motivo_se_guarda_en_la_oferta_y_se_borra_al_ubicarla(conn):
    from housefinder.offers.ingest import Unlocated

    ingest_one(conn, [offer("e3", address="Calle Mayor 1, Madrid")], "e3",
               locate=lambda o: Unlocated("CartoCiudad no responde: HTTP 500", retry=True))
    query = "SELECT location_issue, location_retry FROM offers WHERE external_id = 'e3'"
    assert conn.execute(query).fetchone() == ("CartoCiudad no responde: HTTP 500", True)
    ingest_one(conn, [offer("e3", address="Calle Mayor 1, Madrid")], "e3",
               locate=lambda o: Point(-3.3955, 40.6055, "cartociudad"))
    assert conn.execute(query).fetchone() == (None, False)


def test_fuera_de_la_zona_no_se_pregunta_a_ningun_servicio():
    from housefinder.offers.ingest import Unlocated
    from housefinder.offers.locate import Zone, offer_locator

    def service(*query):
        raise AssertionError("no se tenía que preguntar")

    locate = offer_locator(None, service, service, service, zone=Zone(frozenset({"28"})))
    address = "parcela 14, polígono 501. Municipio: Sahagún (León), Sahagún (León), León"
    expected = Unlocated("provincia sin secciones cargadas: «León»", retry=True)
    assert locate(offer("f1", address=address, municipality="Sahagún (León)", province="León",
                        cadastral_ref="24142A50100014")) == expected
    # Sin provincia, la del paréntesis del municipio.
    assert locate(offer("f2", address=address, municipality="Sahagún (León)")) == expected


@pytest.mark.parametrize("province, municipality, outside", [
    ("Madrid", "Alcalá de Henares", None),
    ("provincia de Madrid", None, None),
    ("Comunidad de Madrid", "Alcalá de Henares (Madrid)", None),
    (None, "Alcalá de Henares (MADRID)", None),
    (None, None, None),  # no lo dice: se intenta y decide la cartografía
    ("Vizcaya", None, None),  # no está en la relación del INE (Bizkaia): no se descarta
    ("León", "Sahagún", "León"),
    ("Toledo", "Seseña (Toledo)", "Toledo"),
    ("A Coruña", None, "A Coruña"),  # «Coruña, A» en la relación
    ("Alacant", None, "Alacant"),  # «Alicante/Alacant»
    (None, "Sahagún (León)", None),  # con León cargada
])
def test_provincia_de_la_oferta_frente_a_la_zona(province, municipality, outside):
    from housefinder.offers.locate import Zone

    loaded = {"28", "24"} if municipality == "Sahagún (León)" else {"28"}
    zone = Zone(frozenset(loaded))
    assert zone.outside(offer("g", province=province, municipality=municipality)) == outside


def test_relacion_de_provincias_del_ine():
    from housefinder.offers.locate import load_provinces

    provinces = load_provinces()
    assert len(set(provinces.codes.values())) == 52
    assert [provinces.code(n) for n in ("León", "LEON", "Illes Balears", "Balears",
                                        "Araba", "Álava", "Coruña", "Ceuta")] == [
        "24", "24", "07", "07", "01", "01", "15", "51"]


@pytest.mark.db
def test_la_zona_son_las_provincias_con_secciones_cargadas(conn):
    from housefinder.offers.locate import load_zone

    zone = load_zone(conn)
    assert "28" in zone.loaded
    assert zone.outside(offer("h", province="Madrid")) is None
    assert zone.outside(offer("h", province="Soria")) == "Soria"


@pytest.mark.parametrize("address, municipality, province, queries", [
    # Con la provincia, «nº» o una coma ante el número, CartoCiudad no la encuentra.
    ("Paseo de la Marina nº 5, Garrucha (Almería), Garrucha, Almería", "Garrucha", "Almería",
     ["Paseo de la Marina 5, Garrucha", "Marina 5, Garrucha"]),
    ("Plaza Cuartel, 6, CACÍN, Granada", "CACÍN", "Granada",
     ["Plaza Cuartel 6, CACÍN", "Cuartel 6, CACÍN"]),
    ("Callejuela del Cuartel, 2, FRECHILLA, Palencia", "FRECHILLA", "Palencia",
     ["Callejuela del Cuartel 2, FRECHILLA", "Cuartel 2, FRECHILLA"]),
    # El municipio entero: con «Donostia» solo, CartoCiudad da Milagro (Navarra).
    ("avenida de Navarra nº 20, Donostia/San Sebastián (Gipuzkoa), Donostia/San Sebastián, "
     "Gipuzkoa", "Donostia/San Sebastián", "Gipuzkoa",
     ["avenida de Navarra 20, Donostia/San Sebastián", "Navarra 20, Donostia/San Sebastián"]),
    ("Calle Mayor 3, Getafe", None, None, ["Calle Mayor 3, Getafe", "Mayor 3, Getafe"]),
])
def test_la_direccion_como_la_busca_cartociudad(address, municipality, province, queries):
    from housefinder.offers.locate import address_queries
    from housefinder.offers.model import NormalizedOffer

    offer = NormalizedOffer(external_id="x", kind="lote", url="", title="", address=address,
                            municipality=municipality, province=province)
    assert address_queries(offer) == list(dict.fromkeys([*queries, address]))


@pytest.mark.parametrize("text, found", [
    ("parcela 14, polígono 501. Municipio: Sahagún (León)", ("501", "14")),
    ("Finca rústica, Polígono nº 7, Parcela n.º 123, paraje La Vega", ("7", "123")),
    ("POLIGONO 12 PARCELA 5", ("12", "5")),
    ("parcelas 14 y 15 del polígono 501", None),  # varias parcelas: no se elige una
    ("parcela urbana en la calle Mayor 3", None),
    ("polígono industrial Las Mercedes, nave 4", None),
    # En letra (BOE-B-2026-32279).
    ("polígono ciento cuatro, parcela siete, Campillo de Llerena", ("104", "7")),
    ("parcela ciento cincuenta y dos del polígono veintitrés", ("23", "152")),
    ("polígono dos mil trescientos uno, parcela cuarenta", ("2301", "40")),
])
def test_poligono_y_parcela_de_una_finca_rustica(text, found):
    from housefinder.offers.locate import polygon_and_parcel

    assert polygon_and_parcel(text) == found


@pytest.mark.db
def test_finca_rustica_por_poligono_y_parcela_del_catastro(conn, database):
    from conftest import add_section

    from housefinder.geo.catastro import parse_cpmrc
    from housefinder.offers.locate import offer_locator

    cpmrc = json.loads((CATASTRO / "cpmrc-24142A50100014.json").read_text())
    add_section(database, "2413901001", -5.0542, 42.3053)
    asked: list[tuple[str, ...]] = []

    def rustic(*query):
        asked.append(query)
        return "24142A50100014"

    def geocoder(address):
        raise AssertionError("una finca rústica no se manda a CartoCiudad")

    conn.execute("DELETE FROM geocode_cache WHERE query = 'rc:24142A50100014'")
    locate = offer_locator(conn, geocoder, lambda ref: parse_cpmrc(cpmrc), rustic)
    point = locate(offer("i1", municipality="Sahagún (León)", province="León", address=(
        'parcela 14, polígono 501. Municipio: Sahagún (León), secano, paraje: "Camino de '
        'Galleguillos", Sahagún (León), León')))
    assert (point.lon, point.lat, point.source) == (-5.0541759331776, 42.3052703074663,
                                                    "catastro")
    assert asked == [("León", "Sahagún", "501", "14")]


@pytest.mark.db
def test_el_municipio_con_otro_nombre_se_reconoce_por_su_codigo_ine(conn, database):
    """BOE-B-2026-35111: la oferta dice «Castellón de la Plana» y el Catastro, «CASTELLO DE LA
    PLANA». El municipio de la sección del punto (12040) es el que CartoCiudad da para el nombre
    de la oferta."""
    from conftest import add_section

    from housefinder.geo.catastro import Parcel
    from housefinder.offers.ingest import Unlocated
    from housefinder.offers.locate import offer_locator

    add_section(database, "1204001001", -0.0450, 39.9800)
    castello = Parcel(-0.0450, 39.9800, "1991501YK5219S",
                      "CL RIO EBRO 33 CASTELLO DE LA PLANA (CASTELLÓN)")
    asked: list[str] = []

    def municipalities(name):
        asked.append(name)
        return frozenset({"12040"}) if name == "Castellón de la Plana" else frozenset()

    def geocoder(address):
        raise AssertionError("ya la ubica el Catastro")

    conn.execute("DELETE FROM geocode_cache WHERE query = 'rc:1991501YK5219S'")
    locate = offer_locator(conn, geocoder, lambda ref: castello, municipalities=municipalities)
    point = locate(offer("j1", cadastral_ref="1991501YK5219S0001GF",
                         municipality="Castellón de la Plana"))
    assert point == Point(-0.0450, 39.9800, "catastro")
    # Otro municipio de verdad (Utiel frente a Requena) sigue sin aceptarse.
    assert locate(offer("j2", cadastral_ref="1991501YK5219S0001GF", municipality="Utiel")
                  ) == Unlocated("la parcela 1991501YK5219S0001GF es de otro municipio: "
                                 "CL RIO EBRO 33 CASTELLO DE LA PLANA (CASTELLÓN)", retry=False)
    assert asked == ["Castellón de la Plana", "Utiel"]
    # Si CartoCiudad no responde al comprobarlo, se reintentará.
    down = offer_locator(conn, geocoder, lambda ref: castello,
                         municipalities=lambda name: (_ for _ in ()).throw(
                             httpx.ConnectError("sin red")))
    missed = down(offer("j3", cadastral_ref="1991501YK5219S0001GF",
                        municipality="Castellón de la Plana"))
    assert missed.retry is True
