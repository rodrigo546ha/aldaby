"""Índice de Precios de Vivienda del INE por comunidad autónoma (F5.5, ADR-0018).

Tabla 80270 de la API Tempus del INE: índice trimestral (base 2025) de los precios escriturados,
general, vivienda nueva y de segunda mano, por comunidad autónoma. Sirve para llevar una
referencia de precio de un año al último trimestre publicado, no para comparar zonas.

Licencia: condiciones del INE, citando la fuente (como el resto de cargas del INE).

Uso: `python -m housefinder.ingestion.ine_ipv --region 13` con `DATABASE_URL`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from housefinder.db.references import ReferenceRow
from housefinder.db.sections import SourceRecord
from housefinder.ingestion.ine_sections import LICENSE, LICENSE_URL, USER_AGENT

TABLE = 80270
TEMPUS = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{table}?tip=AM"
TABLE_PAGE = "https://www.ine.es/jaxiT3/Tabla.htm?t={table}"
SOURCE_ID = f"ine-ipv-{TABLE}"
# Nombre del INE → tipología. Un nombre que no esté aquí no se carga: no se adivina.
TYPOLOGIES = {"General": "todas", "Vivienda nueva": "nueva",
              "Vivienda segunda mano": "segunda_mano"}
QUARTERS = {"T1": 1, "T2": 2, "T3": 3, "T4": 4}


def parse(payload: list[dict[str, Any]], region: str) -> list[ReferenceRow]:
    rows = []
    for series in payload:
        names = [m.get("Nombre", "") for m in series.get("MetaData", [])]
        codes = [m.get("Codigo", "") for m in series.get("MetaData", [])]
        if region not in codes or "Índice" not in names:
            continue
        typology = next((TYPOLOGIES[n] for n in names if n in TYPOLOGIES), None)
        if typology is None:
            continue
        for point in series.get("Data", []):
            if point.get("Valor") is None or point.get("T3_Periodo") not in QUARTERS:
                continue
            rows.append(ReferenceRow(
                level="comunidad", code=region, vintage=None, year=int(point["Anyo"]),
                quarter=QUARTERS[point["T3_Periodo"]], measure="ipv", typology=typology,
                stat="indice", value=Decimal(str(point["Valor"])), unit="índice base 2025"))
    return rows


def source_record(payload: list[dict[str, Any]], rows: list[ReferenceRow]) -> SourceRecord:
    periods = sorted((r.year, r.quarter) for r in rows)
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    first, last = periods[0], periods[-1]
    return SourceRecord(
        id=SOURCE_ID,
        name=f"Índice de Precios de Vivienda (INE), por comunidad autónoma, tabla {TABLE}",
        url=TABLE_PAGE.format(table=TABLE),
        license=LICENSE,
        fetched_at=datetime.now(UTC),
        notes=(f"{first[0]}T{first[1]}–{last[0]}T{last[1]}; {len(rows)} valores; sha256 {digest}. "
               f"Condiciones: {LICENSE_URL}"),
    )


def load(region: str, conninfo: str, client: httpx.Client | None = None) -> dict[str, Any]:
    from housefinder.db.references import load_references

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as own:
        # La tabla entera la sirve desde /wstempus/jsCache/: se sigue la redirección.
        response = (client or own).get(TEMPUS.format(table=TABLE), timeout=120,
                                       follow_redirects=True)
        response.raise_for_status()
    payload = response.json()
    rows = parse(payload, region)
    if not rows:
        raise LookupError(f"El IPV no trae índices para la comunidad {region}")
    loaded, _ = load_references(conninfo, source_record(payload, rows), rows, set(), 0)
    last = max((r.year, r.quarter) for r in rows)
    return {"loaded": loaded, "last": f"{last[0]}T{last[1]}"}


def main() -> int:
    from housefinder.db.migrate import database_url

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--region", required=True, help="código INE de la comunidad (13)")
    args = parser.parse_args()
    result = load(args.region, database_url())
    print(f"IPV: {result['loaded']} índices, último trimestre {result['last']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
