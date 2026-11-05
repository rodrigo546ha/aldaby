"""Comunidad autónoma de cada provincia (`data/territory/provincias.yaml`, códigos INE).

Para pasar de la sección censal o el municipio de una oferta al territorio de las reglas y a los
índices que se publican por comunidad (IPV, IPC de alquiler).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


def default_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "territory" / "provincias.yaml"


@lru_cache
def province_regions() -> dict[str, str]:
    """Provincia (dos cifras) → comunidad autónoma (dos cifras)."""
    data: dict[str, Any] = yaml.safe_load(default_path().read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data.items()}


def region_of(municipality_or_province: str) -> str | None:
    """Comunidad de un código de provincia o de municipio (sus dos primeras cifras)."""
    return province_regions().get(municipality_or_province[:2])
