"""Contradicciones de sentido en el texto del asesor (F6.9, ADR-0027)."""

from decimal import Decimal

from housefinder.agent.references import segments
from housefinder.agent.sense import contradictions
from housefinder.core.figures import Figure

FIGURES = {
    "cashflow.monthly_after_tax": Figure("cashflow.monthly_after_tax", Decimal("-36.66"),
                                         "EUR/mes", "x"),
    "rental.turistico.cashflow": Figure("rental.turistico.cashflow", Decimal("562.87"),
                                        "EUR/mes", "x"),
    "offer.price": Figure("offer.price", Decimal("235000"), "EUR", "x"),
    "affordability.max_price": Figure("affordability.max_price", Decimal("327868.85"), "EUR",
                                      "x"),
}


def rules(text: str) -> list[str]:
    return [c.rule for c in contradictions(segments(text, FIGURES))]


def test_un_texto_correcto_no_tiene_contradicciones():
    assert rules("El cash flow es negativo: {{fig:cashflow.monthly_after_tax}}. El precio, "
                 "{{fig:offer.price}}, queda por debajo de {{fig:affordability.max_price}}.") == []


def test_signo_contrario():
    assert rules("Tendrías un cash flow positivo de {{fig:cashflow.monthly_after_tax}}.") == [
        "palabra positiva junto a cashflow.monthly_after_tax, que es negativa"]
    assert rules("Con el turístico pierdes {{fig:rental.turistico.cashflow}}.") == [
        "palabra negativa junto a rental.turistico.cashflow, que es positiva"]
    # Negado, no contradice
    assert rules("El cash flow no es positivo: {{fig:cashflow.monthly_after_tax}}.") == []


def test_comparacion_falsa():
    assert rules("El precio {{fig:offer.price}} supera tu máximo de "
                 "{{fig:affordability.max_price}}.") == [
        "dice que offer.price supera a affordability.max_price, y no es así"]
    assert rules("Tu máximo {{fig:affordability.max_price}} no llega a "
                 "{{fig:offer.price}}.") == [
        "dice que affordability.max_price queda por debajo de offer.price, y no es así"]


def test_una_frase_por_vez():
    # La palabra de otra frase no cuenta
    assert rules("El plan es positivo en otras cosas. Te queda "
                 "{{fig:cashflow.monthly_after_tax}}.") == []
