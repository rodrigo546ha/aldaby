"""Motor del IRPF: escalas, mínimos y cuota incremental (ADR-0007).

Escalas y mínimos copiados de las reglas cargadas (data/rules/irpf.yaml y madrid.yaml).
Los valores esperados se calcularon aparte con las tablas del BOE («cuota íntegra» acumulada
del tramo + resto × tipo), un método distinto del de este motor.
"""

from decimal import Decimal

import pytest

from housefinder.core.figures import SourceRef
from housefinder.engines.irpf import (
    Bracket,
    IncomeTaxProfile,
    IrpfPart,
    MinimumAmounts,
    income_tax,
    incremental_tax,
    personal_minimum,
    scale_tax,
)

ESTATAL = (
    Bracket(Decimal(0), Decimal("0.095")),
    Bracket(Decimal(12450), Decimal("0.12")),
    Bracket(Decimal(20200), Decimal("0.15")),
    Bracket(Decimal(35200), Decimal("0.185")),
    Bracket(Decimal(60000), Decimal("0.225")),
    Bracket(Decimal(300000), Decimal("0.245")),
)
MADRID = (
    Bracket(Decimal(0), Decimal("0.085")),
    Bracket(Decimal("13362.22"), Decimal("0.107")),
    Bracket(Decimal("19004.63"), Decimal("0.128")),
    Bracket(Decimal("35425.68"), Decimal("0.174")),
    Bracket(Decimal("57320.40"), Decimal("0.205")),
)
MIN_ESTATAL = MinimumAmounts(
    general=Decimal(5550), over_65_extra=Decimal(1150), over_75_extra=Decimal(1400),
    descendants=(Decimal(2400), Decimal(2700), Decimal(4000), Decimal(4500)),
    under_3_extra=Decimal(2800),
)
FUENTE = SourceRef("rule", "escalas-de-prueba")


def _perfil(otra_base: int) -> IncomeTaxProfile:
    return IncomeTaxProfile(
        other_base=Decimal(otra_base),
        state=IrpfPart(ESTATAL, Decimal(5550)),
        regional=IrpfPart(MADRID, Decimal("5956.65")),
        sources=(FUENTE,),
    )


# --- Escala -----------------------------------------------------------------------


def test_escala_estatal_coincide_con_la_tabla_del_boe():
    # Tabla del BOE: desde 20.200 la cuota acumulada es 2.112,75 y el resto va al 15 %.
    # 2.112,75 + (30.000 − 20.200) × 0,15 = 3.582,75
    assert scale_tax(Decimal(30000), ESTATAL) == Decimal("3582.75")
    # La cuota acumulada de cada tramo del BOE sale de los tipos.
    assert scale_tax(Decimal(300000), ESTATAL) == Decimal("62950.75")


def test_escala_con_base_cero_o_negativa():
    assert scale_tax(Decimal(0), ESTATAL) == 0
    assert scale_tax(Decimal(-100), ESTATAL) == 0


# --- Cuota ------------------------------------------------------------------------


def test_cuota_estatal_y_autonomica():
    # Estatal: 3.582,75 − escala(5.550) = 3.582,75 − 527,25 = 3.055,50
    # Madrid:  2.640,62 (tabla del BOE). Total 5.696,12.
    assert income_tax(Decimal(30000), _perfil(0)) == Decimal("5696.12")


def test_base_por_debajo_del_minimo_no_tributa():
    assert income_tax(Decimal(5000), _perfil(0)) == Decimal("0.00")


@pytest.mark.parametrize(
    ("otra_base", "neto", "esperado"),
    [
        (30000, 3000, "834.00"),  # mismo tramo: 3.000 × (15 % + 12,8 %)
        (34000, 3000, "969.42"),  # cruza tramo estatal (35.200) y de Madrid (35.425,68)
        (30000, -2000, "-556.00"),  # rendimiento negativo: ahorro fiscal
        (4000, 1000, "0.00"),  # todo bajo el mínimo
    ],
)
def test_cuota_incremental(otra_base, neto, esperado):
    assert incremental_tax(Decimal(neto), _perfil(otra_base)) == Decimal(esperado)


def test_el_tipo_marginal_se_queda_corto_al_cruzar_tramo():
    marginal = Decimal(3000) * (Decimal("0.15") + Decimal("0.128"))
    assert incremental_tax(Decimal(3000), _perfil(34000)) > marginal


# --- Mínimo personal y familiar ----------------------------------------------------


@pytest.mark.parametrize(
    ("edad", "esperado"),
    [(40, 5550), (65, 5550), (66, 6700), (76, 8100)],
)
def test_minimo_por_edad(edad, esperado):
    # «edad superior a 65 años»: con 65 no hay aumento.
    assert personal_minimum(MIN_ESTATAL, edad, ()) == Decimal(esperado)


def test_minimo_por_descendientes():
    # Primero (10 años) 2.400 + segundo (2 años) 2.700 + menor de tres 2.800 = 7.900
    assert personal_minimum(MIN_ESTATAL, 40, (10, 2)) - Decimal(5550) == Decimal(7900)


def test_cuarto_y_siguientes():
    extra = personal_minimum(MIN_ESTATAL, 40, (20, 18, 15, 12, 9)) - Decimal(5550)
    assert extra == Decimal(2400 + 2700 + 4000 + 4500 + 4500)


# --- IRPF foral (ADR-0046) ---------------------------------------------------------------


def test_deduccion_que_baja_con_la_base():
    from housefinder.engines.irpf import TaperedDeduction

    # Navarra, mínimo personal por renta: 1.280 € hasta 17.500; 150 € a 30.000; 0 a 32.000
    t = TaperedDeduction(((Decimal(17500), Decimal(1280)), (Decimal(30000), Decimal(150)),
                          (Decimal(32000), Decimal(0))))
    assert t.amount(Decimal(10000)) == Decimal(1280)
    assert t.amount(Decimal(25000)) == Decimal(1280) - Decimal("0.0904") * 7500  # 602
    assert t.amount(Decimal(31000)) == Decimal(75)
    assert t.amount(Decimal(40000)) == Decimal(0)


def test_deducciones_forales_por_edad_y_descendientes():
    from housefinder.engines.irpf import ForalAmounts, foral_deductions

    amounts = ForalAmounts(
        general=Decimal(1615),
        age=((66, Decimal(393)), (76, Decimal(714))),
        age_phaseout=(Decimal(20000), Decimal(30000)),
        descendants=(Decimal(682), Decimal(844), Decimal(1421)),
        young_children=((6, Decimal(394)),),
    )
    fixed, tapered = foral_deductions(amounts, 40, (4, 8, 10, 12))
    # 1.615 + 682 + 844 + 1.421 + 1.421 (el último sirve para los demás) + 394 (menor de 6)
    assert fixed == Decimal(6377) and tapered == ()
    fixed, tapered = foral_deductions(amounts, 70, ())
    assert fixed == Decimal(1615)
    assert tapered[0].amount(Decimal(25000)) == Decimal("196.5")  # 393 − 0,0393 × 5.000


def test_cuota_foral_con_minoracion_sin_bajar_de_cero():
    from housefinder.engines.irpf import ZERO_PART

    scale = (Bracket(Decimal(0), Decimal("0.23")), Bracket(Decimal(18080), Decimal("0.28")))
    profile = IncomeTaxProfile(other_base=Decimal(30000),
                               state=IrpfPart(scale, Decimal(0), Decimal(1615)),
                               regional=ZERO_PART)
    # 18.080 × 23 % + 11.920 × 28 % = 7.496,00 − 1.615 = 5.881,00
    assert income_tax(Decimal(30000), profile) == Decimal("5881.00")
    assert income_tax(Decimal(5000), profile) == Decimal("0.00")  # 1.150 − 1.615 → 0
