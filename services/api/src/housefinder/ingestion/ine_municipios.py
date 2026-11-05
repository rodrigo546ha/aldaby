"""Relación de municipios del INE con su código (ADR-0056): nombre oficial de cada municipio.

Fuente: INE, «Relación de municipios y sus códigos por provincias», el diccionario del año
(`https://www.ine.es/daco/daco42/codmun/diccionarioAA.xlsx`), la misma página de la que sale la
relación de provincias (`data/offers/provincias.yaml`). El `robots.txt` del INE permite `/daco/`.

Genera `data/territory/municipios.yaml`: código de cinco cifras → nombre para enseñar y comunidad.
El INE escribe el artículo detrás («Rozas de Madrid, Las»); aquí va delante («Las Rozas de Madrid»).
Los nombres dobles («Alicante/Alacant») se quedan como vienen.

    python -m housefinder.ingestion.ine_municipios --year 2026
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import httpx
import yaml

from housefinder.ingestion.xlsx import iter_rows, sheet_names

URL = "https://www.ine.es/daco/daco42/codmun/diccionario{yy}.xlsx"
USER_AGENT = "HouseFinder/0.1 (datos abiertos)"
SOURCE = "https://www.ine.es/daco/daco42/codmun/codmun_ini.htm"


def default_path() -> Path:
    """services/api/data/territory/municipios.yaml"""
    return Path(__file__).resolve().parents[3] / "data" / "territory" / "municipios.yaml"


def display_name(name: str) -> str:
    """«Rozas de Madrid, Las» → «Las Rozas de Madrid»; «Alicante/Alacant» queda igual. En un nombre
    doble, cada parte por su lado («Coruña, A/Coruña, La» no existe, pero se trataría así)."""
    parts = []
    for part in name.split("/"):
        base, sep, article = part.partition(", ")
        parts.append(f"{article} {base}".strip() if sep and len(article.split()) == 1 else part)
    return "/".join(p.replace("' ", "'") for p in parts)


def parse(path: Path) -> dict[str, dict[str, str]]:
    """Las filas del diccionario: CODAUTO, CPRO, CMUN, DC y NOMBRE (cabecera en la fila 2)."""
    out: dict[str, dict[str, str]] = {}
    for row in iter_rows(path, sheet_names(path)[0], header_row=2):
        cpro, cmun, name = row.get("CPRO"), row.get("CMUN"), row.get("NOMBRE")
        if not (cpro and cmun and name):
            continue
        out[f"{int(cpro):02d}{int(cmun):03d}"] = {
            "name": display_name(name.strip()), "region": f"{int(row['CODAUTO']):02d}"}
    return dict(sorted(out.items()))


def write(municipalities: dict[str, dict[str, str]], year: int, target: Path) -> None:
    header = (
        f"# Generado por `python -m housefinder.ingestion.ine_municipios --year {year}` (ADR-0056):"
        " no editar a mano.\n"
        f"# INE, relación de municipios y sus códigos a 1 de enero de {year} ({SOURCE}).\n"
        "# Código de cinco cifras (provincia y municipio) → nombre con el artículo delante y"
        " comunidad.\n")
    body = yaml.safe_dump({"year": year, "municipalities": municipalities}, allow_unicode=True,
                          sort_keys=False, width=100, default_flow_style=None)
    target.write_text(header + body, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--file", type=Path, help="El diccionario ya descargado")
    args = parser.parse_args()
    if args.file:
        municipalities = parse(args.file)
    else:
        with tempfile.TemporaryDirectory() as tmp, httpx.Client(
                headers={"User-Agent": USER_AGENT}, timeout=60) as client:
            resp = client.get(URL.format(yy=f"{args.year % 100:02d}"))
            resp.raise_for_status()
            local = Path(tmp) / "diccionario.xlsx"
            local.write_bytes(resp.content)
            municipalities = parse(local)
    write(municipalities, args.year, default_path())
    print(f"{len(municipalities)} municipios en {default_path()}")


if __name__ == "__main__":
    main()
