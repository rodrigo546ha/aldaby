"""Gasto medio por hogar en la vivienda, por comunidad autónoma (INE, EPF; ADR-0022).

Encuesta de Presupuestos Familiares, tabla 73993 de la API Tempus (gasto por clases COICOP/EPF y
comunidad): gastos comunitarios (04.4.4), seguros ligados a la vivienda (12.1.3) y mantenimiento y
reparaciones corrientes (04.3.2), en euros al año por hogar. Es la media de todos los hogares,
también los que no tienen ese gasto: como estimación de lo que paga una vivienda, se queda corta.

Licencia: condiciones del INE, citando la fuente.

Uso: `python -m housefinder.ingestion.ine_epf` con `DATABASE_URL`.
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

TABLE = 73993
TEMPUS = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{table}?tip=AM&nult=3"
TABLE_PAGE = "https://www.ine.es/jaxiT3/Tabla.htm?t={table}"
SOURCE_ID = f"ine-epf-{TABLE}"
# Clase COICOP/EPF → medida
CLASSES = {"04.4.4 T": "gasto_comunidad_hogar", "12.1.3 T": "gasto_seguro_vivienda_hogar",
           "04.3.2 T": "gasto_mantenimiento_vivienda_hogar"}


def parse(payload: list[dict[str, Any]]) -> list[ReferenceRow]:
    rows = []
    for series in payload:
        meta = {m.get("T3_Variable"): m for m in series.get("MetaData", [])}
        coicop = (meta.get("Clases COICOP/EPF") or {}).get("Codigo")
        kind = (meta.get("Gastos totales, medios, distribución porcentual e índices sobre la "
                         "media del gasto") or {}).get("Nombre")
        region = meta.get("Comunidades y Ciudades Autónomas") or meta.get("Total Nacional")
        if coicop not in CLASSES or kind != "Gasto medio por hogar" or region is None:
            continue
        level, code = ("pais", "ES") if region.get("Codigo") == "00" else \
            ("comunidad", str(region.get("Codigo")))
        for point in series.get("Data", []):
            if point.get("Valor") is None or point.get("Secreto"):
                continue  # Ceuta y Melilla tienen celdas confidenciales
            rows.append(ReferenceRow(level=level, code=code, vintage=None,
                                     year=int(point["Anyo"]), quarter=0, measure=CLASSES[coicop],
                                     typology="todas", stat="media",
                                     value=Decimal(str(point["Valor"])), unit="EUR/año"))
    return rows


def source_record(payload: list[dict[str, Any]], rows: list[ReferenceRow]) -> SourceRecord:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    years = sorted({r.year for r in rows})
    return SourceRecord(
        id=SOURCE_ID, name=f"Encuesta de Presupuestos Familiares (INE): gasto medio por hogar en "
                           f"la vivienda por comunidad, tabla {TABLE}",
        url=TABLE_PAGE.format(table=TABLE), license=LICENSE, fetched_at=datetime.now(UTC),
        notes=(f"{years[0]}–{years[-1]}; {len(rows)} valores; sha256 {digest}. Condiciones: "
               f"{LICENSE_URL}"))


def load(conninfo: str, client: httpx.Client | None = None) -> dict[str, Any]:
    from housefinder.db.references import load_references

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as own:
        response = (client or own).get(TEMPUS.format(table=TABLE), timeout=180,
                                       follow_redirects=True)
        response.raise_for_status()
    payload = response.json()
    rows = parse(payload)
    if not rows:
        raise LookupError("La EPF no trae los gastos de la vivienda por comunidad")
    loaded, _ = load_references(conninfo, source_record(payload, rows), rows, set(), 0)
    return {"loaded": loaded, "last": max(r.year for r in rows)}


def main() -> int:
    from housefinder.db.migrate import database_url

    result = load(database_url())
    print(f"EPF: {result['loaded']} gastos medios, último año {result['last']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
