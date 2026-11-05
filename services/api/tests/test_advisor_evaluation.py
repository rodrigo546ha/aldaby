"""Banco del agente (F6.0): mide herramientas, texto mostrado y reintentos sin leer el texto."""

from decimal import Decimal

from housefinder.advisor.evaluation import Case, run_cases, summary
from housefinder.agent.loop import AgentAnswer, Step
from housefinder.agent.references import FigureSegment, TextSegment
from housefinder.core.figures import Figure

RENT = Figure("valuation.rent_monthly", Decimal("839.80"), "EUR/mes", "x")
CASES = (Case("¿Renta de la de {municipio}?", frozenset({"valorar_oferta"})),
         Case("¿Zona de la de {municipio}?", frozenset({"zona_de_oferta"})))


def test_el_banco_mide_cada_caso():
    replies = {
        "¿Renta de la de Getafe?": AgentAnswer(
            [TextSegment("Se alquilaría por "), FigureSegment(RENT, "value")], {}, [],
            [Step("ofertas_guardadas", True), Step("valorar_oferta", True)],
            rejected=[["Hay un número escrito a mano"]]),
        "¿Zona de la de Getafe?": AgentAnswer(
            None, {}, [], [Step("valorar_oferta", True)], failure="texto_rechazado",
            rejected=[["a"], ["b"]]),
    }
    results = run_cases(replies.__getitem__, CASES, "Getafe")
    first, second = results
    assert (first.tools_ok, first.shown, first.first_try) == (True, True, False)
    assert first.text == "Se alquilaría por [valuation.rent_monthly]"
    assert (second.tools_ok, second.shown, second.failure) == (False, False, "texto_rechazado")
    assert second.text == "a | b"
    assert summary(results).startswith(
        "herramientas correctas 1/2 · texto mostrado 1/2 · a la primera 0/2")


def test_cuenta_cifras_fuera_de_marcadores_y_contradicciones():
    cash = Figure("cashflow.monthly_after_tax", Decimal("-36.66"), "EUR/mes", "x")
    replies = {"¿Renta de la de Getafe?": AgentAnswer(
        [TextSegment("Tienes un cash flow positivo de "), FigureSegment(cash, "value"),
         TextSegment(", unos 40 al mes.")], {}, [], [Step("valorar_oferta", True)])}
    result = run_cases(replies.__getitem__, CASES[:1], "Getafe")[0]
    assert result.invented == 2
    assert result.contradictions == (
        "palabra positiva junto a cashflow.monthly_after_tax, que es negativa",)
    assert "cifras fuera de marcadores 2 · contradicciones 1" in summary([result])


def test_nombra_las_ofertas_por_su_titulo():
    from housefinder.agent.references import OfferSegment

    replies = {"¿Renta de la de Getafe?": AgentAnswer(
        [OfferSegment("abcd1234", "Oferta pegada"), TextSegment(" no encaja.")], {}, [],
        [Step("valorar_oferta", True)])}
    assert run_cases(replies.__getitem__, CASES[:1], "Getafe")[0].text == (
        "[oferta Oferta pegada] no encaja.")


def test_las_conversaciones_miden_cada_vuelta_con_el_historial():
    # ADR-0067: vuelve a pedir la herramienta, cita la cifra de lo que se pregunta y habla de la
    # misma oferta; el historial lleva los textos aceptados con sus marcadores
    from housefinder.advisor.evaluation import (
        Conversation,
        Turn,
        conversation_metrics,
        run_conversations,
    )

    zone = "{{fig:oferta_abcd1234.territory.income}}"
    talk = Conversation("Zona y precio", offer=False, turns=(
        Turn("¿Zona de la de {municipio}?", frozenset({"zona_de_oferta"})),
        Turn("¿Y está cara?", frozenset({"valorar_oferta"}),
             keys=frozenset({"valuation.price_total"}), same_offer=True),
    ))
    other = Conversation("Otra oferta", offer=False, turns=(
        Turn("¿Zona?", frozenset({"zona_de_oferta"})),
        Turn("¿Y está cara?", frozenset({"valorar_oferta"}), same_offer=True),
    ))
    replies = {
        "¿Zona de la de Getafe?": AgentAnswer([TextSegment("Renta alta.")], {}, [],
                                              [Step("zona_de_oferta", True)],
                                              text=f"Renta {zone}."),
        "¿Y está cara?": AgentAnswer(
            [TextSegment("Pide más.")], {}, [], [Step("valorar_oferta", True)],
            text="Pide más que {{fig:oferta_abcd1234.valuation.price_total:range}}."),
        "¿Zona?": AgentAnswer([TextSegment("Media.")], {}, [], [Step("zona_de_oferta", True)],
                              text="Media {{fig:oferta_99999999.territory.income}}."),
    }
    seen = []

    def answer(conversation, question, history):
        seen.append(list(history))
        return replies[question]

    results = run_conversations(answer, (talk, other), "Getafe")
    assert seen[1] == [{"role": "user", "content": "¿Zona de la de Getafe?"},
                       {"role": "assistant", "content": f"Renta {zone}."}]
    assert seen[2] == []  # cada conversación empieza sin historial
    first, second, _, fourth = results
    assert (first.keys_ok, first.same_offer) == (None, None)
    assert (second.keys_ok, second.same_offer) == (True, True)  # sin mirar el prefijo de oferta
    assert fourth.same_offer is False  # habla de otra oferta que la de la vuelta anterior
    metrics = conversation_metrics(results)
    assert metrics["vueltas"] == 4 and metrics["herramientas"] == 4
    assert (metrics["con_misma_oferta"], metrics["misma_oferta"]) == (2, 1)
    assert (metrics["con_cifra_pedida"], metrics["cifra_pedida"]) == (1, 1)
