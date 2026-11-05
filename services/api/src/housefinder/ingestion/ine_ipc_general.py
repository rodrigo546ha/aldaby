"""Índice general del IPC del INE por comunidad autónoma (ADR-0061).

Tabla 76136 de la API Tempus (índices por comunidades autónomas: general y de grupos ECOICOP
ver.2), índice general mensual base 2025, la misma familia que el componente de alquiler
(`ine_ipc_alquiler`). Sirve para que los gastos fijos de la TIR (comunidad, IBI y seguro) suban
con los precios de la comunidad. La tabla trae las 19 comunidades a la vez: se cargan todas.

En la tabla, la comunidad y el grupo comparten códigos («13» es Madrid y también un grupo): se
distinguen por la variable de cada metadato (`T3_Variable`).

Licencia: condiciones del INE, citando la fuente.

Uso: `python -m housefinder.ingestion.ine_ipc_general` con `DATABASE_URL`.
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

TABLE = 76136
TEMPUS = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{table}?tip=AM"
TABLE_PAGE = "https://www.ine.es/jaxiT3/Tabla.htm?t={table}"
SOURCE_ID = "ine-ipc-general"
REGION_VARIABLE = "Comunidades y Ciudades Autónomas"
GROUP_VARIABLE, GENERAL = "Grupos ECOICOP", "00"
KIND_VARIABLE, INDEX = "Índices y Tasas", "0"


def parse(payload: list[dict[str, Any]]) -> list[ReferenceRow]:
    """Índice general mensual de cada comunidad; ni el nacional, ni los grupos, ni las tasas."""
    rows = []
    for series in payload:
        meta = {m.get("T3_Variable"): m.get("Codigo") for m in series.get("MetaData", [])}
        region = meta.get(REGION_VARIABLE)
        if not region or meta.get(GROUP_VARIABLE) != GENERAL or meta.get(KIND_VARIABLE) != INDEX:
            continue
        for point in series.get("Data", []):
            period = str(point.get("T3_Periodo", ""))
            if point.get("Valor") is None or not period.startswith("M"):
                continue
            rows.append(ReferenceRow(
                level="comunidad", code=str(region), vintage=None, year=int(point["Anyo"]),
                quarter=0, measure="ipc_general", typology="todas", stat="indice",
                value=Decimal(str(point["Valor"])), unit="índice base 2025",
                month=int(period[1:])))
    return rows


def source_record(payload: list[dict[str, Any]], rows: list[ReferenceRow]) -> SourceRecord:
    first = min((r.year, r.month) for r in rows)
    last = max((r.year, r.month) for r in rows)
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return SourceRecord(
        id=SOURCE_ID,
        name=f"IPC (INE), índice general por comunidad autónoma, tabla {TABLE}",
        url=TABLE_PAGE.format(table=TABLE),
        license=LICENSE,
        fetched_at=datetime.now(UTC),
        notes=(f"{first[0]}-{first[1]:02d}–{last[0]}-{last[1]:02d}; {len(rows)} valores de "
               f"{len({r.code for r in rows})} comunidades; sha256 {digest}. "
               f"Condiciones: {LICENSE_URL}"),
    )


def load(conninfo: str, client: httpx.Client | None = None) -> dict[str, Any]:
    from housefinder.db.references import load_references

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as own:
        # La tabla entera la sirve desde /wstempus/jsCache/: se sigue la redirección.
        response = (client or own).get(TEMPUS.format(table=TABLE), timeout=180,
                                       follow_redirects=True)
        response.raise_for_status()
    payload = response.json()
    rows = parse(payload)
    if not rows:
        raise LookupError("El IPC no trae el índice general de ninguna comunidad")
    loaded, _ = load_references(conninfo, source_record(payload, rows), rows, set(), 0)
    last = max((r.year, r.month) for r in rows)
    return {"loaded": loaded, "regions": len({r.code for r in rows}),
            "last": f"{last[0]}-{last[1]:02d}"}


def main() -> int:
    from housefinder.db.migrate import database_url

    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    result = load(database_url())
    print(f"IPC general: {result['loaded']} índices mensuales de {result['regions']} "
          f"comunidades, último {result['last']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
