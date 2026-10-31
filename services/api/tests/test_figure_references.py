"""El agente escribe referencias a cifras, no cifras (ADR-0012)."""

from decimal import Decimal

import pytest

from housefinder.agent.references import (
    FigureSegment,
    InvalidText,
    TextSegment,
    check_text,
    segments,
)
from housefinder.core.figures import Figure

D = Decimal
FIGURES = {
    "cashflow.monthly_after_tax": Figure("cashflow.monthly_after_tax", D("112.40"), "EUR/mes",
                                         "renta − gastos − cuota − IRPF"),
    "valuation.price_m2": Figure("valuation.price_m2", D("2806.45"), "EUR/m2", "renta × relación",
                                 low=D("2400.78"), high=D("3466.44")),
}


def test_texto_con_marcadores_validos():
    text = ("Tras impuestos te quedan {{fig:cashflow.monthly_after_tax}} al mes. El m² se estima "
            "entre {{fig:valuation.price_m2:low}} y {{fig:valuation.price_m2:high}}.")
    assert check_text(text, FIGURES) == []
    parts = segments(text, FIGURES)
    assert parts[0] == TextSegment("Tras impuestos te quedan ")
    assert parts[1] == FigureSegment(FIGURES["cashflow.monthly_after_tax"], "value")
    assert parts[3] == FigureSegment(FIGURES["valuation.price_m2"], "low")
    assert parts[-1] == TextSegment(".")
    assert segments("{{fig:valuation.price_m2:range}}", FIGURES) == [
        FigureSegment(FIGURES["valuation.price_m2"], "range")]


@pytest.mark.parametrize("text, kind", [
    ("Te quedan 112 € al mes.", "digito"),  # la cifra copiada a mano
    ("Compra en 2027.", "digito"),  # también años: si importa, es una cifra del plan
    ("Te quedan {{fig:cashflow.monthly_after_tax}}0 al mes.", "digito"),  # pegado al marcador
    ("Unos {{fig:cashflow.annual_tax}} de IRPF.", "clave_desconocida"),
    ("Entre {{fig:cashflow.monthly_after_tax:low}} y más.", "sin_rango"),
    ("Te quedan {{fig: cashflow.monthly_after_tax}}.", "marcador_mal_escrito"),
    ("Te quedan {fig:cashflow.monthly_after_tax}}.", "marcador_mal_escrito"),
    ("{{cifra:cashflow.monthly_after_tax}}", "marcador_mal_escrito"),
])
def test_textos_rechazados(text, kind):
    problems = check_text(text, FIGURES)
    assert kind in {p.kind for p in problems}
    with pytest.raises(InvalidText) as exc:
        segments(text, FIGURES)
    assert exc.value.problems == problems


def test_los_problemas_se_pueden_devolver_al_modelo():
    problems = check_text("Te quedan 112 € y {{fig:otra.cifra}}.", FIGURES)
    messages = [p.message for p in problems]
    assert messages == [
        "Hay un número escrito a mano («Te quedan 112 € y»): usa un marcador {{fig:clave}}.",
        "La cifra «otra.cifra» no está en el plan.",
    ]
