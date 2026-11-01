"""Descripción corta del fallo de un servicio de ubicación, sin la URL: lleva lo consultado."""

from __future__ import annotations

import json

import httpx


def failure(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    if isinstance(exc, json.JSONDecodeError):
        return "respuesta que no es JSON"
    return type(exc).__name__
