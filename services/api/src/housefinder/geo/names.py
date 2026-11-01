"""Nombres de lugar comparables entre las lenguas oficiales.

Un anuncio escribe «Algimia de Alfara» y el Catastro y el INE, «Algímia d'Alfara»; un anuncio
escribe «Cangas de Narcea» y el Catastro, «CANGAS DEL NARCEA»; el INE escribe «Pobra do Brollón,
A». La clave de un nombre son sus palabras sin mayúsculas, tildes, artículos, preposiciones ni
conjunciones del castellano, el catalán y el valenciano, el gallego y el asturiano. Lo que cambia
entero de una lengua a otra («Donostia» y «San Sebastián») no sale de aquí: lo dan los nombres
dobles del INE y de CartoCiudad («Donostia/San Sebastián»).
"""

from __future__ import annotations

import re
import unicodedata

# Artículos, preposiciones y conjunciones que cambian entre lenguas o entre fuentes.
PARTICLES = frozenset({
    "de", "del", "d", "la", "las", "los", "el", "l", "lo", "les", "els", "es", "sa", "ses", "so",
    "sos", "do", "da", "dos", "das", "o", "a", "os", "as", "y", "i", "e",
})


def place_key(name: str) -> str:
    """«Algímia d'Alfara» y «Algimia de Alfara» → «algimia alfara»."""
    return " ".join(w for w in re.findall(r"[^\W_]+", fold(name)) if w not in PARTICLES)


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())
