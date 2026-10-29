"""Cartografía de secciones censales del INE (F3.2).

Fuente: API OGC Features del INE, capa `Secciones_<año>` (seccionado del Padrón a 1 de
enero). Se filtra por provincia y por `TIPO = 'SECCIONADO'`: la capa incluye también el
contorno de cada distrito (`TIPO = 'DISTRITO'`, sección `000`), que se solapa con sus
secciones y no se carga.

Licencia: CC BY 4.0 según el aviso legal del INE; hay que citar la fuente y la fecha de
actualización. Las coordenadas llegan en longitud/latitud (WGS 84).

Uso: `python -m housefinder.ingestion.ine_sections --year 2025 --province 28` con
`DATABASE_URL`. Repetir la carga actualiza las mismas filas.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from housefinder.db.sections import SectionRow, SourceRecord

API = "https://www.ine.es/geoserver/ogc/features/v1/collections"
LAYER = "WMS_INE_SECCIONES_G01:Secciones_{year}"
SECTION_TYPE = "SECCIONADO"
CODE = re.compile(r"^\d{10}$")
LICENSE = (
    "CC BY 4.0 (aviso legal del INE). Cita: «Elaboración propia con datos extraídos del "
    "sitio web del INE: www.ine.es»"
)
LICENSE_URL = "https://ine.es/dyngs/AYU/index.htm?cid=125"


@dataclass(frozen=True)
class Page:
    sections: list[SectionRow]
    next_url: str | None
    matched: int | None
    skipped: int  # elementos que no son secciones (contornos de distrito)


def collection_url(year: int) -> str:
    return f"{API}/{LAYER.format(year=year)}/items"


def first_page_params(province: str, page_size: int) -> dict[str, str]:
    if not re.fullmatch(r"\d{2}", province):
        raise ValueError(f"Código de provincia no válido: {province!r}")
    return {
        "f": "json",
        "limit": str(page_size),
        "filter-lang": "cql-text",
        "filter": f"CPRO='{province}' AND TIPO='{SECTION_TYPE}'",
    }


def parse_page(payload: dict[str, Any], province: str) -> Page:
    """Secciones de una página de la API, comprobando código, provincia y geometría."""
    sections: list[SectionRow] = []
    skipped = 0
    for feature in payload.get("features", []):
        props = feature.get("properties") or {}
        if props.get("TIPO") != SECTION_TYPE:
            skipped += 1
            continue
        code = str(props.get("CUSEC", ""))
        if not CODE.match(code) or not code.startswith(province) or code.endswith("000"):
            raise ValueError(f"Código de sección no válido: {code!r}")
        if props.get("CUMUN") != code[:5]:
            raise ValueError(f"{code}: el municipio {props.get('CUMUN')!r} no cuadra")
        geometry = feature.get("geometry") or {}
        if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise ValueError(f"{code}: geometría {geometry.get('type')!r} no esperada")
        sections.append(SectionRow(code, code[:5], json.dumps(geometry)))
    next_url = next(
        (link["href"] for link in payload.get("links", []) if link.get("rel") == "next"),
        None,
    )
    return Page(sections, next_url, payload.get("numberMatched"), skipped)


def fetch_sections(
    client: httpx.Client, year: int, province: str, page_size: int = 1000
) -> Iterator[SectionRow]:
    """Todas las secciones de la provincia, siguiendo los enlaces `next`.

    Para si el número de secciones recibidas no cuadra con el que anuncia la API.
    """
    url: str | None = collection_url(year)
    params: dict[str, str] | None = first_page_params(province, page_size)
    matched: int | None = None
    received = 0
    while url is not None:
        response = client.get(url, params=params, timeout=120)
        response.raise_for_status()
        page = parse_page(response.json(), province)
        matched = page.matched if matched is None else matched
        received += len(page.sections) + page.skipped
        yield from page.sections
        url, params = page.next_url, None  # el enlace `next` ya lleva los parámetros
        if not page.sections and not page.skipped:
            break
    if matched is not None and received != matched:
        raise ValueError(f"La API anunció {matched} elementos y llegaron {received}")


def fingerprint(rows: list[SectionRow]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda r: r.code):
        digest.update(row.code.encode())
        digest.update(row.geojson.encode())
    return digest.hexdigest()


def source_record(year: int, province: str, rows: list[SectionRow]) -> SourceRecord:
    return SourceRecord(
        id=f"ine-secciones-{year}-{province}",
        name=f"Cartografía de secciones censales del INE, {year}, provincia {province}",
        url=collection_url(year),
        license=LICENSE,
        fetched_at=datetime.now(UTC),
        notes=(
            f"{len(rows)} secciones (TIPO = {SECTION_TYPE}); sha256 {fingerprint(rows)}. "
            f"Condiciones: {LICENSE_URL}"
        ),
    )


USER_AGENT = "HouseFinder/0.1 (datos abiertos)"


def load(
    year: int, province: str, conninfo: str, client: httpx.Client | None = None
) -> dict[str, Any]:
    """Descarga y carga una cartografía. Idempotente: se puede repetir como trabajo."""
    from housefinder.db.sections import load_sections

    if client is None:
        with httpx.Client(headers={"User-Agent": USER_AGENT}) as own:
            rows = list(fetch_sections(own, year, province))
    else:
        rows = list(fetch_sections(client, year, province))
    source = source_record(year, province, rows)
    total = load_sections(conninfo, source, rows, year, province)
    return {"source": source.id, "loaded": len(rows), "in_database": total}


def main() -> int:
    from housefinder.db.migrate import database_url

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--province", required=True, help="código INE de 2 cifras (28)")
    args = parser.parse_args()
    summary = load(args.year, args.province, database_url())
    print(f"{summary['loaded']} secciones cargadas ({summary['source']}); "
          f"en la base: {summary['in_database']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
