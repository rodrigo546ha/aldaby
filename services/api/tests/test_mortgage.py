from decimal import Decimal

import pytest

from housefinder.core.figures import SourceRef
from housefinder.engines import mortgage as m


def test_cuota_francesa_valor_conocido():
    # 200.000 € al 3 % a 30 años: 843,21 €/mes
    assert m.monthly_payment(Decimal(200000), Decimal("0.03"), 30) == Decimal("843.21")


def test_cuota_sin_interes():
    assert m.monthly_payment(Decimal(120000), Decimal(0), 10) == Decimal("1000.00")


def test_inversa_de_la_cuota():
    p = m.principal_for_payment(Decimal("843.21"), Decimal("0.03"), 30)
    assert abs(p - Decimal(200000)) < Decimal(5)


def test_cuadro_amortizacion_termina_en_cero():
    rows = m.amortization_schedule(Decimal(150000), Decimal("0.035"), 25)
    assert len(rows) == 300
    assert rows[-1].balance == Decimal("0.00")
    total_principal = sum(r.principal for r in rows)
    assert total_principal == Decimal(150000)


def test_capacidad_limitada_por_ahorro():
    res = m.affordability(
        m.BuyerFinances(Decimal(4000), Decimal(0), Decimal(60000), 30),
        annual_rate=Decimal("0.03"),
        purchase_cost_rate=Decimal("0.10"),
    )
    # 60.000 / (1 - 0,70 + 0,10) = 150.000
    assert res.binding_constraint == "ahorro"
    assert res.max_price.value == Decimal("150000.00")
    assert res.max_loan.value == Decimal("105000.00")


def test_capacidad_limitada_por_ingresos():
    res = m.affordability(
        m.BuyerFinances(Decimal(1500), Decimal(200), Decimal(500000), 40),
        annual_rate=Decimal("0.03"),
        purchase_cost_rate=Decimal("0.10"),
    )
    assert res.binding_constraint == "ingresos"
    assert res.max_payment.value == Decimal("325.00")


def test_plazo_limitado_por_edad():
    res = m.affordability(
        m.BuyerFinances(Decimal(3000), Decimal(0), Decimal(80000), 60),
        annual_rate=Decimal("0.03"),
        purchase_cost_rate=Decimal("0.10"),
    )
    assert res.years.value == Decimal(15)


def test_sin_plazo_por_edad_lanza_error():
    with pytest.raises(ValueError):
        m.affordability(
            m.BuyerFinances(Decimal(3000), Decimal(0), Decimal(80000), 80),
            annual_rate=Decimal("0.03"),
            purchase_cost_rate=Decimal("0.10"),
        )


def test_capacidad_con_criterios_por_defecto_es_provisional():
    res = m.affordability(
        m.BuyerFinances(Decimal(4000), Decimal(0), Decimal(60000), 30),
        annual_rate=Decimal("0.03"),
        purchase_cost_rate=Decimal("0.10"),
    )
    assert res.max_price.key == "affordability.max_price"
    assert res.max_price.provisional
    assert res.max_loan.provisional
    assert res.max_payment.provisional
    assert res.years.provisional


def test_capacidad_con_criterios_calibrados_cita_sus_fuentes():
    criterios = m.BankCriteria(source=SourceRef("param", "criterios-banco-x-2026"))
    gastos = SourceRef("rule", "madrid-itp-2026")
    tipo = SourceRef("user_input", "tipo-de-interes")
    res = m.affordability(
        m.BuyerFinances(Decimal(4000), Decimal(0), Decimal(60000), 30),
        annual_rate=Decimal("0.03"),
        purchase_cost_rate=Decimal("0.10"),
        criteria=criterios,
        rate_sources=(tipo,),
        purchase_cost_sources=(gastos,),
    )
    assert not res.max_price.provisional
    assert {criterios.source, gastos, tipo} <= set(res.max_price.sources)
    assert gastos not in res.max_payment.sources


def test_estres_sube_la_cuota():
    base = m.monthly_payment(Decimal(150000), Decimal("0.03"), 30)
    stressed = m.stressed_payment(Decimal(150000), Decimal("0.03"), 30, Decimal("0.02"))
    assert stressed.value > base
    assert stressed.key == "mortgage.stressed_payment"
    assert SourceRef("assumption", "escenario-estres") in stressed.sources
