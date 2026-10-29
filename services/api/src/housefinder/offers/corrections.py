"""Correcciones de anuncios del BOE (F4.4): de qué anuncio es cada corrección.

Una corrección cita el anuncio que corrige con el diario, la fecha y, casi siempre, la página:
«Boletín Oficial del Estado núm. 260, de 20 de octubre de 2026 (Sección V-B, pág. 55514)»,
«BOE núm. 249, de 7 de octubre de 2026 (Sec. V-B.Pág.52908)» o «BOE número 261, de fecha 21 de
octubre de 2026». Con el sumario de esa fecha:
1. si hay página, el anuncio es el que la contiene (las páginas son correlativas en el año);
2. si no, el único anuncio de la sección V de ese día del mismo departamento; si hay varios, el
   único que es una venta o subasta, el que comparte el número de expediente o, por último, el
   único cuyo título comparte con la corrección palabras que los demás no tienen («Aragón»).
Sin LLM: si no se resuelve, se dice por qué y la corrección queda sin enlazar.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from housefinder.ingestion.boe import BoeItem

# Correcciones y cambios de una subasta ya publicada: anular o excluir un lote, suspenderla…
CORRECTION = re.compile(
    r"correcci[oó]n|rectificaci[oó]n|subsanaci[oó]n|modificaci[oó]n|anulaci[oó]n|"
    r"exclusi[oó]n|suspensi[oó]n",
    re.IGNORECASE,
)
SALE = re.compile(r"\b(subasta|enajenaci[oó]n|venta)\b", re.IGNORECASE)
MONTHS = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
          "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11,
          "diciembre": 12}
CITATION = re.compile(
    r"(?:Bolet[ií]n Oficial del Estado|«?BOE»?)\s*,?\s*"
    r"(?:n(?:[úu]m(?:ero|\.)?|\.?\s?º)\s*(?P<number>\d+)\s*,?\s*)?"
    r"de\s+(?:fecha\s+)?(?P<day>\d{1,2})\s+de\s+(?P<month>[a-záéíóú]+)\s+de\s+(?P<year>\d{4})"
    r"(?P<tail>.{0,60})",
    re.IGNORECASE,
)
PAGE = re.compile(r"p[áa]g(?:ina)?\.?\s*(\d{3,})", re.IGNORECASE)
WORD = re.compile(r"[a-zñ]{4,}")
FILE_NUMBER = re.compile(r"\b\d{2,}(?:/[\dA-Z]+){1,}\b")


@dataclass(frozen=True)
class Citation:
    published_on: date
    number: int | None
    page: int | None
    text: str


@dataclass(frozen=True)
class Resolution:
    original: BoeItem | None
    method: str  # 'pagina', 'departamento', 'expediente' o el motivo de no resolverla


def is_sale_correction(title: str) -> bool:
    return CORRECTION.search(title) is not None and SALE.search(title) is not None


def parse_citation(text: str, before: date) -> Citation | None:
    """Primera cita a un BOE anterior a la corrección (`before`) con fecha válida."""
    for match in CITATION.finditer(text):
        month = MONTHS.get(match["month"].lower())
        if month is None:
            continue
        try:
            day = date(int(match["year"]), month, int(match["day"]))
        except ValueError:
            continue
        if day >= before:
            continue
        page = PAGE.search(match["tail"])
        return Citation(day, int(match["number"]) if match["number"] else None,
                        int(page.group(1)) if page else None, match.group(0).strip())
    return None


def resolve(
    correction: BoeItem, text: str, citation: Citation, items: Iterable[BoeItem]
) -> Resolution:
    """El anuncio corregido entre los del sumario de la fecha citada."""
    candidates = [i for i in items if i.section.startswith("5")
                  and i.identifier != correction.identifier]
    if citation.page is not None:
        hits = [i for i in candidates if i.pages and i.pages[0] <= citation.page <= i.pages[1]]
        if len(hits) == 1:
            return Resolution(hits[0], "pagina")
        return Resolution(None, f"ningún anuncio de ese día está en la página {citation.page}")
    same = [i for i in candidates if i.department and i.department == correction.department]
    if len(same) == 1:
        return Resolution(same[0], "departamento")
    sales = [i for i in same if SALE.search(i.title)]
    if len(sales) == 1:
        return Resolution(sales[0], "departamento")
    numbers = set(FILE_NUMBER.findall(f"{correction.title} {text}"))
    shared = [i for i in sales if numbers & set(FILE_NUMBER.findall(i.title))]
    if len(shared) == 1:
        return Resolution(shared[0], "expediente")
    by_title = _distinct_title_match(correction.title, sales)
    if by_title is not None:
        return Resolution(by_title, "titulo")
    return Resolution(None, f"{len(sales)} subastas del mismo departamento ese día")


def _distinct_title_match(title: str, candidates: list[BoeItem]) -> BoeItem | None:
    """El único candidato con palabras del título de la corrección que no están en todos."""
    if len(candidates) < 2:
        return None
    words = [set(WORD.findall(_fold(c.title))) for c in candidates]
    common = set.intersection(*words)
    wanted = set(WORD.findall(_fold(title))) - common
    scores = [len(wanted & (w - common)) for w in words]
    best = max(scores)
    if best == 0 or scores.count(best) > 1:
        return None
    return candidates[scores.index(best)]


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))
