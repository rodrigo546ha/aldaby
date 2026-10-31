"""Tipos de interés de las nuevas hipotecas del Banco de España (ADR-0022).

Boletín Estadístico, tabla 19.4: TEDR de las nuevas operaciones de crédito a la vivienda de las
entidades de crédito y EFC con hogares, por periodo de fijación inicial del tipo, mensual y
nacional, desde 2003. El tipo de la hipoteca fija del plan es el de más de diez años; la subida del
estrés sale de la misma serie.

Condiciones: se cita al Banco de España como fuente y los datos no se alteran
(https://www.bde.es/wbe/es/pie/aviso-legal/). Se guardan en tanto por uno.

Uso: `python -m housefinder.ingestion.bde_tipos` con `DATABASE_URL`.
"""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from housefinder.db.references import ReferenceRow
from housefinder.db.sections import SourceRecord
from housefinder.ingestion.ine_sections import USER_AGENT

URL = "https://www.bde.es/webbe/es/estadisticas/compartido/datos/csv/be1904.csv"
PAGE = ("https://www.bde.es/webbe/es/estadisticas/otras-clasificaciones/publicaciones/"
        "boletin-estadistico/capitulo-19.html")
SOURCE_ID = "bde-be1904"
LICENSE = "Banco de España, citando la fuente y sin alterar los datos"
MEASURE = "tedr_vivienda_nuevas"
# Código de la serie → periodo de fijación inicial. Una serie que no esté aquí no se carga.
SERIES = {"DN_1TI2T0002": "total", "DN_1TI2T0003": "hasta_1", "DN_1TI2T0004": "1_5",
          "DN_1TI2T0005": "5_10", "DN_1TI2T0006": "mas_10"}
MONTHS = {m: i for i, m in enumerate(
    ("ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"), 1)}


def parse(raw: bytes) -> list[ReferenceRow]:
    rows = list(csv.reader(io.StringIO(raw.decode("latin-1"))))
    codes = rows[0]
    wanted = {i: SERIES[c] for i, c in enumerate(codes) if c in SERIES}
    out = []
    for row in rows:
        month, _, year = (row[0] if row else "").partition(" ")
        if month not in MONTHS or not year.isdigit():
            continue
        for i, band in wanted.items():
            try:
                value = Decimal(row[i]) / 100
            except (InvalidOperation, IndexError):
                continue  # «_»: sin dato ese mes
            out.append(ReferenceRow(level="pais", code="ES", vintage=None, year=int(year),
                                    quarter=0, month=MONTHS[month], measure=MEASURE,
                                    typology=band, stat="valor", value=value, unit="ratio"))
    return out


def source_record(raw: bytes, rows: list[ReferenceRow]) -> SourceRecord:
    first = min((r.year, r.month) for r in rows)
    last = max((r.year, r.month) for r in rows)
    return SourceRecord(
        id=SOURCE_ID, name="Banco de España, Boletín Estadístico 19.4: TEDR de nuevas "
                           "operaciones de crédito a la vivienda por periodo de fijación",
        url=PAGE, license=LICENSE, fetched_at=datetime.now(UTC),
        notes=(f"{first[0]}-{first[1]:02d}–{last[0]}-{last[1]:02d}; {len(rows)} valores; "
               f"sha256 {hashlib.sha256(raw).hexdigest()}. Fichero: {URL}"))


def load(conninfo: str, client: httpx.Client | None = None) -> dict[str, Any]:
    from housefinder.db.references import load_references

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as own:
        response = (client or own).get(URL, timeout=60)
        response.raise_for_status()
    rows = parse(response.content)
    if not rows:
        raise LookupError("El CSV del Banco de España no trae las series de la vivienda")
    loaded, _ = load_references(conninfo, source_record(response.content, rows), rows, set(), 0)
    last = max((r.year, r.month) for r in rows)
    return {"loaded": loaded, "last": f"{last[0]}-{last[1]:02d}"}


def main() -> int:
    from housefinder.db.migrate import database_url

    result = load(database_url())
    print(f"Banco de España: {result['loaded']} tipos, último mes {result['last']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
