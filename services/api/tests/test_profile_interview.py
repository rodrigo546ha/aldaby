"""Entrevista de perfil (ADR-0020): evidencia en la respuesta, conversiones y siguiente pregunta."""

from datetime import date
from decimal import Decimal

import pytest

from housefinder.agent.extraction import Quoted
from housefinder.agent.profiling import ProfileExtraction, check_answer
from housefinder.profiles.interview import (
    QUESTIONS,
    DraftField,
    State,
    apply_answer,
    next_question,
    question_text,
    region_in,
    to_profile,
)
from housefinder.profiles.model import ProfileError

TODAY = date(2026, 10, 31)
NONE = Quoted(value=None, evidence=None)


def raw(**fields) -> ProfileExtraction:
    """Extracción con todo vacío salvo lo indicado (`Quoted` o valores de opción)."""
    base = {name: NONE for name in ("birth_year", "age", "residence", "income", "income_payments",
                                    "debt", "savings", "horizon_years")}
    base |= {"income_period": None, "income_period_evidence": None, "no_debt": False,
             "no_debt_evidence": None, "children_birth_years": [], "children_ages": [],
             "no_children": False, "no_children_evidence": None, "goal": None,
             "goal_evidence": None, "risk_tolerance": None, "risk_tolerance_evidence": None,
             "management": None, "management_evidence": None}
    return ProfileExtraction(**(base | fields))


def q(value, evidence) -> Quoted:
    return Quoted(value=value, evidence=evidence)


def run(state: State, asked: str, text: str, extraction: ProfileExtraction) -> State:
    return apply_answer(state, asked, text, check_answer(text, extraction), TODAY)


def test_varios_datos_en_una_respuesta_y_cuentas_en_codigo():
    text = "Tengo 35 años, vivo en Sevilla y cobro 1.800 netos en 14 pagas"
    state = run(State(), "birth_year", text, raw(
        age=q("35", "Tengo 35 años"), residence=q("Sevilla", "vivo en Sevilla"),
        income=q("1800", "cobro 1.800 netos"), income_payments=q("14", "en 14 pagas")))
    draft = state.draft
    assert draft["birth_year"].value == "1991" and draft["birth_year"].source == "calculado"
    assert draft["residence"].value == "ES-01" and draft["residence"].note == "Andalucía"
    # 1.800 × 14 / 12 = 2.100,00 €
    assert draft["net_monthly_income"].value == "2100.00"
    assert draft["net_monthly_income"].note == "1800 € × 14 pagas / 12 meses."
    assert state.issues == []
    assert next_question(state).field == "existing_monthly_debt"


def test_ingresos_al_anio_y_ahorro_en_miles():
    text = "Unos 42.000 al año y tengo 40 mil ahorrados"
    state = run(State(), "net_monthly_income", text, raw(
        income=q("42000", "Unos 42.000 al año"), income_period="año",
        income_period_evidence="al año", savings=q("40000", "tengo 40 mil ahorrados")))
    assert state.draft["net_monthly_income"].value == "3500.00"  # 42.000 / 12
    assert state.draft["available_savings"].value == "40000.00"


def test_la_cita_tiene_que_estar_en_la_respuesta_y_el_numero_en_la_cita():
    text = "Gano bastante, unos dos mil"
    before = State(draft={"birth_year": DraftField("1991", "1991", "respuesta"),
                          "residence": DraftField("ES-13", "Madrid", "calculado")})
    state = run(before, "net_monthly_income", text, raw(
        income=q("2000", "unos dos mil"),  # con letras: no hay número que comprobar
        savings=q("30000", "tengo 30.000 ahorrados")))  # la cita no está en la respuesta
    assert "net_monthly_income" not in state.draft and "available_savings" not in state.draft
    assert "escríbela con cifras" in state.issues[0]
    assert question_text(state).startswith("No lo he entendido.")


def test_sin_deudas_y_sin_hijos_son_cero_y_lista_vacia():
    text = "No tengo ningún préstamo y no tengo hijos"
    state = run(State(), "existing_monthly_debt", text, raw(
        no_debt=True, no_debt_evidence="No tengo ningún préstamo",
        no_children=True, no_children_evidence="no tengo hijos"))
    assert state.draft["existing_monthly_debt"].value == "0"
    assert state.draft["descendant_birth_years"].value == []


def test_un_opcional_sin_respuesta_se_salta_y_un_obligatorio_se_repite():
    state = State(draft={})
    state = run(state, "goal", "Prefiero no decirlo", raw())
    assert "goal" in state.skipped
    state = run(state, "birth_year", "No sé", raw())
    assert next_question(state).field == "birth_year"  # obligatorio: se vuelve a preguntar


def test_comunidad_desde_las_palabras_del_usuario():
    assert region_in("vivo en Castilla y León") == ("ES-07", "Castilla y León")  # no León sola
    assert region_in("en la comunidad de madrid") == ("ES-13", "Comunidad de Madrid")
    assert region_in("vivo en Getafe") is None  # un municipio que no está: se pregunta otra vez
    state = run(State(), "residence", "Vivo en Getafe",
                raw(residence=q("Getafe", "Vivo en Getafe")))
    assert "residence" not in state.draft and "dime el nombre de la comunidad" in state.issues[0]


def test_lo_confirmado_se_valida_sin_mostrar_valores():
    profile = to_profile({"birth_year": "1991", "residence": "ES-13",
                          "net_monthly_income": "2100.00", "existing_monthly_debt": "0",
                          "available_savings": "40000", "descendant_birth_years": ["2019"],
                          "goal": "renta", "horizon_years": ""})
    assert profile.net_monthly_income == Decimal("2100.00")
    assert profile.descendant_birth_years == (2019,) and profile.horizon_years is None
    with pytest.raises(ProfileError) as exc:
        to_profile({"birth_year": "1991", "residence": "Madrid", "net_monthly_income": "-5",
                    "available_savings": "1"})
    assert "residence" in str(exc.value) and "Madrid" not in str(exc.value)


def test_las_preguntas_no_dependen_del_modelo():
    assert [q.field for q in QUESTIONS if q.required] == [
        "birth_year", "residence", "net_monthly_income", "existing_monthly_debt",
        "available_savings"]
    complete = State(draft={f: None for f in (q.field for q in QUESTIONS)})  # type: ignore[misc]
    assert next_question(complete) is None


def test_una_cita_de_la_pregunta_no_vale():
    from housefinder.agent.llm import FakeLLMClient
    from housefinder.agent.profiling import extract_answer

    question = "¿Cuánto ingresas al mes? Si lo sabes en 14 pagas, dímelo así."
    answer = "Unos 2.000 al mes"
    llm = FakeLLMClient(respond=lambda _i, _d, _o: raw(
        income=q("2000", "Unos 2.000 al mes"), income_payments=q("14", "en 14 pagas")))
    checked = extract_answer(llm, question, answer)
    assert checked.verified("income") == Decimal("2000")
    assert checked.fields["income_payments"].status == "rechazado"  # «14 pagas» es de la pregunta
    assert question in llm.calls[0] and answer in llm.calls[0]  # el modelo ve las dos


def test_lista_de_comunidades_para_la_web():
    from fastapi.testclient import TestClient

    from housefinder.api.main import app

    listed = TestClient(app).get("/profile/regions").json()
    assert len(listed) == 19 and {"code": "ES-13", "name": "Comunidad de Madrid"} in listed


def test_lo_que_devolvio_qwen3_no_da_cifras_falsas():
    # Extracciones reales de qwen3:14b (2026-10-31) para estas respuestas
    text = "Tengo 38 años, vivo en Madrid y cobro 2.300 € netos en 14 pagas"
    state = run(State(), "birth_year", text, raw(
        age=q("use the age from the response", "Tengo 38 años"),  # valor basura, cita buena
        residence=q("Madrid", "vivo en Madrid"),
        income=q("2300", "cobro 2.300 € netos en 14 pagas"),
        income_period="año", income_period_evidence="en 14 pagas",  # la cita no dice «año»
        income_payments=q("14", "en 14 pagas")))
    assert state.draft["birth_year"].value == "1988"  # 2026 − 38, desde la cita
    assert state.draft["net_monthly_income"].value == "2683.33"  # 2.300 × 14 / 12, no / 12

    text = "Pago 350 € al mes del préstamo del coche y tengo unos 60 mil ahorrados"
    state = run(state, "existing_monthly_debt", text, raw(
        debt=q(None, "350 € al mes del préstamo del coche"),  # sin valor: sale de la cita
        savings=q(None, "unos 60 mil ahorrados")))
    assert state.draft["existing_monthly_debt"].value == "350.00"
    assert state.draft["available_savings"].value == "60000.00"

    text = "Medio, no me importa algo de riesgo"
    later = run(state, "descendant_birth_years", text, raw(
        no_debt=True, no_debt_evidence=text, no_children=True, no_children_evidence=text))
    assert later.draft["existing_monthly_debt"].value == "350.00"  # no dice «sin deuda»
    assert "descendant_birth_years" not in later.draft

    text = "Sí, dos hijos: uno nació en 2016 y el otro en 2020"
    later = run(state, "descendant_birth_years", text, raw(
        children_birth_years=[q(None, None), q(None, None)]))  # placeholders vacíos
    assert later.draft["descendant_birth_years"].value == ["2016", "2020"]


def test_una_cita_con_varios_numeros_y_sin_valor_no_elige():
    text = "Entre 1.500 y 2.000 según el mes"
    state = run(State(), "net_monthly_income", text, raw(income=q(None, text)))
    assert "net_monthly_income" not in state.draft


def test_otra_respuesta_no_pisa_lo_contestado_ni_cuela_un_anio_imposible():
    before = State(draft={"birth_year": DraftField("1988", "Tengo 38 años", "calculado")})
    text = "Sí, dos hijos: uno nació en 2016 y el otro en 2020"
    state = run(before, "descendant_birth_years", text, raw(
        birth_year=q("2016", "uno nació en 2016"),  # qwen3 lo tomó por el del usuario
        children_birth_years=[q("2016", "uno nació en 2016"), q("2020", "el otro en 2020")]))
    assert state.draft["birth_year"].value == "1988"
    assert state.draft["descendant_birth_years"].value == ["2016", "2020"]
    alone = run(State(), "birth_year", "Nací en 2016", raw(birth_year=q("2016", "Nací en 2016")))
    assert "birth_year" not in alone.draft  # menos de dieciocho años: no es quien invierte


def test_la_opcion_tiene_que_casar_con_la_cita():
    text = "Prefiero delegarlo en una gestora"
    wrong = run(State(), "management", text, raw(management="activa", management_evidence=text))
    assert "management" not in wrong.draft  # la cita dice delegar
    right = run(State(), "management", text, raw(management="pasiva", management_evidence=text))
    assert right.draft["management"].value == "pasiva"
