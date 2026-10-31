"""Argumentos para no comprar que añade el asesor (F6.7, ADR-0025).

Los argumentos que salen de las cifras los decide el código (`planning/arguments.py`). El modelo
puede añadir hasta tres más, cualitativos. No se pueden comprobar, así que se piden sin números:
el que lleva un dígito o copia un argumento que ya está se descarta (ADR-0012). La web los marca
como del asesor.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence

from pydantic import BaseModel, Field

from housefinder.agent.llm import LLMClient, LLMOutputError
from housefinder.agent.references import check_text

MAX_EXTRA = 3
INSTRUCTIONS = """Eres el asesor de HouseFinder, una plataforma independiente que no vende
inmuebles. El documento describe en palabras, sin cifras, el plan de inversión de un usuario para
una vivienda y los argumentos para no comprarla que ya ha calculado el programa.

Añade como mucho tres argumentos más para pensárselo antes de comprar, que no estén ya en la
lista: riesgos prácticos o de su situación (dedicación, liquidez, concentración, estado del
inmueble, cambios de normativa…). Cada uno en una frase corta, en español, dirigida al usuario.
No escribas ningún número, porcentaje, año ni importe. Si no se te ocurre ninguno sólido, devuelve
la lista vacía."""


class ExtraArguments(BaseModel):
    argumentos: list[str] = Field(default_factory=list, max_length=MAX_EXTRA,
                                  description="Argumentos nuevos, una frase cada uno, sin números")


def extra_arguments(llm: LLMClient, summary: str, given: Sequence[str]) -> list[str]:
    """Los argumentos del modelo que pasan: sin dígitos, sin repetir los del programa."""
    try:
        result = llm.structured(instructions=INSTRUCTIONS, document=summary,
                                output=ExtraArguments)
    except LLMOutputError:
        return []
    seen = {_fold(g) for g in given}
    kept: list[str] = []
    for text in result.argumentos[:MAX_EXTRA]:
        text = text.strip()
        if not text or check_text(text, {}) or _fold(text) in seen:
            continue
        seen.add(_fold(text))
        kept.append(text)
    return kept


def _fold(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in plain if c.isalnum())
