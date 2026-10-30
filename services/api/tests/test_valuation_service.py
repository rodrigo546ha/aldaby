"""Servicio de valoración (F5.3, F5.4, ADR-0018) contra la base temporal, con un municipio ficticio
(28997) y valores calculados a mano:

- sección: 30 alquileres, P25 14, mediana 18, P75 22 €/m² mes (2024);
- municipio: P25 10, mediana 12, P75 15; k = 10 (parámetro PROVISIONAL) → peso 30/40 = 0,75 →
  13 / 16,5 / 20,25 €/m²; para 80 m², 1.040 / 1.320 / 1.620 €/mes;
- valor tasado 2024 del municipio 3.600 €/m² → relación 3.600 / (12 × 12) = 25 años;
- precio 2024: 3.900 / 4.950 / 6.075 €/m²; IPV de 2024 = 100 de media y 110 en 2026T2 →
  4.290 / 5.445 / 6.682,50 €/m²; × 80 m² = 343.200 / 435.600 / 534.600 €.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from conftest import add_section

from housefinder.db.references import ReferenceRow, replace_references
from housefinder.db.sections import SourceRecord
from housefinder.params.book import ParamBook, default_params_dir
from housefinder.valuation.service import OutsideCoverage, value_property

pytestmark = pytest.mark.db
psycopg = pytest.importorskip("psycopg")
D = Decimal
SECTION, DISTRICT, MUNICIPALITY = "2899701001", "2899701", "28997"
LON, LAT = -3.80, 40.30  # sección con datos
EMPTY_LON, EMPTY_LAT = -3.78, 40.30  # sección del mismo municipio sin datos


def rent_rows(level, code, n, p25, median, p75, year=2024):
    rows = [ReferenceRow(level, code, 2021, year, 0, "renta_m2_mes", "colectiva", stat, D(v),
                         "EUR/m2 mes")
            for stat, v in (("p25", p25), ("mediana", median), ("p75", p75))]
    rows.append(ReferenceRow(level, code, 2021, year, 0, "alquileres", "colectiva", "n", D(n),
                             "viviendas"))
    return rows


def source(source_id):
    return SourceRecord(source_id, "prueba", "https://x", "prueba", datetime.now(UTC))


@pytest.fixture(scope="module")
def database(migrated_database: str) -> str:
    add_section(migrated_database, SECTION, LON, LAT, vintage=2021)
    add_section(migrated_database, "2899701002", EMPTY_LON, EMPTY_LAT, vintage=2021)
    with psycopg.connect(migrated_database) as conn:
        replace_references(conn, source("serpavi"),
                           rent_rows("seccion", SECTION, 30, "14", "18", "22")
                           + rent_rows("municipio", MUNICIPALITY, 5000, "10", "12", "15"))
        replace_references(conn, source("valor-tasado-comunidad-madrid"), [
            ReferenceRow("municipio", MUNICIPALITY, None, 2024, 0, "valor_tasado_m2", "todas",
                         "valor", D("3600"), "EUR/m2")])
        replace_references(conn, source("ine-ipv-80270"), [
            ReferenceRow("comunidad", "13", None, year, quarter, "ipv", "segunda_mano",
                         "indice", D(value), "índice base 2025")
            for year, quarter, value in [(2024, 1, "98"), (2024, 2, "99"), (2024, 3, "101"),
                                         (2024, 4, "102"), (2026, 2, "110")]])
        conn.commit()
    return migrated_database


@pytest.fixture
def conn(database):
    with psycopg.connect(database) as connection:
        yield connection


BOOK = ParamBook.from_dir(default_params_dir())
ON = date(2026, 10, 30)


def figures(report):
    return {f.key: f for f in report.figures}


def test_renta_y_precio_de_un_piso_de_80_m2(conn):
    report = value_property(conn, BOOK, LON, LAT, D("80"), on=ON)
    f = figures(report)
    assert report.section_code == SECTION and report.level == "seccion"
    rent = f["valuation.rent_m2_month"]
    assert (rent.low, rent.value, rent.high) == (D("13.00"), D("16.50"), D("20.25"))
    assert rent.provisional  # k es PROVISIONAL
    monthly = f["valuation.rent_monthly"]
    assert (monthly.low, monthly.value, monthly.high) == (D("1040.00"), D("1320.00"),
                                                          D("1620.00"))
    assert f["valuation.price_rent_ratio"].value == D("25.0000")
    price = f["valuation.price_m2"]
    assert (price.low, price.value, price.high) == (D("4290.00"), D("5445.00"), D("6682.50"))
    assert price.as_of == date(2026, 6, 30)
    assert any(s.kind == "assumption" for s in price.sources)
    total = f["valuation.price_total"]
    assert (total.low, total.value, total.high) == (D("343200.00"), D("435600.00"),
                                                    D("534600.00"))
    assert any("peso del 75 %" in n for n in report.notes)


def test_sin_datos_de_la_seccion_se_usa_el_municipio(conn):
    report = value_property(conn, BOOK, EMPTY_LON, EMPTY_LAT, D("80"), on=ON)
    assert report.level == "municipio"
    rent = figures(report)["valuation.rent_m2_month"]
    assert (rent.low, rent.value, rent.high) == (D("10.00"), D("12.00"), D("15.00"))


def test_unifamiliar_sin_referencias_y_punto_fuera(conn):
    with pytest.raises(OutsideCoverage, match="unifamiliar"):
        value_property(conn, BOOK, LON, LAT, D("120"), typology="unifamiliar", on=ON)
    with pytest.raises(OutsideCoverage, match="cartografía de 2021"):
        value_property(conn, BOOK, 2.0, 41.0, D("80"), on=ON)


def test_sin_valor_tasado_no_hay_precio(conn):
    conn.execute("DELETE FROM market_references WHERE source_id = 'valor-tasado-comunidad-madrid' "
                 "AND code = %s", (MUNICIPALITY,))
    try:
        report = value_property(conn, BOOK, LON, LAT, D("80"), on=ON)
        assert "valuation.price_m2" not in figures(report)
        assert "valuation.rent_monthly" in figures(report)
        assert any("no tiene valor tasado de 2024" in n for n in report.notes)
    finally:
        conn.rollback()


def test_api_de_valoracion(database):
    from fastapi.testclient import TestClient

    from housefinder.api.deps import get_db
    from housefinder.api.main import app

    def db():
        with psycopg.connect(database) as connection:
            yield connection

    app.dependency_overrides[get_db] = db
    try:
        http = TestClient(app)
        ok = http.get("/valuation", params={"lon": LON, "lat": LAT, "area_m2": "80"})
        assert ok.status_code == 200
        body = ok.json()
        assert body["section_code"] == SECTION and body["rent_level"] == "seccion"
        price = body["figures"]["valuation.price_total"]
        assert (price["low"], price["value"], price["high"]) == ("343200.00", "435600.00",
                                                                 "534600.00")
        assert price["provisional"] is True  # k y el supuesto de rentabilidad uniforme
        assert http.get("/valuation", params={"lon": 2.0, "lat": 41.0,
                                              "area_m2": "80"}).status_code == 404
        assert http.get("/valuation", params={"lon": LON, "lat": LAT}).status_code == 422
    finally:
        app.dependency_overrides.clear()
