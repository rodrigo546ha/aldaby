"""Bonificaciones de la cuota y deducción del IRPF de Ceuta y Melilla (ADR-0045).

Valores a mano con las reglas del repositorio: ITP 6 % (TRLITPAJD art. 11.1.a) y AJD 0,5 %
(art. 31.2) con el 50 % del art. 57 bis; IPSI 4 % (ordenanza de Ceuta, art. 33.Tres); IBI de
Ceuta 0,79 % (libro de Hacienda 2026) con el 50 % del TRLRHL art. 159.2; deducción del 60 % de la
Ley del IRPF, art. 68.4.
"""

from datetime import date
from decimal import Decimal

import pytest

from housefinder.engines.irpf import Bracket, IncomeTaxProfile, IrpfPart, incremental_tax
from housefinder.regulation.kinds import RentalFacts
from housefinder.regulation.resolvers import (
    ibi_annual,
    purchase_tax,
    purchase_tax_rate,
    tax_params,
)
from housefinder.regulation.rules import RuleBook, default_rules_dir
from housefinder.regulation.transactions import municipal_gains_params, purchase_costs

D = Decimal
CEUTA = "ES-18-51001"
MELILLA = "ES-19-52001"
HOY = date(2026, 11, 3)


@pytest.fixture(scope="module")
def book() -> RuleBook:
    return RuleBook.from_dir(default_rules_dir())


def test_itp_con_la_bonificacion_del_50(book):
    itp = purchase_tax(book, D(100000), CEUTA, HOY, False, allow_unverified=True)
    assert itp.value == D("3000.00")  # 100.000 × 6 % × (1 − 0,5)
    assert {s.id for s in itp.sources} >= {"ceuta-itp-inmuebles-2002", "ceuta-bonificacion-itp"}
    assert "bonificación" in itp.formula
    rate = purchase_tax_rate(book, MELILLA, HOY, False, allow_unverified=True)
    assert rate.value == D("0.03")


def test_vivienda_nueva_con_ipsi_y_ajd_bonificado(book):
    costs = purchase_costs(book, D(100000), CEUTA, HOY, True, allow_unverified=True)
    assert costs.tax.value == D("4000.00")  # IPSI del 4 %, no IVA del 10 %
    assert costs.stamp_duty is not None
    assert costs.stamp_duty.value == D("250.00")  # 100.000 × 0,5 % × (1 − 0,5)


def test_el_iva_de_la_vivienda_nueva_es_el_del_territorio(book):
    # Antes se buscaba siempre en ES: Canarias pagaba el IVA del 10 % en vez del IGIC del 7 %
    canarias = purchase_costs(book, D(100000), "ES-05-35016", HOY, True, allow_unverified=True)
    assert canarias.tax.value == D("7000.00")
    madrid = purchase_costs(book, D(100000), "ES-13-28079", HOY, True, allow_unverified=True)
    assert madrid.tax.value == D("10000.00")


def test_ibi_y_plusvalia_con_la_bonificacion_municipal(book):
    ibi = ibi_annual(book, D(100000), CEUTA, HOY, allow_unverified=True)
    assert ibi.value == D("395.00")  # 100.000 × 0,79 % × (1 − 0,5)
    gains = municipal_gains_params(book, CEUTA, date(2036, 6, 1), 10, 0, D(1), D(1),
                                   allow_unverified=True)
    assert gains.params.rebate == D("0.5") and gains.params.rate == D("0.27")
    madrid = municipal_gains_params(book, "ES-13-28079", date(2036, 6, 1), 10, 0, D(1), D(1),
                                    allow_unverified=True)
    assert madrid.params.rebate == 0  # sin regla, sin bonificación


def test_deduccion_del_60_de_la_parte_proporcional_de_la_cuota():
    flat = IrpfPart((Bracket(D(0), D("0.10")),), D(0))
    profile = IncomeTaxProfile(other_base=D(20000), state=flat, regional=flat)
    # Con el alquiler: 30.000 × 20 % = 6.000; sin él, 4.000. Incremental 2.000. La parte de la
    # cuota del alquiler es 6.000 × 10.000 / 30.000 = 2.000, y se deduce su 60 %: 1.200.
    assert incremental_tax(D(10000), profile) == D("2000.00")
    assert incremental_tax(D(10000), profile, D("0.6")) == D("800.00")
    # Sin renta positiva no hay nada que deducir
    assert incremental_tax(D(-1000), profile, D("0.6")) == incremental_tax(D(-1000), profile)


def test_la_deduccion_va_por_el_territorio_del_inmueble(book):
    situation = RentalFacts(contract="primer-alquiler", large_holder=False)
    ceuta = tax_params(book, CEUTA, HOY, situation, marginal_rate=D("0.3"),
                       allow_unverified=True)
    assert ceuta.territorial_deduction == D("0.6")
    assert "ceuta-deduccion-irpf-rentas" in ceuta.rule_ids
    madrid = tax_params(book, "ES-13-28079", HOY, situation, marginal_rate=D("0.3"),
                        allow_unverified=True)
    assert madrid.territorial_deduction == 0
