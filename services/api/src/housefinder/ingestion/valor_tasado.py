"""Valor tasado de la vivienda libre por municipio (F5.1, ADR-0018).

Estadística de Valor Tasado de la Vivienda del Ministerio de Vivienda y Agenda Urbana, en la copia
de la Comunidad de Madrid (datos.comunidad.madrid, CSV, CC BY 4.0): €/m² de tasación de vivienda
libre, anual desde 2005, solo municipios de más de 25.000 habitantes. Es tasación, no precio de
compraventa.

El CSV usa el código de municipio de la Comunidad de Madrid: las tres cifras del INE y un dígito de
control («0796» es Madrid, 28079). Un «-» es un año sin dato.

**Sin descarga automática:** el `robots.txt` de datos.comunidad.madrid prohíbe el acceso automático
(`User-agent: *` / `Disallow: /`). Una persona descarga el CSV desde la página del conjunto de datos
(`PAGE`) y este cargador lo lee del disco. El dato es anual: una vez al año.

Uso: `python -m housefinder.ingestion.valor_tasado --fichero ruta.csv` con `DATABASE_URL`.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from housefinder.db.references import ReferenceRow
from housefinder.db.sections import SourceRecord

PAGE = "https://datos.comunidad.madrid/dataset/8cb70b8c-c1e2-43f7-826a-1a22c573a743"
SOURCE_ID = "valor-tasado-comunidad-madrid"
LICENSE = ("CC BY 4.0 (Comunidad de Madrid). Fuente: Estadística de Valor Tasado de la Vivienda, "
           "Ministerio de Vivienda y Agenda Urbana")
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/legalcode.es"
PROVINCE = "28"


def parse(content: bytes) -> tuple[list[ReferenceRow], int]:
    """Filas con valor y cuántas quedan sin dato («-»)."""
    reader = csv.DictReader(io.StringIO(content.decode("latin-1")), delimiter=";")
    rows, empty = [], 0
    for record in reader:
        if record.get("Tipo territorio") != "Municipios":
            continue
        raw = (record.get("Valor") or "").strip()
        try:
            value = Decimal(raw)
        except InvalidOperation:
            empty += 1
            continue
        if record.get("Unidad") != "Euros/m2":
            raise ValueError(f"Unidad inesperada en el valor tasado: {record.get('Unidad')!r}")
        code = record["Código territorio"].strip()
        rows.append(ReferenceRow(
            level="municipio", code=PROVINCE + code[:3], vintage=None,
            year=int(record["Año"]), quarter=0, measure="valor_tasado_m2", typology="todas",
            stat="valor", value=value, unit="EUR/m2"))
    return rows, empty


def source_record(content: bytes, rows: list[ReferenceRow], name: str) -> SourceRecord:
    years = sorted({r.year for r in rows})
    return SourceRecord(
        id=SOURCE_ID,
        name="Valor tasado de la vivienda libre por municipios de más de 25.000 habitantes "
             "(Comunidad de Madrid, datos del Ministerio de Vivienda y Agenda Urbana)",
        url=PAGE,
        license=LICENSE,
        fetched_at=datetime.now(UTC),
        notes=(f"Fichero {name} descargado a mano de {PAGE}; sha256 "
               f"{hashlib.sha256(content).hexdigest()}; años "
               f"{years[0]}–{years[-1]}; {len(rows)} valores. Condiciones: {LICENSE_URL}"),
    )


def load(conninfo: str, path: Path) -> dict[str, Any]:
    """Carga el CSV que una persona ha descargado de `PAGE`. No accede a la red."""
    from housefinder.db.references import load_references

    content = path.read_bytes()
    rows, empty = parse(content)
    if not rows:
        raise LookupError("El CSV del valor tasado no trae valores")
    loaded, _ = load_references(conninfo, source_record(content, rows, path.name), rows, set(),
                                0)
    return {"loaded": loaded, "empty": empty,
            "years": sorted({r.year for r in rows}),
            "municipalities": len({r.code for r in rows})}


def main() -> int:
    from housefinder.db.migrate import database_url

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fichero", type=Path, required=True,
                        help=f"CSV descargado a mano de {PAGE}")
    args = parser.parse_args()
    result = load(database_url(), args.fichero)
    print(f"Valor tasado: {result['loaded']} valores de {result['municipalities']} municipios, "
          f"años {result['years'][0]}–{result['years'][-1]} ({result['empty']} sin dato)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
