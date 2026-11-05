"""Municipios por su nombre oficial del INE (`data/territory/municipios.yaml`, ADR-0056).

Para elegir un municipio por su nombre en vez de escribir su código («ES-13-28079»), y para
enseñar el nombre oficial de una oferta ubicada («Móstoles», no «MOSTOLES»).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Municipality:
    code: str  # cinco cifras: provincia y municipio
    name: str
    region: str  # comunidad autónoma (código INE)

    @property
    def territory(self) -> str:
        """El territorio de las reglas (core/dated.py): ES-CC-MMMMM."""
        return f"ES-{self.region}-{self.code}"


def default_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "territory" / "municipios.yaml"


@lru_cache
def load_municipalities(path: Path | None = None) -> dict[str, Municipality]:
    data = yaml.safe_load((path or default_path()).read_text(encoding="utf-8"))
    return {str(code): Municipality(str(code), str(v["name"]), str(v["region"]))
            for code, v in data["municipalities"].items()}


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def search(query: str, limit: int = 12,
           municipalities: dict[str, Municipality] | None = None) -> list[Municipality]:
    """Los municipios cuyo nombre contiene todas las palabras de `query`, sin tildes ni mayúsculas.

    Primero los que empiezan por lo escrito y, entre ellos, los de nombre más corto: «madrid» da
    Madrid antes que Las Rozas de Madrid.
    """
    words = fold(query).split()
    if not words:
        return []
    found = []
    for m in (municipalities or load_municipalities()).values():
        name = fold(m.name)
        if all(w in name for w in words):
            starts = any(part.startswith(words[0]) for part in name.split("/"))
            found.append((not starts, len(m.name), m.name, m))
    return [m for *_, m in sorted(found, key=lambda t: t[:3])[:limit]]
