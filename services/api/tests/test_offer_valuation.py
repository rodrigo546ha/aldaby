"""Valoración de una oferta confirmada (F5.4) contra la base temporal, por la API. Municipio
ficticio 28993 con las mismas referencias que test_valuation_service (k = 10 de prueba, IPC de
alquiler 100 → 110, IPV de 2024 = 100 de media y 110 en 2026T2), piso de 80 m²:

- renta 1.144 / 1.452 / 1.782,40 €/mes; precio 343.200 / 435.600 / 534.600 €.
- Venta por 400.000 €: 400.000 / 435.600 − 1 = −0,081726… → −0,0817; frente al P75,
  400.000 / 534.600 − 1 = −0,251777… → −0,2518; frente al P25, 400.000 / 343.200 − 1 =
  0,165501… → 0,1655. Rentabilidad bruta: 1.452 × 12 / 400.000 = 0,04356 → 0,0436; con el P25,
  13.728 / 400.000 = 0,03432 → 0,0343; con el P75, 21.388,8 / 400.000 = 0,053472 → 0,0535.
- Alquiler por 1.200 €/mes: 1.200 / 1.452 − 1 = −0,173553… → −0,1736; frente al P75,
  1.200 / 1.782,40 − 1 = −0,326750… → −0,3268; frente al P25, 1.200 / 1.144 − 1 = 0,048951… →
  0,0490.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from conftest import add_section

from housefinder.db.references import ReferenceRow, replace_references
from housefinder.db.sections import SourceRecord
from housefinder.params.book import Param, ParamBook

pytestmark = pytest.mark.db
psycopg = pytest.importorskip("psycopg")
D = Decimal
SECTION, MUNICIPALITY = "2899301001", "28993"
LON, LAT = -3.60, 40.10
BOOK = ParamBook([Param(
    id="contraccion-prueba", kind="contraccion_renta", territory="ES",
    effective_from=date(2026, 1, 1), effective_to=None, params={"k": 10},
    source="prueba", provisional=True)])


def rent_rows(level, code, n, p25, median, p75):
    rows = [ReferenceRow(level, code, 2021, 2024, 0, "renta_m2_mes", "colectiva", stat, D(v),
                         "EUR/m2 mes")
            for stat, v in (("p25", p25), ("mediana", median), ("p75", p75))]
    rows.append(ReferenceRow(level, code, 2021, 2024, 0, "alquileres", "colectiva", "n", D(n),
                             "viviendas"))
    return rows


def source(source_id):
    return SourceRecord(source_id, "prueba", "https://x", "prueba", datetime.now(UTC))


@pytest.fixture(scope="module")
def database(migrated_database: str) -> str:
    add_section(migrated_database, SECTION, LON, LAT, vintage=2021)
    with psycopg.connect(migrated_database) as conn:
        replace_references(conn, source("serpavi"),
                           rent_rows("seccion", SECTION, 30, "14", "18", "22")
                           + rent_rows("municipio", MUNICIPALITY, 5000, "10", "12", "15"))
        replace_references(conn, source("valor-tasado-comunidad-madrid"), [
            ReferenceRow("municipio", MUNICIPALITY, None, 2024, 0, "valor_tasado_m2", "todas",
                         "valor", D("3600"), "EUR/m2")])
        replace_references(conn, source("ine-ipc-alquiler"), [
            ReferenceRow("comunidad", "13", None, year, 0, "ipc_alquiler", "todas", "indice",
                         D(value), "índice base 2025", month=month)
            for year, month, value in [(2024, m, "100") for m in range(1, 13)]
            + [(2026, 9, "110")]])
        replace_references(conn, source("ine-ipv-80270"), [
            ReferenceRow("comunidad", "13", None, year, quarter, "ipv", "segunda_mano",
                         "indice", D(value), "índice base 2025")
            for year, quarter, value in [(2024, 1, "98"), (2024, 2, "99"), (2024, 3, "101"),
                                         (2024, 4, "102"), (2026, 2, "110")]])
        conn.commit()
    return migrated_database


@pytest.fixture
def api(database):
    from fastapi.testclient import TestClient

    from housefinder.api.deps import get_db, get_org, get_param_book
    from housefinder.api.main import app
    from housefinder.db.profiles import create_organization

    with psycopg.connect(database) as conn:
        org = create_organization(conn, f"Valoración {uuid4()}", "particular")
        conn.commit()

    def db():
        with psycopg.connect(database) as connection:
            yield connection

    app.dependency_overrides[get_db] = db
    app.dependency_overrides[get_org] = lambda: org
    app.dependency_overrides[get_param_book] = lambda: BOOK
    try:
        yield TestClient(app), org
    finally:
        app.dependency_overrides.clear()


def confirmed_offer(database, org, operation, price, property_type="vivienda", located=True):
    """Oferta pegada y confirmada a mano, ubicada en la sección de prueba."""
    from housefinder.db.offers import confirm_offer, create_property, link_offer
    from housefinder.offers.pasted import submit_text

    with psycopg.connect(database) as conn:
        offer_id = submit_text(conn, org, f"Piso en {operation} por {price} ({uuid4()})").offer_id
        confirm_offer(conn, offer_id, org,
                      asking_price=D(price) if operation == "venta" else None,
                      built_area_m2=D("80"), address="calle de Prueba, 1", cadastral_ref=None,
                      extracted={
                          "listing": {"property_type": property_type},
                          "confirmed": {"operation": operation, "fields": {
                              "price": {"value": price, "origin": "extraido"},
                              "built_area_m2": {"value": "80", "origin": "extraido"}}}})
        if located:
            prop = create_property(conn, lon=LON, lat=LAT, cadastral_ref=None,
                                   address="calle de Prueba, 1", built_area_m2=D("80"),
                                   municipality=MUNICIPALITY, section=(SECTION, 2021))
            link_offer(conn, offer_id, prop, "cartociudad")
        conn.commit()
    return offer_id


def test_piso_en_venta_frente_al_precio_estimado(api, database):
    http, org = api
    offer_id = confirmed_offer(database, org, "venta", "400000")
    response = http.get(f"/offers/{offer_id}/valuation")
    assert response.status_code == 200
    body = response.json()
    assert body["section_code"] == SECTION and body["rent_level"] == "seccion"
    figures = body["figures"]
    total = figures["valuation.price_total"]
    assert (total["low"], total["value"], total["high"]) == ("343200.00", "435600.00",
                                                             "534600.00")
    gap = figures["offer.asking_gap"]
    assert (gap["low"], gap["value"], gap["high"]) == ("-0.2518", "-0.0817", "0.1655")
    assert gap["formula"].startswith("Precio pedido 400.000 € / precio estimado 435.600 €")
    assert {"kind": "user_input", "id": "anuncio-confirmado", "provisional": False} in \
        gap["sources"]
    assert figures["offer.asking_price"]["value"] == "400000"
    gross = figures["offer.gross_yield_at_asking"]
    assert (gross["low"], gross["value"], gross["high"]) == ("0.0343", "0.0436", "0.0535")
    notes = body["notes"]
    assert any("dentro del rango estimado (343.200 € – 534.600 €)" in n for n in notes)
    assert any("no es un margen de negociación" in n for n in notes)
    assert any("Sin escenarios de revalorización" in n for n in notes)  # IPV sin ventanas


def test_piso_en_alquiler_frente_a_la_renta_estimada(api, database):
    http, org = api
    offer_id = confirmed_offer(database, org, "alquiler", "1200")
    body = http.get(f"/offers/{offer_id}/valuation").json()
    gap = body["figures"]["offer.asking_rent_gap"]
    assert (gap["low"], gap["value"], gap["high"]) == ("-0.3268", "-0.1736", "0.0490")
    assert "offer.asking_gap" not in body["figures"]
    assert any("renta pedida está dentro del rango" in n for n in body["notes"])


def test_ofertas_que_no_se_pueden_valorar(api, database):
    from housefinder.offers.pasted import submit_text

    http, org = api
    with psycopg.connect(database) as conn:
        pending = submit_text(conn, org, f"Piso en venta por 200.000 € ({uuid4()})").offer_id
    assert http.get(f"/offers/{pending}/valuation").json()["detail"] == (
        "Confirma primero los datos del anuncio")
    garage = confirmed_offer(database, org, "venta", "20000", property_type="garaje")
    response = http.get(f"/offers/{garage}/valuation")
    assert response.status_code == 422 and "garaje" in response.json()["detail"]
    unlocated = confirmed_offer(database, org, "venta", "200000", located=False)
    assert "no está ubicada" in http.get(f"/offers/{unlocated}/valuation").json()["detail"]
    assert http.get(f"/offers/{uuid4()}/valuation").status_code == 404
