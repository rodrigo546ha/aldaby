"""Espera entre reintentos (ADR-0010): 1, 2, 4, 8… minutos, como mucho una hora."""

from __future__ import annotations

from datetime import timedelta

BASE = timedelta(minutes=1)
CAP = timedelta(hours=1)


def backoff(attempt: int) -> timedelta:
    """Espera antes del intento siguiente al número `attempt` (el primero es 1)."""
    if attempt < 1:
        raise ValueError("Los intentos empiezan en 1")
    return min(BASE * 2 ** (attempt - 1), CAP)
