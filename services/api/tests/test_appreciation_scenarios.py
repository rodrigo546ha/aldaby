"""Escenarios de revalorización (F5.5, ADR-0018) contra la base temporal. Datos sintéticos:

- IPV de segunda mano de la comunidad 13 que sube un 5 % al año, trimestral 2020–2024: todas las
  ventanas de 2 años dan +5 % → los tres percentiles del ciclo son 0,05;
- renta del municipio ficticio 28996 a 12 €/m² y de la provincia a 15 (2024): brecha
  ln(12/15) = −0,2231 (municipio barato);
- parámetro de prueba: b base 0, b bajo −0,1, b alto +0,1, pasos de 1 año, horizonte 2 años.
  Optimista (converge, b = −0,1): relativo −0,2231 × (0,9² − 1) = +0,0424 → 1,05 × e^0,0212 − 1
  = 7,25 %. Base: 5,00 %. Conservador (diverge, b = +0,1): −0,2231 × (1,1² − 1) = −0,0469 →
  1,05 × e^−0,02345 − 1 = 2,57 %.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from housefinder.db.references import ReferenceRow, replace_references
from housefinder.db.sections import SourceRecord
from housefinder.params.book import Param, ParamBook
from housefinder.valuation.scenarios import NoScenarios, appreciation_scenarios, rent_growth

pytestmark = pytest.mark.db
psycopg = pytest.importorskip("psycopg")
D = Decimal
BOOK = ParamBook([Param(
    id="convergencia-prueba", kind="convergencia_municipal", territory="ES-13",
    effective_from=date(2026, 1, 1), effective_to=None,
    params={"step_years": 1, "b_base": 0, "b_low": -0.1, "b_high": 0.1}, source="prueba",
    provisional=False)])


def source(source_id):
    return SourceRecord(source_id, "prueba", "https://x", "prueba", datetime.now(UTC))


@pytest.fixture(scope="module")
def conn(migrated_database: str):
    with psycopg.connect(migrated_database) as connection:
        replace_references(connection, source("ine-ipv-80270"), [
            ReferenceRow("comunidad", "13", None, year, quarter, "ipv", "segunda_mano", "indice",
                         D(100) * D("1.05") ** (year - 2020 + D(quarter - 1) / 4),
                         "índice base 2025")
            for year in range(2020, 2025) for quarter in range(1, 5)])
        territories = (("municipio", "28996", "12"), ("provincia", "28", "15"))
        replace_references(connection, source("serpavi"), [
            ReferenceRow(level, code, 2021, 2024, 0, "renta_m2_mes", "colectiva", stat,
                         D(value), "EUR/m2 mes")
            for level, code, value in territories for stat in ("p25", "mediana", "p75")])
        # IPC de alquiler que sube exactamente un 3 % al año, de 2020-01 a 2024-12
        replace_references(connection, source("ine-ipc-alquiler"), [
            ReferenceRow("comunidad", "13", None, year, 0, "ipc_alquiler", "todas", "indice",
                         D(100) * D("1.03") ** (year - 2020 + D(month - 1) / 12),
                         "índice base 2025", month=month)
            for year in range(2020, 2025) for month in range(1, 13)], scope="13")
        connection.commit()
        yield connection


def test_tres_escenarios_de_un_municipio_barato(conn):
    report = appreciation_scenarios(conn, BOOK, "28996", horizon_years=2,
                                    on=date(2026, 10, 31))
    rates = {name: s.rate for name, s in report.scenarios.items()}
    assert rates == {"conservative": D("0.0257"), "base": D("0.0500"),
                     "optimistic": D("0.0725")}
    figure = {f.key: f for f in report.figures}["valuation.appreciation_base"]
    assert figure.unit == "ratio" and figure.as_of == date(2024, 12, 31)
    assert {s.kind for s in figure.sources} >= {"dataset", "param", "model", "assumption"}
    assert "5,00 %" in figure.formula
    assert any("20 % por debajo" in n for n in report.notes)
    assert any("12 ventanas de 2 años" in n for n in report.notes)


def test_sin_historia_suficiente_se_acortan_las_ventanas(conn):
    report = appreciation_scenarios(conn, BOOK, "28996", horizon_years=10,
                                    on=date(2026, 10, 31))
    # 2020–2024 da 8 ventanas de 3 años (inicios 2020 y 2021, cuatro trimestres): el mínimo
    assert any("se usan de 3" in n for n in report.notes)


def test_municipio_sin_renta_y_provincia_sin_indice(conn):
    report = appreciation_scenarios(conn, BOOK, "28995", horizon_years=2,
                                    on=date(2026, 10, 31))
    assert {s.rate for s in report.scenarios.values()} == {D("0.0500")}
    assert any("Sin renta del municipio" in n for n in report.notes)
    with pytest.raises(NoScenarios):
        appreciation_scenarios(conn, BOOK, "08019", horizon_years=2)


def test_subida_de_la_renta_con_el_ipc_de_alquiler(conn):
    # ADR-0060: con 5 años de serie no hay 8 ventanas de 10 años; de 4 años hay 12 (inicios
    # 2020-01 a 2020-12) y todas crecen un 3 % al año, así que la mediana es 0,0300
    figure = rent_growth(conn, "28996", horizon_years=10)
    assert figure.key == "assumption.rent_growth" and figure.unit == "ratio"
    assert figure.value == D("0.0300")
    assert figure.as_of == date(2024, 12, 31)
    assert "12 ventanas de 4 años" in figure.formula
    assert {s.kind for s in figure.sources} == {"dataset", "assumption"}
    with pytest.raises(NoScenarios):
        rent_growth(conn, "08019")  # Cataluña: sin IPC de alquiler cargado aquí
