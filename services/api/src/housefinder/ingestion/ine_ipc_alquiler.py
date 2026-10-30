"""Componente de alquiler de vivienda del IPC del INE por comunidad autónoma (ADR-0018).

Tabla 76137 de la API Tempus (índices por comunidades autónomas de subgrupos ECOICOP ver.2),
subgrupo 04.1 «Alquiler de vivienda», índice mensual base 2025. Mide los alquileres en vigor, como
el SERPAVI: sirve para llevar la renta declarada del último año del SERPAVI al último mes publicado.
En el backtesting (F5.6) reduce el error de una renta de dos años del 7,9 % al 4,2 %; sigue
quedándose corta un 4 % en los años recientes.

Licencia: condiciones del INE, citando la fuente.

Uso: `python -m housefinder.ingestion.ine_ipc_alquiler --region 13` con `DATABASE_URL`.
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

TABLE = 76137
TEMPUS = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{table}?tip=AM"
TABLE_PAGE = "https://www.ine.es/jaxiT3/Tabla.htm?t={table}"
SOURCE_ID = "ine-ipc-alquiler"
SUBGROUP = "04.1"  # Alquiler de vivienda
INDEX = "Índice"


def parse(payload: list[dict[str, Any]], region: str) -> list[ReferenceRow]:
    rows = []
    for series in payload:
        meta = series.get("MetaData", [])
        codes = {m.get("Codigo", "") for m in meta}
        names = {m.get("Nombre", "") for m in meta}
        if region not in codes or SUBGROUP not in codes or INDEX not in names:
            continue
        for point in series.get("Data", []):
            period = str(point.get("T3_Periodo", ""))
            if point.get("Valor") is None or not period.startswith("M"):
                continue
            rows.append(ReferenceRow(
                level="comunidad", code=region, vintage=None, year=int(point["Anyo"]), quarter=0,
                measure="ipc_alquiler", typology="todas", stat="indice",
                value=Decimal(str(point["Valor"])), unit="índice base 2025",
                month=int(period[1:])))
    return rows


def source_record(payload: list[dict[str, Any]], rows: list[ReferenceRow]) -> SourceRecord:
    first = min((r.year, r.month) for r in rows)
    last = max((r.year, r.month) for r in rows)
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return SourceRecord(
        id=SOURCE_ID,
        name=f"IPC (INE), subgrupo 04.1 Alquiler de vivienda por comunidad autónoma, tabla {TABLE}",
        url=TABLE_PAGE.format(table=TABLE),
        license=LICENSE,
        fetched_at=datetime.now(UTC),
        notes=(f"{first[0]}-{first[1]:02d}–{last[0]}-{last[1]:02d}; {len(rows)} valores; "
               f"sha256 {digest}. Condiciones: {LICENSE_URL}"),
    )


def load(region: str, conninfo: str, client: httpx.Client | None = None) -> dict[str, Any]:
    from housefinder.db.references import load_references

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as own:
        # La tabla entera la sirve desde /wstempus/jsCache/: se sigue la redirección.
        response = (client or own).get(TEMPUS.format(table=TABLE), timeout=180,
                                       follow_redirects=True)
        response.raise_for_status()
    payload = response.json()
    rows = parse(payload, region)
    if not rows:
        raise LookupError(f"El IPC no trae el alquiler de vivienda de la comunidad {region}")
    loaded, _ = load_references(conninfo, source_record(payload, rows), rows, set(), 0)
    last = max((r.year, r.month) for r in rows)
    return {"loaded": loaded, "last": f"{last[0]}-{last[1]:02d}"}


def main() -> int:
    from housefinder.db.migrate import database_url

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--region", required=True, help="código INE de la comunidad (13)")
    args = parser.parse_args()
    result = load(args.region, database_url())
    print(f"IPC alquiler: {result['loaded']} índices mensuales, último {result['last']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
