"""Textos legales como datos (ADR-0039).

Cada documento es un Markdown de `data/legal/` con su cabecera YAML (versión, fecha, si hay que
aceptarlo y si lo ha revisado el abogado). Los huecos `{{campo}}` se rellenan con
`data/legal/titular.yaml`; un campo vacío sale como «[pendiente: …]», nunca inventado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

PLACEHOLDER = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")
FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
LABELS = {
    "servicio": "nombre del servicio", "titular": "razón social del titular", "nif": "NIF",
    "domicilio": "domicilio", "registro": "datos registrales", "correo": "correo de contacto",
    "web": "dominio", "alojamiento": "proveedor de alojamiento",
    "plazo_copias": "plazo de conservación de las copias",
}


@dataclass(frozen=True)
class LegalDocument:
    id: str
    title: str
    version: int
    effective_from: date
    requires_acceptance: bool
    verified: bool
    text: str  # Markdown con los huecos ya rellenos
    missing: tuple[str, ...]  # campos del titular que faltan


def default_dir() -> Path:
    """services/api/data/legal"""
    return Path(__file__).resolve().parents[3] / "data" / "legal"


def fill(text: str, holder: dict[str, object]) -> tuple[str, tuple[str, ...]]:
    missing: list[str] = []

    def value(match: re.Match[str]) -> str:
        key = match.group(1)
        found = holder.get(key)
        if found in (None, ""):
            if key not in missing:
                missing.append(key)
            return f"[pendiente: {LABELS.get(key, key)}]"
        return str(found)

    return PLACEHOLDER.sub(value, text), tuple(missing)


def parse(content: str, holder: dict[str, object]) -> LegalDocument:
    head = FRONT_MATTER.match(content)
    if head is None:
        raise ValueError("Falta la cabecera YAML del documento legal")
    meta = yaml.safe_load(head.group(1))
    text, missing = fill(content[head.end():].strip(), holder)
    title, _ = fill(str(meta["title"]), holder)
    return LegalDocument(
        id=str(meta["id"]), title=title, version=int(meta["version"]),
        effective_from=meta["effective_from"],
        requires_acceptance=bool(meta["requires_acceptance"]),
        verified=bool(meta.get("verified", False)), text=text, missing=missing,
    )


@lru_cache
def load(directory: Path | None = None) -> dict[str, LegalDocument]:
    folder = directory or default_dir()
    holder = yaml.safe_load((folder / "titular.yaml").read_text(encoding="utf-8")) or {}
    documents = {}
    for path in sorted(folder.glob("*.md")):
        doc = parse(path.read_text(encoding="utf-8"), holder)
        if doc.id != path.stem:
            raise ValueError(f"{path.name}: el id {doc.id!r} no coincide con el nombre del fichero")
        documents[doc.id] = doc
    return documents


def to_accept(documents: dict[str, LegalDocument]) -> dict[str, int]:
    """Versión vigente de cada documento que hay que aceptar."""
    return {d.id: d.version for d in documents.values() if d.requires_acceptance}


def pending(documents: dict[str, LegalDocument], accepted: dict[str, int]) -> list[str]:
    """Los documentos cuya versión vigente la cuenta aún no ha aceptado."""
    return [doc for doc, version in to_accept(documents).items() if accepted.get(doc) != version]
