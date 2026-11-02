"""Resolutores de normativa: de reglas a entradas de los motores (F2.7).

Usan las reglas del repositorio. Mientras estén sin verificar, solo se resuelven con
allow_unverified=True y todas las cifras salen provisionales.
"""

from datetime import date
from decimal import Decimal

import pytest

from housefinder.core.figures import SourceRef
from housefinder.engines.cashflow import InvestmentInputs, RentalAssumptions, compute_cashflow
from housefinder.regulation.kinds import RentalFacts
from housefinder.regulation.resolvers import (
    ibi_annual,
    income_tax_profile,
    purchase_tax,
    rental_reduction,
    tax_params,
)
from housefinder.regulation.rules import RuleBook, default_rules_dir

MADRID = "ES-13-28079"
PRECIO = SourceRef("user_input", "precio-de-prueba")
TIPO_MARGINAL = SourceRef("user_input", "tipo-marginal-de-prueba")
# Inversor particular que alquila por primera vez a un adulto, fuera de zona tensionada.
PRIMER_ALQUILER = RentalFacts(contract="primer-alquiler", large_holder=False)


@pytest.fixture(scope="module")
def book() -> RuleBook:
    return RuleBook.from_dir(default_rules_dir())


# --- Impuesto de compra -------------------------------------------------------


def test_itp_valor_conocido(book: RuleBook):
    # 150.000 € × 6 % (DL 1/2010 de Madrid, art. 28) = 9.000,00 €
    fig = purchase_tax(
        book, Decimal(150000), MADRID, date(2026, 11, 1), new_build=False,
        price_sources=(PRECIO,), allow_unverified=True,
    )
    assert fig.value == Decimal("9000.00")
    assert fig.key == "purchase_costs.transfer_tax"
    assert SourceRef("rule", "madrid-itp-inmuebles-2014", provisional=True) in fig.sources
    assert PRECIO in fig.sources
    assert fig.provisional  # regla sin verificar


def test_sin_verificar_no_se_resuelve(book: RuleBook):
    with pytest.raises(LookupError, match="impuesto_compra_segunda_mano"):
        purchase_tax(book, Decimal(150000), MADRID, date(2026, 11, 1), new_build=False)


def test_vivienda_nueva_aun_no_disponible(book: RuleBook):
    with pytest.raises(LookupError, match="nueva"):
        purchase_tax(
            book, Decimal(150000), MADRID, date(2026, 11, 1), new_build=True,
            allow_unverified=True,
        )


# --- IBI ----------------------------------------------------------------------


def test_ibi_valor_conocido(book: RuleBook):
    # 85.000 € de valor catastral × 0,414 % (Ordenanza 9/2025) = 351,90 €
    fig = ibi_annual(book, Decimal(85000), MADRID, date(2026, 6, 1), allow_unverified=True)
    assert fig.value == Decimal("351.90")
    assert fig.key == "holding_costs.ibi_annual"
    assert SourceRef("rule", "madrid-ibi-urbana-2026", provisional=True) in fig.sources


def test_ibi_sin_regla_para_el_ano(book: RuleBook):
    with pytest.raises(LookupError, match="tipo_ibi"):
        ibi_annual(book, Decimal(85000), MADRID, date(2025, 6, 1), allow_unverified=True)


# --- TaxParams ----------------------------------------------------------------


def test_tax_params_contrato_de_2026(book: RuleBook):
    tax = tax_params(
        book, MADRID, contract_date=date(2026, 11, 15), situation=PRIMER_ALQUILER,
        marginal_rate=Decimal("0.30"), marginal_rate_sources=(TIPO_MARGINAL,),
        allow_unverified=True,
    )
    assert tax.rental_income_reduction == Decimal("0.50")  # Ley 12/2023, d) cualquier otro caso
    assert tax.depreciation_rate == Decimal("0.03")
    assert tax.marginal_rate == Decimal("0.30")
    assert tax.rule_ids == (
        "irpf-reduccion-alquiler-ley-12-2023",
        "irpf-amortizacion-inmueble",
        "irpf-limite-intereses-reparacion",
    )
    assert tax.interest_repair_carryforward_years == 4
    assert TIPO_MARGINAL in tax.sources


def test_misma_situacion_distinto_regimen(book: RuleBook):
    # Primer alquiler en zona tensionada, arrendatario adulto, contrato de 2027.
    situacion = PRIMER_ALQUILER.model_copy(update={"stressed_zone": True})
    contrato = date(2027, 1, 15)
    base = rental_reduction(book, MADRID, contrato, situacion, allow_unverified=True)
    rdl = rental_reduction(
        book, MADRID, contrato, situacion, include_pending=True, allow_unverified=True
    )
    # Ley 12/2023: la zona tensionada solo da el 70 % con arrendatario joven → 50 %.
    assert (base.case, base.reduction) == ("general", Decimal("0.50"))
    # RDL 29/2026: b) 3.º primer alquiler en zona tensionada → 90 %.
    assert (rdl.case, rdl.reduction) == ("primer-alquiler-zona-tensionada", Decimal("0.90"))


def test_se_aplica_la_mayor_reduccion(book: RuleBook):
    # Joven y zona tensionada con el RDL 29/2026: 95 % (no 90 % ni 85 %).
    situacion = PRIMER_ALQUILER.model_copy(update={"stressed_zone": True, "young_tenant": True})
    res = rental_reduction(
        book, MADRID, date(2027, 1, 15), situacion, include_pending=True, allow_unverified=True
    )
    assert (res.case, res.reduction) == ("primer-alquiler-zona-tensionada-joven", Decimal("0.95"))


def test_gran_tenedor_sin_otro_supuesto_no_tiene_reduccion(book: RuleBook):
    gran_tenedor = RentalFacts(contract="primer-alquiler", large_holder=True)
    res = rental_reduction(
        book, MADRID, date(2027, 1, 15), gran_tenedor, include_pending=True, allow_unverified=True
    )
    assert (res.case, res.reduction) == (None, Decimal(0))


def test_las_cifras_del_cash_flow_citan_las_reglas(book: RuleBook):
    tax = tax_params(
        book, MADRID, contract_date=date(2026, 11, 15), situation=PRIMER_ALQUILER,
        marginal_rate=Decimal("0.30"), allow_unverified=True,
    )
    inv = InvestmentInputs(
        price=Decimal(150000), purchase_costs=Decimal(15000), renovation=Decimal(0),
        loan=Decimal(105000), monthly_mortgage_payment=Decimal("442.68"),
        first_year_interest=Decimal(3100), construction_value=Decimal(60000),
    )
    rent = RentalAssumptions(
        monthly_rent=Decimal(900), vacancy_rate=Decimal("0.05"),
        community_fees_monthly=Decimal(60), ibi_annual=Decimal(300),
        insurance_annual=Decimal(350), management_fee_rate=Decimal(0),
        maintenance_reserve_rate=Decimal("0.05"),
    )
    res = compute_cashflow(inv, rent, tax)
    ids = {ref.id for ref in res.annual_tax.sources if ref.kind == "rule"}
    assert ids == {
        "irpf-reduccion-alquiler-ley-12-2023",
        "irpf-amortizacion-inmueble",
        "irpf-limite-intereses-reparacion",
    }
    assert res.annual_tax.provisional



# --- Perfil del IRPF para la cuota incremental (ADR-0007) ---------------------------

EJERCICIO = date(2026, 12, 31)
BASE = SourceRef("user_input", "base-liquidable-de-prueba")


def test_perfil_irpf_residente_en_madrid(book: RuleBook):
    perfil = income_tax_profile(
        book, residence="ES-13", tax_year=EJERCICIO, other_base=Decimal(30000), age=40,
        descendant_ages=(), other_base_sources=(BASE,), allow_unverified=True,
    )
    assert perfil.state.minimum == Decimal(5550)
    assert perfil.regional.minimum == Decimal("5956.65")
    assert perfil.regional.scale[1].start == Decimal("13362.22")
    ids = {ref.id for ref in perfil.sources if ref.kind == "rule"}
    assert ids == {
        "irpf-escala-general-estatal-2021",
        "madrid-irpf-escala-general-2023",
        "irpf-minimo-contribuyente-2015",
        "irpf-minimo-descendientes-2015",
        "madrid-irpf-minimo-contribuyente-2023",
        "madrid-irpf-minimo-descendientes-2023",
    }
    assert BASE in perfil.sources


def test_minimos_con_edad_y_descendientes(book: RuleBook):
    perfil = income_tax_profile(
        book, residence="ES-13", tax_year=EJERCICIO, other_base=Decimal(30000), age=70,
        descendant_ages=(10, 2), allow_unverified=True,
    )
    # Estatal: 5.550 + 1.150 + 2.400 + 2.700 + 2.800 = 14.600
    # Madrid:  5.956,65 + 1.234,26 + 2.575,85 + 2.897,83 + 3.005,16 = 15.669,75
    assert perfil.state.minimum == Decimal(14600)
    assert perfil.regional.minimum == Decimal("15669.75")


def test_residencia_sin_escala_autonomica(book: RuleBook):
    with pytest.raises(LookupError, match="escala_irpf_general_autonomica"):
        income_tax_profile(
            book, residence="ES-11", tax_year=EJERCICIO, other_base=Decimal(30000), age=40,
            descendant_ages=(), allow_unverified=True,
        )


def test_cash_flow_con_cuota_incremental_y_reglas_reales(book: RuleBook):
    perfil = income_tax_profile(
        book, residence="ES-13", tax_year=EJERCICIO, other_base=Decimal(30000), age=40,
        descendant_ages=(), allow_unverified=True,
    )
    tax = tax_params(
        book, MADRID, contract_date=date(2026, 11, 15), situation=PRIMER_ALQUILER,
        income=perfil, allow_unverified=True,
    )
    inv = InvestmentInputs(
        price=Decimal(150000), purchase_costs=Decimal(15000), renovation=Decimal(0),
        loan=Decimal(105000), monthly_mortgage_payment=Decimal("442.68"),
        first_year_interest=Decimal(3100), construction_value=Decimal(60000),
    )
    rent = RentalAssumptions(
        monthly_rent=Decimal(900), vacancy_rate=Decimal("0.05"),
        community_fees_monthly=Decimal(60), ibi_annual=Decimal(300),
        insurance_annual=Decimal(350), management_fee_rate=Decimal(0),
        maintenance_reserve_rate=Decimal("0.05"),
    )
    # Mismo caso que tests/test_cashflow.py: 1.738,50 reducidos sobre 30.000 → 483,31
    assert compute_cashflow(inv, rent, tax).annual_tax.value == Decimal("483.31")


def test_tax_params_exige_un_modo(book: RuleBook):
    with pytest.raises(ValueError):
        tax_params(
            book, MADRID, contract_date=date(2026, 11, 15), situation=PRIMER_ALQUILER,
            allow_unverified=True,
        )


ITP_TRAMOS = """
- id: prueba-itp-tramos
  kind: impuesto_compra_segunda_mano
  territory: ES-09
  effective_from: 2025-06-27
  effective_to: null
  status: vigente
  verified: false
  params:
    brackets:
      - {from: 0, rate: 0.10}
      - {from: 600000, rate: 0.11}
      - {from: 900000, rate: 0.12}
      - {from: 1500000, rate: 0.13}
  source_url: https://www.boe.es/prueba
  notes: "Escala de prueba con la forma de la catalana: cada tipo solo en su tramo."
"""


def test_itp_por_tramos_cada_tipo_en_su_tramo(tmp_path):
    from housefinder.regulation.resolvers import purchase_tax_rate

    (tmp_path / "itp.yaml").write_text(ITP_TRAMOS, encoding="utf-8")
    tramos = RuleBook.from_dir(tmp_path)
    on = date(2026, 11, 1)

    def tax(price: int) -> Decimal:
        return purchase_tax(tramos, Decimal(price), "ES-09-08019", on, new_build=False,
                            allow_unverified=True).value

    # 300.000 × 10 % = 30.000,00
    assert tax(300000) == Decimal("30000.00")
    # 600.000 × 10 % + 300.000 × 11 % + 100.000 × 12 % = 60.000 + 33.000 + 12.000 = 105.000,00
    assert tax(1000000) == Decimal("105000.00")
    # 60.000 + 33.000 + 600.000 × 12 % + 500.000 × 13 % = 60.000 + 33.000 + 72.000 + 65.000
    assert tax(2000000) == Decimal("230000.00")
    with pytest.raises(LookupError, match="tramos"):
        purchase_tax_rate(tramos, "ES-09", on, new_build=False, allow_unverified=True)


def test_el_itp_lleva_tipo_o_tramos_pero_no_los_dos():
    from housefinder.regulation.kinds import parse_params

    with pytest.raises(ValueError, match="uno de los dos"):
        parse_params("impuesto_compra_segunda_mano",
                     {"rate": 0.1, "brackets": [{"from": 0, "rate": 0.1}]})
    with pytest.raises(ValueError, match="uno de los dos"):
        parse_params("impuesto_compra_segunda_mano", {})
    with pytest.raises(ValueError, match="empezar en 0"):
        parse_params("impuesto_compra_segunda_mano", {"brackets": [{"from": 10, "rate": 0.1}]})


def test_itp_valenciano_el_tipo_del_tramo_sobre_todo_el_valor(book: RuleBook):
    # Ley 13/1997 de la Generalitat Valenciana, art. 13.Uno (Ley 5/2025): 9 %; por encima de
    # 1.000.000 €, 11 % sobre todo el valor. 1.000.000 × 9 % = 90.000,00; 1.200.000 × 11 % =
    # 132.000,00 (no 90.000 + 200.000 × 11 %).
    on = date(2026, 11, 1)

    def tax(price: int) -> Decimal:
        return purchase_tax(book, Decimal(price), "ES-10-46250", on, new_build=False,
                            allow_unverified=True).value

    assert tax(1000000) == Decimal("90000.00")
    assert tax(1200000) == Decimal("132000.00")
