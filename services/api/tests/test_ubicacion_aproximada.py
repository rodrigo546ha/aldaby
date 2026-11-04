"""Direcciones del Portal de Subastas y ubicación aproximada en el municipio (ADR-0054)."""

import pytest

from housefinder.geo.cartociudad import AddressNotFound
from housefinder.offers.locate import (
    address_queries,
    clean_street,
    parcel_in_municipality,
    same_municipality,
)
from housefinder.offers.model import NormalizedOffer


@pytest.mark.parametrize("address, town, street", [
    ("Calle Alcala, 204 - Piso: 8ª - Puerta: A - CP: 28000", "Madrid", "Calle Alcala 204"),
    ("PISO 2º 1 DE LA CALLE DIAMANTE Nº 65 DE MADRID", "Madrid", "CALLE DIAMANTE 65"),
    ("CALLE MONTEJURRA Nº 33 BLOQUE 1 BAJO A", "Madrid", "CALLE MONTEJURRA 33"),
    ("CALLE CRUZ ANTIGUA Nº 17 ESCALERA 1 ATICO B", "Ciempozuelos", "CALLE CRUZ ANTIGUA 17"),
    ("CALLE GRAN CAPITAN Nº4, 4ºA", "Alcala de Henares", "CALLE GRAN CAPITAN 4"),
    ("calle Avutarda num. 2, bloque 3 , 1ºD", "Sevilla la Nueva", "calle Avutarda 2"),
    ("CASA EN NTRA SRA DEL ROSARIO Nº 6 . FINCA 3052 REGISTRO Nº 15", "Madrid",
     "Nuestra Señora DEL ROSARIO 6"),
    # Sin piso ni puerta no hay nada que limpiar: valen las formas de siempre
    ("Plaza Cuartel, 6, CACÍN, Granada", "CACÍN", None),
    ("Calle Mayor 3, Getafe", None, None),
])
def test_calle_y_numero_sin_piso_ni_puerta(address, town, street):
    assert clean_street(address, town) == street


def test_la_direccion_limpia_va_primero():
    offer = NormalizedOffer(external_id="x", kind="lote", url="", title="",
                            address="Calle Alcala, 204 - Piso: 8ª - Puerta: A - CP: 28000",
                            municipality="Madrid")
    queries = address_queries(offer)
    assert queries[:2] == ["Calle Alcala 204, Madrid", "Alcala 204, Madrid"]
    assert queries[-1] == offer.address


@pytest.mark.parametrize("expected, address, same", [
    ("Las Rozas", "CL ISLAS PITIUSAS 2 URB LOS ALAMOS LAS ROZAS DE MADRID (MADRID)", True),
    ("Galapagar Parquelagos", "CL LOMBARDIA 17 GALAPAGAR (MADRID)", True),
    # Con «de» o artículo, cada palabra no vale por sí sola
    ("Sevilla la Nueva", "CL MAYOR 1 SEVILLA (SEVILLA)", False),
])
def test_municipio_del_portal_frente_al_catastro(expected, address, same):
    assert parcel_in_municipality(expected, address) is same


def test_localidad_con_su_nucleo():
    assert same_municipality("Galapagar Parquelagos", "CALLE LOMBARDIA 17, 28420 Parquelagos")


# --- Con base de datos ----------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")
from test_offers import conn, database  # noqa: E402, F401


@pytest.mark.db
def test_punto_aproximado_en_el_municipio(conn, database):  # noqa: F811
    from conftest import add_section

    from housefinder.db.sections import municipality_point
    from housefinder.offers.ingest import Unlocated
    from housefinder.offers.locate import offer_locator

    # Un municipio propio de esta prueba (Zamora), con una sola sección centrada en el punto
    add_section(database, "4999901001", -5.75, 41.5)
    point = municipality_point(conn, "49999", 2025)
    assert point is not None and point == pytest.approx((-5.75, 41.5), abs=1e-6)
    assert municipality_point(conn, "49998", 2025) is None

    def nowhere(address):
        raise AddressNotFound(address)

    locate = offer_locator(conn, nowhere, municipalities=lambda name: frozenset({"49999"}))
    found = locate(NormalizedOffer(external_id="x", kind="lote", url="", title="",
                                   address="Calle Inventada 1", municipality="Villaprueba",
                                   province="Zamora"))
    assert isinstance(found, Unlocated)
    assert found.approx is not None and found.approx.source == "municipio"
    assert (found.approx.lon, found.approx.lat) == pytest.approx((-5.75, 41.5))
    # Si el nombre da varios municipios de la provincia, no se adivina
    ambiguous = offer_locator(conn, nowhere,
                              municipalities=lambda name: frozenset({"49999", "49001"}))
    missed = ambiguous(NormalizedOffer(external_id="y", kind="lote", url="", title="",
                                       address="Calle Inventada 1", municipality="Villaprueba",
                                       province="Zamora"))
    assert isinstance(missed, Unlocated) and missed.approx is None


@pytest.mark.db
def test_el_punto_aproximado_se_guarda_y_se_borra_al_ubicar(conn):  # noqa: F811
    from housefinder.db.offers import catalog_rows, create_property, link_offer, mark_unlocated
    from housefinder.db.profiles import create_organization
    from housefinder.offers.catalog import catalog_item
    from housefinder.offers.locate import load_provinces
    from housefinder.offers.pasted import submit_text

    org = create_organization(conn, "Aproximada", "particular")
    offer_id = submit_text(conn, org, "Piso en venta en algún sitio de Madrid por 100000").offer_id
    mark_unlocated(conn, offer_id, "CartoCiudad no encuentra la dirección", False,
                   (-3.395, 40.605))
    row = catalog_rows(conn, org, offer_id)[0]
    item = catalog_item(row, load_provinces())
    assert item.approximate and not item.exact
    assert (item.lon, item.lat) == pytest.approx((-3.395, 40.605))
    prop = create_property(conn, lon=-3.396, lat=40.604, cadastral_ref=None, address="x",
                           built_area_m2=None, municipality="28079", section=None)
    link_offer(conn, offer_id, prop, "cartociudad")
    item = catalog_item(catalog_rows(conn, org, offer_id)[0], load_provinces())
    assert not item.approximate and item.exact
    assert (item.lon, item.lat) == pytest.approx((-3.396, 40.604))
