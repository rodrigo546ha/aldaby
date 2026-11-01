"""Supuestos del plan desde fuentes públicas (ADR-0022), contra la base temporal."""

from datetime import date
from decimal import Decimal

import pytest

from housefinder.db.references import ReferenceRow, SeriesPoint, replace_references
from housefinder.db.sections import SourceRecord
from housefinder.valuation.assumptions import (
    MissingData,
    largest_rise,
    market_assumptions,
    property_assumptions,
)

D = Decimal


def point(year: int, month: int, value: str) -> SeriesPoint:
    return SeriesPoint(year, month, D(value), "bde-be1904")


def test_la_mayor_subida_en_la_ventana():
    series = [point(2010, 1, "0.040"), point(2010, 2, "0.030"), point(2011, 1, "0.045"),
              point(2012, 6, "0.050"), point(2014, 1, "0.090")]
    rise, start, end = largest_rise(series, 24)
    # La ventana es de meses de calendario, aunque la serie tenga huecos: 2011 → 2014 (36 meses)
    # no cuenta; la mayor dentro de 24 meses es jun 2012 → ene 2014 (19 meses), +0,040
    assert rise == D("0.040") and (start.year, end.year) == (2012, 2014)
    assert largest_rise([point(2020, 1, "0.03")], 24)[0] == 0  # sin subidas


psycopg = pytest.importorskip("psycopg")


def source(id_: str) -> SourceRecord:
    from datetime import UTC, datetime

    return SourceRecord(id=id_, name=id_, url="https://example", license="prueba",
                        fetched_at=datetime.now(UTC), notes="")


def row(level, code, year, measure, value, unit="EUR", month=0, typology="todas", stat="valor"):
    return ReferenceRow(level=level, code=code, vintage=None, year=year, quarter=0,
                        measure=measure, typology=typology, stat=stat, value=D(value), unit=unit,
                        month=month)


@pytest.fixture
def references(migrated_database: str) -> str:
    with psycopg.connect(migrated_database) as conn:
        replace_references(conn, source("bde-be1904"), [
            row("pais", "ES", 2026, "tedr_vivienda_nuevas", v, "ratio", m, band)
            for m, v, band in [(6, "0.0270", "mas_10"), (7, "0.0281", "mas_10"),
                               (8, "0.027556", "mas_10"), (7, "0.03158", "hasta_1"),
                               (8, "0.032325", "hasta_1")]])
        replace_references(conn, source("catastro-urbana-2026"), [
            row("municipio", "28993", 2026, "inmuebles_residenciales", "1000", "inmuebles",
                stat="n"),
            row("municipio", "28993", 2026, "valor_catastral_residencial", "90000000"),
            row("municipio", "28993", 2026, "valor_catastral", "200000000"),
            row("municipio", "28993", 2026, "valor_construccion", "80000000")])
        replace_references(conn, source("ine-epf-73993"), [
            row("comunidad", "13", 2024, "gasto_comunidad_hogar", "900", "EUR/año", stat="media"),
            row("comunidad", "13", 2025, "gasto_comunidad_hogar", "1045.76", "EUR/año",
                stat="media"),
            row("comunidad", "13", 2025, "gasto_seguro_vivienda_hogar", "270.54", "EUR/año",
                stat="media"),
            row("comunidad", "13", 2025, "gasto_mantenimiento_vivienda_hogar", "109.27",
                "EUR/año", stat="media")])
        conn.commit()
    return migrated_database


@pytest.mark.db
def test_supuestos_de_una_oferta_con_su_fuente(references):
    with psycopg.connect(references) as conn:
        market = market_assumptions(conn)
        prop = property_assumptions(conn, "28993", "13", D("200000"), None)
        listed = property_assumptions(conn, "28993", "13", D("200000"), D("65"))
    assert market.mortgage_rate.value == D("0.0276")  # el último mes, a cuatro decimales
    assert market.mortgage_rate.as_of == date(2026, 8, 1)
    assert market.mortgage_rate.sources[0].id == "bde-be1904@2026-08"
    assert market.rate_shock.value == D("0.0011")  # 0,0270 → 0,0281
    assert prop.cadastral_value.value == D("90000.00")  # 90.000.000 / 1.000
    assert prop.construction_value.value == D("80000.00")  # 200.000 × (80 / 200)
    assert prop.cadastral_land_value.value == D("54000.00")  # 90.000 × (1 − 0,4)
    assert prop.community_fees_monthly.value == D("87.15")  # 1.045,76 / 12, el último año
    assert "se queda corta" in prop.community_fees_monthly.formula
    assert prop.insurance_annual.value == D("270.54")
    assert prop.maintenance_annual.value == D("109.27")
    assert listed.community_fees_monthly.value == D("65.00")  # la del anuncio gana
    assert listed.community_fees_monthly.sources[0].id == "anuncio-confirmado"


@pytest.mark.db
def test_sin_datos_dice_que_falta_y_como_cargarlo(migrated_database):
    with psycopg.connect(migrated_database) as conn, pytest.raises(MissingData,
                                                                   match="make supuestos"):
        property_assumptions(conn, "28000", "13", D("1"), None)


@pytest.mark.db
def test_hipoteca_variable_estimada(references):
    from housefinder.params.book import ParamBook, default_params_dir
    from housefinder.valuation.assumptions import variable_mortgage

    book = ParamBook.from_dir(default_params_dir())
    with psycopg.connect(references) as conn:
        variable = variable_mortgage(conn, book, date(2026, 10, 31))
    assert variable.initial_rate.value == D("0.0323")  # agosto, el último mes
    # Julio, el mes del Euríbor oficial del ancla (2,855 %): 0,03158 − 0,02855
    assert variable.spread.value == D("0.0030")
    assert variable.terms.initial_months == 12 and variable.terms.label == "variable"
    assert any(s.provisional for s in variable.spread.sources)
