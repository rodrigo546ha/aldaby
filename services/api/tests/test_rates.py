from decimal import Decimal

import pytest

from housefinder.core.figures import SourceRef
from housefinder.engines import mortgage as m
from housefinder.engines.rates import MortgageTerms, RatePath, RateSegment, rate_segments

OFERTA = SourceRef("user_input", "oferta-banco")
# Trayectoria de prueba, NO una previsión real del Euríbor.
TRAYECTORIA = SourceRef("assumption", "trayectoria-de-prueba", provisional=True)


# --- RatePath ---------------------------------------------------------------


def test_trayectoria_valor_por_tramos():
    path = RatePath(((0, Decimal("0.02")), (12, Decimal("0.025")), (36, Decimal("0.03"))))
    assert path.value_at(0) == Decimal("0.02")
    assert path.value_at(11) == Decimal("0.02")
    assert path.value_at(12) == Decimal("0.025")
    assert path.value_at(200) == Decimal("0.03")


def test_trayectoria_empieza_en_el_mes_cero():
    with pytest.raises(ValueError):
        RatePath(((1, Decimal("0.02")),))


def test_trayectoria_meses_crecientes():
    with pytest.raises(ValueError):
        RatePath(((0, Decimal("0.02")), (12, Decimal("0.02")), (12, Decimal("0.03"))))


def test_trayectoria_desplazada_suma_el_choque_y_cita_el_escenario():
    path = RatePath(((0, Decimal("0.02")), (12, Decimal("0.03"))), (TRAYECTORIA,))
    shifted = path.shifted(Decimal("0.02"), SourceRef("assumption", "escenario-estres"))
    assert shifted.value_at(0) == Decimal("0.04")
    assert shifted.value_at(12) == Decimal("0.05")
    assert SourceRef("assumption", "escenario-estres") in shifted.sources
    assert TRAYECTORIA in shifted.sources


# --- Condiciones y tramos ---------------------------------------------------


def test_fija_un_solo_tramo():
    terms = MortgageTerms.fixed("fija", Decimal("0.03"))
    path = RatePath.flat(Decimal("0.05"))
    assert rate_segments(terms, path, 360) == (RateSegment(0, Decimal("0.03")),)


def test_mixta_tramo_fijo_y_revisiones():
    terms = MortgageTerms("mixta", Decimal("0.02"), 24, Decimal("0.01"), 12)
    path = RatePath(((0, Decimal("0.03")), (36, Decimal("0.04"))))
    assert rate_segments(terms, path, 60) == (
        RateSegment(0, Decimal("0.02")),
        RateSegment(24, Decimal("0.04")),  # 0,03 + 0,01
        RateSegment(36, Decimal("0.05")),  # 0,04 + 0,01
        RateSegment(48, Decimal("0.05")),
    )


def test_etiqueta_invalida():
    with pytest.raises(ValueError):
        MortgageTerms.fixed("Fija Banco A", Decimal("0.03"))


def test_revision_debe_ser_positiva():
    with pytest.raises(ValueError):
        MortgageTerms("variable", Decimal("0.02"), 12, Decimal("0.01"), 0)


# --- Cuadro por tramos ------------------------------------------------------


def test_cuadro_por_tramos_valor_conocido():
    # Calculado a mano con la fórmula francesa cerrada:
    #   100.000 € a 24 meses; 12 meses al 0 %, después índice 12 % + 0 (1 % mensual).
    #   Meses 1–12: 100.000 / 24                                  = 4.166,67
    #   Saldo al mes 12: 100.000 − 12 × 4.166,67                   = 49.999,96
    #   Meses 13–24: 49.999,96 × 0,01 × 1,01^12 / (1,01^12 − 1)    = 4.442,44
    #   Intereses: 11 × 4.442,44 + 4.442,39 (última) − 49.999,96   = 3.309,27
    segments = (RateSegment(0, Decimal(0)), RateSegment(12, Decimal("0.12")))
    rows = m.amortization_schedule_segments(Decimal(100000), 24, segments)
    assert rows[0].payment == Decimal("4166.67")
    assert rows[11].balance == Decimal("49999.96")
    assert rows[12].payment == Decimal("4442.44")
    assert rows[-1].payment == Decimal("4442.39")
    assert rows[-1].balance == Decimal("0.00")
    assert sum(r.interest for r in rows) == Decimal("3309.27")


def test_cuadro_de_un_tramo_igual_que_el_fijo():
    fijo = m.amortization_schedule(Decimal(150000), Decimal("0.035"), 25)
    tramos = m.amortization_schedule_segments(
        Decimal(150000), 300, (RateSegment(0, Decimal("0.035")),)
    )
    assert tramos == fijo


def test_revision_semestral_termina_en_cero():
    segments = tuple(RateSegment(s, Decimal("0.02") + Decimal(s) / 10000) for s in range(0, 90, 6))
    rows = m.amortization_schedule_segments(Decimal(80000), 90, segments)
    assert len(rows) == 90
    assert rows[-1].balance == Decimal("0.00")
    assert sum(r.principal for r in rows) == Decimal(80000)


# --- Comparación fija / variable / mixta -----------------------------------

FIJA = MortgageTerms.fixed("fija", Decimal("0.03"), (OFERTA,))
VARIABLE = MortgageTerms("variable", Decimal(0), 12, Decimal(0), 12, (OFERTA,))
CASO_A = RatePath.flat(Decimal("0.12"), (TRAYECTORIA,))


def _compare(*options: MortgageTerms):
    return m.compare_mortgages(
        principal=Decimal(100000),
        years=2,
        options=options,
        expected_path=CASO_A,
        rate_shock=Decimal("0.02"),
    )


def test_comparacion_valores_conocidos():
    # Fija: 100.000 al 3 % a 24 meses = 4.298,12 €/mes, igual en estrés.
    # Variable: el caso A de arriba; en estrés (14 %): 49.999,96 a 12 meses = 4.489,35.
    res = _compare(FIJA, VARIABLE)
    fija, variable = res.options
    assert fija.first_payment.value == Decimal("4298.12")
    assert fija.stressed_max_payment.value == Decimal("4298.12")
    assert variable.first_payment.value == Decimal("4166.67")
    assert variable.expected_total_interest.value == Decimal("3309.27")
    assert variable.stressed_max_payment.value == Decimal("4489.35")


def test_comparacion_elige_la_mas_barata_y_la_mas_segura():
    res = _compare(FIJA, VARIABLE)
    fija, variable = res.options
    # Fija al 3 %: intereses ≈ 3.155; variable: 3.309,27. La fija es más barata y más segura.
    assert fija.expected_total_interest.value < variable.expected_total_interest.value
    assert res.cheapest_expected == "fija"
    assert res.lowest_stressed_payment == "fija"


def test_la_fija_no_depende_de_la_trayectoria():
    res = _compare(FIJA, VARIABLE)
    fija, variable = res.options
    assert TRAYECTORIA not in fija.expected_total_interest.sources
    assert not fija.expected_total_interest.provisional
    assert TRAYECTORIA in variable.expected_total_interest.sources
    assert variable.expected_total_interest.provisional


def test_claves_por_etiqueta():
    res = _compare(FIJA, VARIABLE)
    assert res.options[1].stressed_max_payment.key == (
        "mortgage_comparison.variable.stressed_max_payment"
    )
    stress = SourceRef("assumption", "escenario-estres")
    assert stress in res.options[1].stressed_max_payment.sources


def test_la_peor_cuota_es_la_pactada_no_el_ajuste_de_redondeo():
    # En la fija, la última cuota absorbe el redondeo (4.298,13): no es la cuota pactada.
    res = _compare(FIJA)
    assert res.options[0].stressed_max_payment.value == Decimal("4298.12")


def test_etiquetas_repetidas_son_un_error():
    with pytest.raises(ValueError):
        _compare(FIJA, FIJA)


def test_sin_opciones_es_un_error():
    with pytest.raises(ValueError):
        _compare()
