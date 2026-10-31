"""Recomendación de tipo de alquiler y de gestión (F6.6, ADR-0024): reglas fijas y deterministas."""

from decimal import Decimal

from housefinder.core.figures import Figure
from housefinder.planning.rental_advice import TypeOption, advise, management_for

D = Decimal


def cash(value: str) -> Figure:
    return Figure("cashflow.monthly_after_tax", D(value), "EUR/mes", "plan")


def option(rental_type="habitual", income="1000", active="100", passive="40", allowed=True,
           reduction=True) -> TypeOption:
    return TypeOption(
        rental_type, allowed, "régimen", (), reduction, (), ("regla",),
        Figure(f"rental.{rental_type}.income", D(income), "EUR/mes", "x") if income else None,
        cash(active) if active else None, cash(passive) if passive else None)


def test_gestion_recomendada():
    assert management_for("turistico", False, "activa")[0] == "pasiva"
    assert management_for("temporada", False, None)[0] == "pasiva"
    assert management_for("habitual", True, "activa") == (
        "pasiva", "Pasiva: la vivienda está fuera de tu comunidad.")
    assert management_for("habitual", False, "pasiva") == ("pasiva", "Pasiva: es la que elegiste.")
    assert management_for("habitaciones", False, None)[0] == "activa"


def test_solo_el_habitual_tiene_cifras():
    advice = advise([option(), option("turistico", income=None, active=None, passive=None,
                                      reduction=False)], "media", "activa", False)
    assert advice.recommended == "habitual"
    assert "único con renta pública" in advice.reasons[-1]
    turistico = advice.types[1]
    assert turistico.cashflow is None and "escribe lo que esperas" in turistico.notes[0]


def test_gana_el_de_mayor_cash_flow_con_su_gestion():
    advice = advise([option(active="100", passive="40"),
                     option("turistico", income="1800", active="400", passive="150",
                            reduction=False)], "media", "activa", False)
    assert advice.recommended == "turistico"
    chosen = advice.chosen()
    assert chosen is not None and chosen.management == "pasiva"
    # Con gestión pasiva el turístico deja 150 > 100 del habitual con gestión activa
    assert chosen.cashflow is not None and chosen.cashflow.value == D(150)
    assert chosen.cashflow.key == "rental.turistico.cashflow"
    assert chosen.delegation_cost is not None and chosen.delegation_cost.value == D("250.00")
    assert advice.types[0].management == "activa" and advice.types[0].cashflow.value == D(100)


def test_empate_gana_el_habitual():
    advice = advise([option(active="100"), option("temporada", active="300", passive="100",
                                                  reduction=False)], "media", "activa", False)
    assert advice.recommended == "habitual"


def test_con_riesgo_bajo_el_habitual():
    advice = advise([option(), option("turistico", active="900", passive="800",
                                      reduction=False)], "baja", "activa", False)
    assert advice.recommended == "habitual"
    assert "riesgo bajo" in advice.reasons[-1]


def test_un_tipo_prohibido_no_se_recomienda():
    advice = advise([option(), option("turistico", active="900", passive="800", allowed=False,
                                      reduction=False)], "media", "activa", False)
    assert advice.recommended == "habitual"
    assert advice.reasons[0] == "El alquiler turístico no se puede ejercer en este municipio."


def test_sin_lo_que_cobra_la_gestion():
    advice = advise([option("temporada", active="200", passive=None, reduction=False),
                     option(active="100", passive=None)], "media", None, False)
    temporada = advice.types[0]
    assert temporada.management == "pasiva" and temporada.delegation_cost is None
    assert temporada.cashflow is not None and temporada.cashflow.value == D(200)
    assert "Falta lo que cobra la gestión" in temporada.notes[0]


def test_reduccion_por_confirmar_se_avisa():
    advice = advise([option("habitaciones", reduction=None)], "media", "activa", False)
    assert "Por confirmar" in advice.types[0].notes[0]


def test_ningun_tipo_con_cifras():
    advice = advise([option(income=None, active=None, passive=None)], "media", None, False)
    assert advice.recommended is None
