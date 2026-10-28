from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from housefinder.core.figures import SourceRef
from housefinder.params.book import ParamBook, default_params_dir
from housefinder.params.euribor import (
    CONVERSION,
    FLAT_AFTER_HORIZON,
    anchor_month,
    euribor_12m_path,
)

# Misma forma que los datos reales; valores del ejemplo del ADR-0006 (ronda S26).
YAML = """
- id: euribor-3m-bce-s26
  kind: trayectoria_euribor_3m
  territory: ES
  effective_from: 2026-09-10
  provisional: false
  params:
    round: S26
    cut_off: 2026-08-19
    series: MPD.Q.U2.STN.I.S26.0000
    unit: percent
    quarters: {2026-Q2: 2.2, 2026-Q3: 2.5, 2026-Q4: 2.7, 2027-Q1: 2.9, 2027-Q2: 3,
               2027-Q3: 3, 2027-Q4: 3}
  source: "Prueba"
- id: euribor-12m-boe-2026-07
  kind: euribor_12m_oficial
  territory: ES
  effective_from: 2026-08-04
  provisional: false
  params: {month: 2026-07, unit: percent, value: 2.855}
  source: "Prueba"
"""


@pytest.fixture
def book(tmp_path: Path) -> ParamBook:
    (tmp_path / "euribor.yaml").write_text(YAML, encoding="utf-8")
    return ParamBook.from_dir(tmp_path)


def test_ancla_es_el_mes_anterior_al_corte():
    assert anchor_month(date(2026, 8, 19)) == (2026, 7)
    assert anchor_month(date(2027, 1, 5)) == (2026, 12)


def test_trayectoria_a_un_ano_valor_conocido(book: ParamBook):
    # Calculado a mano (ADR-0006), en porcentaje:
    #   media 3M de 2026T3–2027T2 = (2,5 + 2,7 + 2,9 + 3) / 4 = 2,775
    #   prima = 2,855 (Euríbor a un año de julio, BOE) − 2,775 = 0,080
    #   2026T3: 2,775 + 0,08 = 2,855 · 2026T4: (2,7+2,9+3+3)/4 + 0,08 = 2,980
    #   2027T1: (2,9+3+3+3)/4 + 0,08 = 3,055 · 2027T2 en adelante: 3 + 0,08 = 3,080
    path = euribor_12m_path(book, date(2026, 10, 28))
    assert path.round == "S26"
    assert path.premium == Decimal("0.0008")
    values = dict(path.quarters)
    assert values[date(2026, 7, 1)] == Decimal("0.02855")
    assert values[date(2026, 10, 1)] == Decimal("0.0298")
    assert values[date(2027, 1, 1)] == Decimal("0.03055")
    assert values[date(2027, 4, 1)] == Decimal("0.0308")
    assert values[date(2027, 10, 1)] == Decimal("0.0308")
    # Empieza en el trimestre del ancla: 2026T2 no forma parte de la trayectoria.
    assert date(2026, 4, 1) not in values


def test_rate_path_en_meses_desde_la_firma(book: ParamBook):
    path = euribor_12m_path(book, date(2026, 10, 28)).rate_path(date(2026, 10, 15))
    # Firma en octubre (mes 0, trimestre 2026T4); enero es el mes 3, abril el 6…
    assert path.value_at(0) == Decimal("0.0298")
    assert path.value_at(2) == Decimal("0.0298")
    assert path.value_at(3) == Decimal("0.03055")
    assert path.value_at(6) == Decimal("0.0308")
    assert path.value_at(400) == Decimal("0.0308")


def test_firma_anterior_a_la_trayectoria_usa_el_primer_valor(book: ParamBook):
    path = euribor_12m_path(book, date(2026, 10, 28)).rate_path(date(2026, 5, 20))
    assert path.value_at(0) == Decimal("0.02855")
    assert path.value_at(2) == Decimal("0.02855")  # julio, mes 2
    assert path.value_at(5) == Decimal("0.0298")  # octubre, mes 5


def test_cita_ronda_ancla_y_supuestos(book: ParamBook):
    path = euribor_12m_path(book, date(2026, 10, 28))
    assert set(path.sources) == {
        SourceRef("param", "euribor-3m-bce-s26"),
        SourceRef("param", "euribor-12m-boe-2026-07"),
        CONVERSION,
        FLAT_AFTER_HORIZON,
    }
    assert path.rate_path(date(2026, 10, 15)).sources == path.sources
    assert not any(ref.provisional for ref in path.sources)


def test_sin_ancla_es_un_error(tmp_path: Path):
    sin_ancla = YAML.split("- id: euribor-12m-boe-2026-07")[0]
    (tmp_path / "euribor.yaml").write_text(sin_ancla, encoding="utf-8")
    with pytest.raises(LookupError, match="2026-07"):
        euribor_12m_path(ParamBook.from_dir(tmp_path), date(2026, 10, 28))


def test_sin_ronda_vigente_es_un_error(book: ParamBook):
    with pytest.raises(LookupError):
        euribor_12m_path(book, date(2026, 9, 1))  # antes de publicarse S26


def test_unidad_desconocida_es_un_error(tmp_path: Path):
    (tmp_path / "euribor.yaml").write_text(
        YAML.replace("unit: percent\n    quarters", "unit: bp\n    quarters"), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="unit"):
        euribor_12m_path(ParamBook.from_dir(tmp_path), date(2026, 10, 28))


def test_trimestres_no_consecutivos_son_un_error(tmp_path: Path):
    (tmp_path / "euribor.yaml").write_text(
        YAML.replace("2026-Q4: 2.7, ", ""), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="consecutivos"):
        euribor_12m_path(ParamBook.from_dir(tmp_path), date(2026, 10, 28))


def test_los_datos_del_repositorio_dan_el_ejemplo_del_adr():
    path = euribor_12m_path(ParamBook.from_dir(default_params_dir()), date(2026, 10, 28))
    assert path.round == "S26"
    assert path.cut_off == date(2026, 8, 19)
    values = dict(path.quarters)
    assert values[date(2026, 7, 1)] == Decimal("0.02855")
    assert values[date(2028, 10, 1)] == Decimal("0.0308")


def test_la_trayectoria_alimenta_la_comparacion_de_hipotecas():
    from housefinder.engines import mortgage as m
    from housefinder.engines.rates import MortgageTerms

    path = euribor_12m_path(ParamBook.from_dir(default_params_dir()), date(2026, 10, 28))
    variable = MortgageTerms("variable", Decimal("0.025"), 12, Decimal("0.008"), 12)
    res = m.compare_mortgages(
        principal=Decimal(150000),
        years=25,
        options=(variable,),
        expected_path=path.rate_path(date(2026, 11, 1)),
        rate_shock=Decimal("0.02"),
    )
    cost = res.options[0].expected_total_interest
    assert SourceRef("param", "euribor-3m-bce-s26") in cost.sources
    assert SourceRef("param", "euribor-12m-boe-2026-07") in cost.sources
    assert CONVERSION in cost.sources
