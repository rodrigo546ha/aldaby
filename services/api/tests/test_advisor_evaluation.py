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
