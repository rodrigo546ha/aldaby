"""Parámetro de contracción de la renta (ADR-0018)."""

from datetime import date
from decimal import Decimal

from housefinder.params.book import ParamBook, default_params_dir
from housefinder.params.valuation import shrinkage


def test_k_calibrado_con_el_backtesting():
    found = shrinkage(ParamBook.from_dir(default_params_dir()), "ES-13-28079", date(2026, 10, 30))
    assert found.k == Decimal("0")  # sin contracción: F5.6, docs/research/f5-6-backtesting.md
    assert found.source.kind == "param" and not found.source.provisional
