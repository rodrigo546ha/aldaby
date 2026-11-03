"""Resolutores de gastos y tributos de compra y venta con las reglas del repositorio (tanda 4).

Valores calculados a mano; ver tests/test_taxes.py para el detalle de los aranceles.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from housefinder.regulation.kinds import GainsRate, parse_params
from housefinder.regulation.resolvers import purchase_tax
from housefinder.regulation.rules import RuleBook, default_rules_dir
from housefinder.regulation.transactions import (
    municipal_gains_params,
    purchase_costs,
    savings_tax_profile,
)

D = Decimal
MADRID = "ES-13-28079"
HOY = date(2026, 10, 29)


@pytest.fixture(scope="module")
def book() -> RuleBook:
    return RuleBook.from_dir(default_rules_dir())


def test_compra_usada_en_madrid(book):
    costs = purchase_costs(book, D(200000), MADRID, HOY, False, allow_unverified=True)
    assert costs.tax.key == "purchase_costs.transfer_tax"
    assert costs.tax.value == D("12000.00")
    assert costs.stamp_duty is None
    assert costs.notary is None  # Código Civil, art. 1455: la escritura la paga el vendedor
    assert costs.registry.value == D("214.05")  # 176,90 + 37,15 de IVA
    assert costs.total.value == D("12214.05")
    ids = {r.id for r in costs.total.sources}
    assert {"arancel-registral-inscripciones", "iva-tipo-general-2012"} <= ids


def test_compra_nueva_banda_intermedia_del_ajd(book):
    costs = purchase_costs(book, D(150000), MADRID, HOY, True, "comprador",
                           allow_unverified=True)
    assert costs.tax.value == D("15000.00")  # IVA 10 %
    assert costs.stamp_duty is not None and costs.stamp_duty.value == D("750.00")  # 0,5 %
    # Notaría: 90,15 + 108,18 + 45,08 + 89.898,79 × 1‰ = 333,3087 × 0,95 = 316,64;
    # + 66,49 de IVA.
    assert costs.notary is not None and costs.notary.value == D("383.13")


def test_itp_no_se_aplica_a_vivienda_nueva(book):
    with pytest.raises(LookupError, match="IVA y AJD"):
        purchase_tax(book, D(200000), MADRID, HOY, True, allow_unverified=True)


def test_coeficiente_de_menos_de_un_año_se_prorratea(book):
    resolved = municipal_gains_params(book, MADRID, HOY, 0, 6, D(40000), D("0.4"),
                                      allow_unverified=True)
    assert resolved.params.coefficient == D("0.075")  # 0,15 × 6 / 12
    assert resolved.params.rate == D("0.29")


def test_veinte_años_o_mas_usa_el_ultimo_coeficiente(book):
    resolved = municipal_gains_params(book, MADRID, HOY, 25, 0, D(40000), D("0.4"),
                                      allow_unverified=True)
    assert resolved.params.coefficient == D("0.40")


def test_coeficiente_municipal_limitado_por_el_maximo(tmp_path: Path, book):
    # Un municipio con coeficientes por encima del máximo estatal: se aplica el máximo.
    (tmp_path / "x.yaml").write_text(
        """
- id: maximos
  kind: coeficientes_plusvalia
  territory: ES
  effective_from: 2024-01-01
  verified: false
  params: {by_years: [0.15, 0.15, 0.14, 0.14, 0.16, 0.18, 0.19, 0.20, 0.19, 0.15, 0.12,
                      0.10, 0.09, 0.09, 0.09, 0.09, 0.10, 0.13, 0.17, 0.23, 0.40]}
  source_url: https://example.org/max
- id: municipio
  kind: coeficientes_plusvalia
  territory: ES-13-28005
  effective_from: 2024-01-01
  verified: false
  params: {by_years: [0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.50,
                      0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10]}
  source_url: https://example.org/municipio
- id: tipo
  kind: tipo_plusvalia
  territory: ES-13-28005
  effective_from: 2024-01-01
  verified: false
  params: {rate: 0.30}
  source_url: https://example.org/tipo
""",
        encoding="utf-8",
    )
    local = RuleBook.from_dir(tmp_path)
    ten = municipal_gains_params(local, "ES-13-28005", HOY, 10, 0, D(1), D(1),
                                 allow_unverified=True)
    assert ten.params.coefficient == D("0.12")  # 0,50 del municipio, limitado a 0,12
    two = municipal_gains_params(local, "ES-13-28005", HOY, 2, 0, D(1), D(1),
                                 allow_unverified=True)
    assert two.params.coefficient == D("0.10")  # el municipal, menor que 0,14


def test_tipo_de_la_plusvalia_por_años_de_tenencia():
    tipo = parse_params("tipo_plusvalia", {"by_years": [
        {"from_years": 0, "rate": 0.30}, {"from_years": 6, "rate": 0.25},
        {"from_years": 11, "rate": 0.20},
    ]})
    assert isinstance(tipo, GainsRate)
    assert [tipo.for_years(y) for y in (0, 5, 6, 10, 11, 25)] == [
        D("0.30"), D("0.30"), D("0.25"), D("0.25"), D("0.20"), D("0.20")]
    assert parse_params("tipo_plusvalia", {"rate": 0.29}).for_years(7) == D("0.29")
    with pytest.raises(ValueError, match="uno de los dos"):
        parse_params("tipo_plusvalia", {"rate": 0.3, "by_years": [{"from_years": 0, "rate": 0.3}]})
    with pytest.raises(ValueError, match="empezar en 0"):
        parse_params("tipo_plusvalia", {"by_years": [{"from_years": 1, "rate": 0.3}]})


def test_gijon_cambia_de_tipo_con_los_años(book):
    # Ordenanza 1.03, art. 8.1: 25 % hasta 5 años, 22 % de 6 a 19 y 18 % desde 20
    gijon = "ES-03-33024"
    rates = [municipal_gains_params(book, gijon, HOY, years, 0, D(1), D(1),
                                    allow_unverified=True).params.rate
             for years in (5, 6, 19, 20, 30)]
    assert rates == [D("0.25"), D("0.22"), D("0.22"), D("0.18"), D("0.18")]


def test_ahorro_recibe_el_minimo_que_sobra_de_la_base_general(book):
    # Base general 3.000 €: sobran 5.550 − 3.000 en la parte estatal y 5.956,65 − 3.000 en
    # la autonómica (contribuyente de 40 años sin descendientes).
    profile = savings_tax_profile(book, "ES-13", HOY, D(0), D(3000), 40, (),
                                  allow_unverified=True)
    assert profile.state.minimum == D("2550")
    assert profile.regional.minimum == D("2956.65")


def test_sin_base_general_el_minimo_se_supone_absorbido(book):
    profile = savings_tax_profile(book, "ES-13", HOY, D(0), None, 40, (),
                                  allow_unverified=True)
    assert profile.state.minimum == 0
    assert any(r.id == "minimo-absorbido-por-la-base-general" for r in profile.sources)
