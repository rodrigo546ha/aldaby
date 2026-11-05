"""Estado y antigüedad del inmueble: avisos del plan, no descuentos (decisión de Rodrigo,
2026-11-05). Funciones puras.

La renta y el precio estimados son los de una vivienda en el estado habitual de su zona: el
SERPAVI ya mezcla edificios nuevos y viejos. Un descuento por estado o por antigüedad sería un
juicio sin fuente (los coeficientes del Catastro, RD 1020/1993, norma 13, valoran solo la
construcción a efectos catastrales). En su lugar, el plan dice lo que no recoge la valoración y
pide el coste de la reforma, que se suma a la compra.
"""

from __future__ import annotations

import unicodedata
from decimal import Decimal

# Palabras de un anuncio que dicen que la vivienda necesita obra («reformado» no cuenta)
RENOVATION_WORDS = ("a reformar", "para reformar", "necesita reforma", "precisa reforma",
                    "necesita obra", "a rehabilitar", "para rehabilitar", "a actualizar",
                    "para actualizar")


def needs_renovation(condition: str | None) -> bool:
    """Si el estado que da el anuncio dice que hay que reformar."""
    if not condition:
        return False
    text = _fold(condition)
    return any(word in text for word in RENOVATION_WORDS)


def condition_notes(condition: str | None, built_year: int | None, year_source: str,
                    this_year: int, renovation: Decimal) -> list[str]:
    """Avisos del plan sobre el estado (con las palabras del anuncio) y el año del edificio."""
    notes = []
    if needs_renovation(condition):
        if renovation > 0:
            notes.append(f"El anuncio dice «{condition}»: el plan suma la reforma que has "
                         "indicado a la compra y a lo que pones.")
        else:
            notes.append(f"El anuncio dice «{condition}»: la renta y el precio estimados son los "
                         "de una vivienda en el estado habitual de la zona, sin descontar la "
                         "reforma. Indica lo que costaría: se suma a la compra y a lo que pones.")
    if built_year is not None and 1500 < built_year <= this_year:
        notes.append(f"El edificio es de {built_year} ({this_year - built_year} años, según "
                     f"{year_source}). Pide a la comunidad el último informe de inspección "
                     "técnica del edificio, si lo tiene, y las derramas aprobadas o previstas: "
                     "no están en la valoración ni en el plan.")
    return notes


def _fold(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text.lower())
    return " ".join("".join(c for c in plain if not unicodedata.combining(c)).split())
