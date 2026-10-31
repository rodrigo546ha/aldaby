"""El agente escribe referencias a cifras, no cifras (ADR-0012)."""

from decimal import Decimal

import pytest

from housefinder.agent.references import (
    FigureSegment,
    InvalidText,
    TextSegment,
    check_text,
    segments,
    without_numbers,
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
    text = ("Tras impuestos te quedan {{fig:cashflow.monthly_after_tax}}. El m² se estima "
            "entre {{fig:valuation.price_m2:low}} y {{fig:valuation.price_m2:high}}.")
    assert check_text(text, FIGURES) == []
    parts = segments(text, FIGURES)
    assert parts[0] == TextSegment("Tras impuestos te quedan ")
    assert parts[2] == TextSegment(". El m² se estima entre ")
    assert parts[1] == FigureSegment(FIGURES["cashflow.monthly_after_tax"], "value")
    assert parts[3] == FigureSegment(FIGURES["valuation.price_m2"], "low")
    assert parts[-1] == TextSegment(".")
    assert segments("{{fig:valuation.price_m2:range}}", FIGURES) == [
        FigureSegment(FIGURES["valuation.price_m2"], "range")]


@pytest.mark.parametrize("text, kind", [
    ("Te quedan 112 € al mes.", "digito"),  # la cifra copiada a mano
    ("Compra en 2027.", "digito"),  # también años: si importa, es una cifra del plan
    ("La renta del municipio está un … % por debajo.", "digito"),  # copiado de un aviso tapado
    ("Te quedan {{fig:cashflow.monthly_after_tax}}0 al mes.", "digito"),  # pegado al marcador
    ("Unos {{fig:cashflow.annual_tax}} de IRPF.", "clave_desconocida"),
    ("Entre {{fig:cashflow.monthly_after_tax:low}} y más.", "sin_rango"),
    # la web ya escribe «112,40 € al mes»: repetir la unidad la duplica
    ("Te quedan {{fig:cashflow.monthly_after_tax}} al mes.", "unidad_repetida"),
    ("Desde **{{fig:valuation.price_m2:low}}** €/m².", "unidad_repetida"),
    ("Un {{fig:valuation.price_m2}} ratio.", "unidad_repetida"),
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
        "Hay un número escrito a mano («Te quedan 112 € y»): usa un marcador {{fig:clave}} o di "
        "lo mismo sin números.",
        "La cifra «otra.cifra» no está en el plan.",
    ]


def test_cada_numero_es_un_problema():
    problems = check_text("Desde 2023 la población crece; hay 3,5 colegios", FIGURES)
    assert [p.kind for p in problems] == ["digito", "digito"]
    assert "3,5 colegios" in problems[1].message


def test_sin_numeros_para_lo_que_el_modelo_no_puede_citar():
    assert without_numbers("Atlas del INE, año 2024, sección 2806501011 (+6,6 %)") == (
        "Atlas del INE, año …, sección … (+… %)")
