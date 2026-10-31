"""Tipo medio de las hipotecas sobre viviendas del INE (ADR-0022), solo para contrastar.

Estadística de Hipotecas, tabla 76315 de la API Tempus: tipo de interés medio al inicio de las
hipotecas constituidas sobre viviendas (fijo, variable y total), mensual y nacional. Son hipotecas
ya firmadas, no las nuevas operaciones del Banco de España, que son las que usa el plan.

Licencia: condiciones del INE, citando la fuente. Se guardan en tanto por uno.

Uso: `python -m housefinder.ingestion.ine_hipotecas` con `DATABASE_URL`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from housefinder.db.references import ReferenceRow
from housefinder.db.sections import SourceRecord
from housefinder.ingestion.ine_sections import LICENSE, LICENSE_URL, USER_AGENT

TABLE = 76315
TEMPUS = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{table}?tip=AM"
TABLE_PAGE = "https://www.ine.es/jaxiT3/Tabla.htm?t={table}"
SOURCE_ID = f"ine-hipotecas-{TABLE}"
MEASURE = "tipo_hipotecas_viviendas"
TYPES = {"Fijo": "fijo", "Variable": "variable", "Total": "total"}


def parse(payload: list[dict[str, Any]]) -> list[ReferenceRow]:
    rows = []
    for series in payload:
        names = {m.get("T3_Variable"): m.get("Nombre") for m in series.get("MetaData", [])}
        if names.get("Naturaleza de la finca") != "Viviendas" or \
                names.get("Concepto financiero") != "Tipo de interés medio":
            continue
        kind = TYPES.get(names.get("Tipo de interés", ""))
        if kind is None:
            continue
        for point in series.get("Data", []):
            period = str(point.get("T3_Periodo", ""))
            if point.get("Valor") is None or not period.startswith("M"):
                continue
            rows.append(ReferenceRow(
                level="pais", code="ES", vintage=None, year=int(point["Anyo"]), quarter=0,
                month=int(period[1:]), measure=MEASURE, typology=kind, stat="valor",
                value=Decimal(str(point["Valor"])) / 100, unit="ratio"))
    return rows


def source_record(payload: list[dict[str, Any]], rows: list[ReferenceRow]) -> SourceRecord:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    first = min((r.year, r.month) for r in rows)
    last = max((r.year, r.month) for r in rows)
    return SourceRecord(
        id=SOURCE_ID, name=f"Estadística de Hipotecas (INE): tipo medio de las hipotecas sobre "
                           f"viviendas, tabla {TABLE}",
        url=TABLE_PAGE.format(table=TABLE), license=LICENSE, fetched_at=datetime.now(UTC),
        notes=(f"{first[0]}-{first[1]:02d}–{last[0]}-{last[1]:02d}; {len(rows)} valores; "
               f"sha256 {digest}. Condiciones: {LICENSE_URL}"))


def load(conninfo: str, client: httpx.Client | None = None) -> dict[str, Any]:
    from housefinder.db.references import load_references

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as own:
        response = (client or own).get(TEMPUS.format(table=TABLE), timeout=120,
                                       follow_redirects=True)
        response.raise_for_status()
    payload = response.json()
    rows = parse(payload)
    if not rows:
        raise LookupError("La tabla de hipotecas no trae el tipo medio de las viviendas")
    loaded, _ = load_references(conninfo, source_record(payload, rows), rows, set(), 0)
    last = max((r.year, r.month) for r in rows)
    return {"loaded": loaded, "last": f"{last[0]}-{last[1]:02d}"}


def main() -> int:
    from housefinder.db.migrate import database_url

    result = load(database_url())
    print(f"Hipotecas (INE): {result['loaded']} tipos, último mes {result['last']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
