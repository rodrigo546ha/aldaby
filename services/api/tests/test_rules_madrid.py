"""Reglas cargadas del repositorio para un inmueble en el municipio de Madrid.

Los valores esperados son los del texto oficial consultado (fuentes en cada regla de
data/rules/). Mientras no estén verificadas, solo se resuelven con allow_unverified=True.
"""

from datetime import date
from decimal import Decimal

import pytest

from housefinder.regulation.kinds import parse_params
from housefinder.regulation.rules import RuleBook, default_rules_dir

MADRID = "ES-13-28079"


@pytest.fixture(scope="module")
def book() -> RuleBook:
    return RuleBook.from_dir(default_rules_dir())


def _resolve(book: RuleBook, kind: str, on: date, **kwargs):
    return book.resolve(kind, MADRID, on, allow_unverified=True, **kwargs)


def test_sin_verificar_no_se_aplican(book: RuleBook):
    assert book.resolve("impuesto_compra_segunda_mano", MADRID, date(2026, 10, 28)) is None


def test_itp_de_madrid(book: RuleBook):
    rule = _resolve(book, "impuesto_compra_segunda_mano", date(2026, 10, 28))
    assert rule.id == "madrid-itp-inmuebles-2014"
    assert parse_params(rule.kind, rule.params).rate == Decimal("0.06")


def test_ibi_de_madrid_2026(book: RuleBook):
    rule = _resolve(book, "tipo_ibi", date(2026, 10, 28))
    assert parse_params(rule.kind, rule.params).rate == Decimal("0.00414")
    assert _resolve(book, "tipo_ibi", date(2025, 6, 1)) is None  # 2025 no está cargado


def test_amortizacion(book: RuleBook):
    rule = _resolve(book, "amortizacion_inmueble_alquiler", date(2026, 10, 28))
    assert parse_params(rule.kind, rule.params).rate == Decimal("0.03")


def test_reduccion_contrato_de_2026_usa_la_ley_12_2023(book: RuleBook):
    rule = _resolve(book, "reduccion_irpf_alquiler", date(2026, 11, 15))
    params = parse_params(rule.kind, rule.params)
    assert rule.id == "irpf-reduccion-alquiler-ley-12-2023"
    assert params.case("general").reduction == Decimal("0.50")


def test_reduccion_contrato_de_2027_base_y_escenario(book: RuleBook):
    contrato = date(2027, 1, 15)
    base = _resolve(book, "reduccion_irpf_alquiler", contrato)
    escenario = _resolve(book, "reduccion_irpf_alquiler", contrato, include_pending=True)
    # Sin convalidar el RDL 29/2026, el plan base sigue con la Ley 12/2023…
    assert base.id == "irpf-reduccion-alquiler-ley-12-2023"
    # …y el escenario aplica el RDL 29/2026.
    assert escenario.id == "irpf-reduccion-alquiler-rdl-29-2026"
    params = parse_params(escenario.kind, escenario.params)
    assert params.case("primer-alquiler-sobre-indice").reduction == Decimal("0.50")
