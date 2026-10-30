"""Parámetro de contracción de la renta (ADR-0018)."""

from datetime import date
from decimal import Decimal

from housefinder.params.book import ParamBook, default_params_dir
from housefinder.params.valuation import shrinkage


def test_k_inicial_provisional():
    found = shrinkage(ParamBook.from_dir(default_params_dir()), "ES-13-28079", date(2026, 10, 30))
    assert found.k == Decimal("10")
    assert found.source.kind == "param" and found.source.provisional
