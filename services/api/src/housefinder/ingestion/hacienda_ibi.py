"""Tipo del IBI urbano de cada municipio, del Ministerio de Hacienda (ADR-0022).

PDF anual «Tipos de gravamen, índices y coeficientes» de la Oficina Virtual para la Coordinación
Financiera con las Entidades Locales, por comunidad. El tipo del IBI es normativa: no va a la base
sino a reglas `tipo_ibi` en `data/rules/ibi_hacienda_{año}.yaml`, sin verificar y con el PDF como
fuente (ADR-0003). Un municipio que ya tiene su regla (Madrid, de su ordenanza) no se toca.

Condiciones: reutilización «para fines comerciales y no comerciales», citando la fuente
(https://www.hacienda.gob.es/es-ES/Paginas/Avisolegal.aspx).

Uso: `python -m housefinder.ingestion.hacienda_ibi --year 2026` (las 17 comunidades de régimen
común; Navarra y el País Vasco no están: régimen foral) o `--region MADRID` para una sola. El PDF
solo trae los municipios de más de 1.000 habitantes.
"""

from __future__ import annotations

import argparse
import io
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

import httpx
import yaml

from housefinder.ingestion.ine_sections import USER_AGENT

URL = ("https://serviciostelematicosext.hacienda.gob.es/SGFAL/ConsultaTipos/aspx/descargaPDF.aspx"
       "?URLPDF={path}")
# Carpeta y fichero de cada comunidad, como los enlaza el libro completo del año
# (`{año}/COMPLETO/Imposicion.pdf`); no siguen un patrón. Código INE de la comunidad.
REGIONS: dict[str, tuple[str, str]] = {
    "ANDALUCIA": ("Andalucia.pdf", "01"), "ARAGON": ("Aragon.pdf", "02"),
    "ASTURIAS": ("Asturias.pdf", "03"), "ILLES BALEARS": ("Illes Balears.pdf", "04"),
    "CANARIAS": ("Canarias.pdf", "05"), "CANTABRIA": ("Cantabria.pdf", "06"),
    "CASTILLA-LEON": ("Castilla-Leon.pdf", "07"), "CASTILLA-MANCHA": ("Castilla-Mancha.pdf", "08"),
    "CATALUÑA": ("Cataluña.pdf", "09"), "C.VALENCIANA": ("C.Valenciana.pdf", "10"),
    "EXTREMADURA": ("Extremadura.pdf", "11"), "GALICIA": ("Galicia.pdf", "12"),
    "MADRID": ("Madrid.pdf", "13"), "MURCIA": ("Murcia.pdf", "14"), "RIOJA": ("Rioja.pdf", "17"),
    "CEUTA": ("Ceuta.pdf", "18"), "MELILLA": ("Melilla.pdf", "19"),
}
# Primera tabla del PDF: código, municipio, año de la última revisión catastral y tipo urbano
ROW = re.compile(r"^\s*(\d{2})-(\d{3})\s+(.+?)\s+(\d{4})\s+(\d+,\d{5})\s")


@dataclass(frozen=True)
class MunicipalRate:
    code: str  # código INE del municipio (28065)
    name: str
    revision_year: int
    rate: Decimal  # en tanto por uno


def parse(text: str) -> list[MunicipalRate]:
    """La primera aparición de cada municipio con año y tipo de cinco decimales: la del IBI."""
    found: dict[str, MunicipalRate] = {}
    for line in text.splitlines():
        match = ROW.match(line)
        if match and (code := match.group(1) + match.group(2)) not in found:
            found[code] = MunicipalRate(code, match.group(3).strip(), int(match.group(4)),
                                        Decimal(match.group(5).replace(",", ".")) / 100)
    return list(found.values())


def pdf_text(content: bytes) -> str:
    from pypdf import PdfReader

    return "\n".join(page.extract_text(extraction_mode="layout") or ""
                     for page in PdfReader(io.BytesIO(content)).pages)


def rules(rates: list[MunicipalRate], year: int, ccaa: str, url: str,
          existing: set[str]) -> list[dict[str, object]]:
    out = []
    for r in sorted(rates, key=lambda r: r.code):
        territory = f"ES-{ccaa}-{r.code}"
        if territory in existing:
            continue
        out.append({
            "id": f"ibi-{r.code}-{year}", "kind": "tipo_ibi", "territory": territory,
            "effective_from": f"{year}-01-01", "effective_to": f"{year}-12-31",
            "status": "vigente", "verified": False,
            "params": {"rate": float(r.rate)}, "source_url": url,
            "notes": (f"{r.name}: tipo del IBI urbano {year} según el Ministerio de Hacienda "
                      f"(Oficina Virtual EELL), última revisión catastral {r.revision_year}."),
        })
    return out


def existing_territories(rules_dir: Path) -> set[str]:
    """Municipios con su propia regla del IBI fuera del fichero generado."""
    found = set()
    for path in rules_dir.glob("*.yaml"):
        if path.name.startswith("ibi_hacienda_"):
            continue
        for rule in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            if isinstance(rule, dict) and rule.get("kind") == "tipo_ibi":
                found.add(str(rule["territory"]))
    return found


def rules_dir() -> Path:
    """services/api/data/rules (sin importar regulation/: la ingesta no depende de ella)."""
    return Path(__file__).resolve().parents[3] / "data" / "rules"


def region_url(year: int, region: str) -> str:
    filename, _ = REGIONS[region]
    return URL.format(path=quote(f"{year}/{region}/{filename}", safe=""))


def main() -> int:
    import time

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--region", choices=sorted(REGIONS),
                        help="una sola comunidad (carpeta del PDF); sin ella, todas")
    args = parser.parse_args()
    regions = [args.region] if args.region else list(REGIONS)
    folder = rules_dir()
    existing = existing_territories(folder)
    generated: list[dict[str, object]] = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for region in regions:
            url = region_url(args.year, region)
            response = client.get(url, timeout=120)
            response.raise_for_status()
            rates = parse(pdf_text(response.content))
            generated += rules(rates, args.year, REGIONS[region][1], url, existing)
            print(f"IBI {args.year} {region}: {len(rates)} municipios")
            time.sleep(1)
    target = folder / f"ibi_hacienda_{args.year}.yaml"
    which = f"--region {args.region}" if args.region else "(todas las comunidades)"
    header = (f"# Generado por `python -m housefinder.ingestion.hacienda_ibi --year {args.year}` "
              f"{which} (ADR-0022): no editar a mano.\n"
              f"# Tipo del IBI urbano por municipio, Ministerio de Hacienda. Sin verificar.\n")
    target.write_text(header + yaml.safe_dump(generated, allow_unicode=True, sort_keys=False),
                      encoding="utf-8")
    print(f"{len(generated)} reglas en {target.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
