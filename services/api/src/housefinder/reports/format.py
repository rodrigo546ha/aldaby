"""Cifras en español para el PDF, con `Decimal` (ADR-0026): la web formatea en el navegador."""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

CENT = Decimal("0.01")


def number(value: Decimal, decimals: int = 2) -> str:
    """1234567.891 → «1.234.567,89»."""
    quantum = Decimal(1).scaleb(-decimals)
    rounded = value.quantize(quantum, rounding=ROUND_HALF_EVEN)
    sign = "−" if rounded < 0 else ""
    whole, _, frac = f"{abs(rounded):f}".partition(".")
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    text = ".".join(groups)
    return f"{sign}{text},{frac}" if frac else f"{sign}{text}"


def percent(value: Decimal) -> str:
    """Tanto por uno → «4,75 %», con hasta dos decimales y sin ceros de más."""
    text = number(value * 100, 2)
    if "," in text:
        text = text.rstrip("0").rstrip(",")
    return f"{text} %"


def format_value(value: Decimal, unit: str) -> str:
    match unit:
        case "EUR":
            return f"{number(value)} €"
        case "EUR/mes":
            return f"{number(value)} € al mes"
        case "EUR/año":
            return f"{number(value)} € al año"
        case "EUR/m2":
            return f"{number(value)} €/m²"
        case "EUR/m2 mes":
            return f"{number(value)} €/m² al mes"
        case "ratio":
            return percent(value)
        case "años":
            return f"{number(value, 0) if value == value.to_integral() else number(value, 1)} años"
        case _:
            return f"{value} {unit}"
