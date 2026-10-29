"""Costes del contrato de alquiler para el arrendador (forma de cálculo; los plazos y las
mensualidades llegan de la normativa resuelta)."""

from __future__ import annotations

from decimal import Decimal

from housefinder.core.figures import money


def non_renewal_compensation(
    flat_months: Decimal,
    months_per_year: Decimal,
    monthly_basis: Decimal,
    years_resided: Decimal,
) -> Decimal:
    """Indemnización por no prorrogar: la mayor de `flat_months` mensualidades o
    `months_per_year` por año de residencia (con la fracción de año prorrateada).

    `monthly_basis`: la mensualidad de referencia que fije la norma.
    """
    if monthly_basis < 0 or years_resided < 0:
        raise ValueError("La mensualidad y los años de residencia no pueden ser negativos")
    months = max(flat_months, months_per_year * years_resided)
    return money(months * monthly_basis)
