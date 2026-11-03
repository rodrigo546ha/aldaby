"""Tipo y coeficientes de la plusvalía municipal de cada municipio, del Ministerio de Hacienda.

Mismo PDF anual que el IBI (`hacienda_ibi`, ADR-0022): su tercera parte, «Impuesto sobre el
incremento del valor de los terrenos de naturaleza urbana», trae para los municipios de más de
1.000 habitantes que tienen establecido el impuesto dos tablas de 21 periodos de generación
(menos de un año, 1… 19 años y 20 o más): los coeficientes sobre la base imponible y el tipo de
gravamen. Van a reglas `tipo_plusvalia` y `coeficientes_plusvalia` sin verificar en
`data/rules/plusvalia_hacienda.yaml` (ADR-0044):

- El tipo, único si es igual en los 21 periodos y por años de tenencia si no (TRLRHL, art. 108.1).
- Los coeficientes, solo si no son los máximos legales vigentes: el municipio que aplica los
  máximos sigue a la regla de `ES` cuando cambien.
- Un municipio de la tabla del IBI (todos los de más de 1.000 habitantes) que no está en la de
  la plusvalía no tiene establecido el impuesto: tipo 0.

La plusvalía se calcula a la fecha de venta del plan, años después: las reglas rigen desde el 1 de
enero del año del libro y sin fin, y el fichero se rehace entero con el libro de cada año. Un
municipio con su regla en otro fichero (de su ordenanza) no se toca; se avisa si no coincide.
La bonificación del 50 % de Ceuta y Melilla va en reglas propias (ADR-0045).

Uso: `python -m housefinder.ingestion.hacienda_plusvalia --year 2026`.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import yaml

from housefinder.ingestion.hacienda_ibi import REGIONS, pdf_text, region_url, rules_dir
from housefinder.ingestion.hacienda_ibi import parse as parse_ibi
from housefinder.ingestion.ine_sections import USER_AGENT

GENERATED = "plusvalia_hacienda.yaml"
PERIODS = 21  # menos de un año, 1… 19 años y 20 o más
HUNDRED = Decimal(100)

# Cabecera de cada página: «IMPUESTO SOBRE EL INCREMENTO DEL VALOR DE …», «IMPUESTOS SOBRE BIENES
# INMUEBLES…». La numeración de las partes («3.M») no está en todos los PDF (Ceuta).
HEADING = re.compile(r"^IMPUESTOS? SOBRE ")
ROW = re.compile(r"^\s*(\d{2})-(\d{3})\s+(.*?)\s+((?:\d+,\d{2}\s*){22})\s*$")
NUMBER = re.compile(r"\d+,\d{2}")


@dataclass(frozen=True)
class MunicipalGains:
    code: str  # código INE del municipio (28079)
    name: str
    coefficients: tuple[Decimal, ...]  # 21 periodos
    rates: tuple[Decimal, ...]  # 21 periodos, en tanto por uno
    reduction: Decimal  # columna «Porc. reducc.» de los coeficientes, tal cual (no se modela)


def parse(text: str) -> list[MunicipalGains]:
    """Municipios con las dos tablas de la parte de la plusvalía del PDF."""
    in_gains = False
    table = None
    coefficients: dict[str, tuple[str, tuple[Decimal, ...], Decimal]] = {}
    rates: dict[str, tuple[Decimal, ...]] = {}
    for line in text.splitlines():
        if HEADING.match(line):
            in_gains, table = "INCREMENTO DEL VALOR" in line, None
            continue
        if not in_gains:
            continue
        if "Coeficiente sobre la Base" in line:
            table = "coef"
        elif "Tipo de Gravamen" in line:
            table = "tipo"
        elif table and (row := ROW.match(line)):
            code = row.group(1) + row.group(2)
            values = [Decimal(v.replace(",", ".")) for v in NUMBER.findall(row.group(4))]
            if table == "coef":
                coefficients.setdefault(code, (row.group(3).strip(), tuple(values[:PERIODS]),
                                               values[PERIODS]))
            else:
                rates.setdefault(code, tuple(v / HUNDRED for v in values[:PERIODS]))
    if missing := set(coefficients) ^ set(rates):
        raise ValueError(f"Municipios con una sola de las dos tablas: {sorted(missing)}")
    return [MunicipalGains(code, name, coefs, rates[code], reduction)
            for code, (name, coefs, reduction) in sorted(coefficients.items())]


def rate_params(rates: tuple[Decimal, ...]) -> dict[str, object]:
    """`rate` si es igual en todos los periodos; si no, un paso por cada cambio de tipo."""
    if len(set(rates)) == 1:
        return {"rate": float(rates[0])}
    steps = [{"from_years": years, "rate": float(rate)} for years, rate in enumerate(rates)
             if years == 0 or rate != rates[years - 1]]
    return {"by_years": steps}


def rules(found: list[MunicipalGains], without_tax: list[tuple[str, str]], year: int, ccaa: str,
          url: str, existing: dict[str, set[str]],
          maximums: tuple[Decimal, ...]) -> list[dict[str, object]]:
    """Reglas de una comunidad. `without_tax`: (código, nombre) de los que no lo tienen."""
    common = {"effective_from": f"{year}-01-01", "effective_to": None, "status": "vigente",
              "verified": False, "source_url": url}
    source = f"según el Ministerio de Hacienda (Oficina Virtual EELL), libro de {year}"
    out: list[dict[str, object]] = []
    for m in found:
        territory = f"ES-{ccaa}-{m.code}"
        if territory not in existing["tipo_plusvalia"]:
            note = f"{m.name}: tipo de gravamen de la plusvalía municipal {source}."
            if m.reduction:
                note += (f" La tabla de coeficientes trae además «Porc. reducc.» {m.reduction}, "
                         "que no se modela.")
            out.append({"id": f"plusvalia-tipo-{m.code}", "kind": "tipo_plusvalia",
                        "territory": territory, **common, "params": rate_params(m.rates),
                        "notes": note})
        if (m.coefficients != maximums
                and territory not in existing["coeficientes_plusvalia"]):
            out.append({"id": f"plusvalia-coeficientes-{m.code}", "kind": "coeficientes_plusvalia",
                        "territory": territory, **common,
                        "params": {"by_years": [float(c) for c in m.coefficients]},
                        "notes": (f"{m.name}: coeficientes propios {source}; donde pasen del "
                                  "máximo legal se aplica el máximo (TRLRHL, art. 107.4).")})
    for code, name in without_tax:
        territory = f"ES-{ccaa}-{code}"
        if territory in existing["tipo_plusvalia"]:
            continue
        out.append({"id": f"plusvalia-tipo-{code}", "kind": "tipo_plusvalia",
                    "territory": territory, **common, "params": {"rate": 0.0},
                    "notes": (f"{name}: no figura entre los municipios de más de 1.000 habitantes "
                              f"que tienen establecido el impuesto {source}: sin plusvalía.")})
    return sorted(out, key=lambda r: (str(r["territory"]), str(r["kind"])))


def existing_territories(folder: Path) -> dict[str, set[str]]:
    """Municipios con regla propia de tipo o de coeficientes fuera del fichero generado."""
    found: dict[str, set[str]] = {"tipo_plusvalia": set(), "coeficientes_plusvalia": set()}
    for path in folder.glob("*.yaml"):
        if path.name == GENERATED:
            continue
        for rule in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            if isinstance(rule, dict) and rule.get("kind") in found:
                found[str(rule["kind"])].add(str(rule["territory"]))
    return found


def legal_maximums(folder: Path, on: date) -> tuple[Decimal, ...]:
    """Coeficientes máximos vigentes en `on`: la regla `coeficientes_plusvalia` de `ES`."""
    for path in folder.glob("*.yaml"):
        for rule in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            if (isinstance(rule, dict) and rule.get("kind") == "coeficientes_plusvalia"
                    and rule.get("territory") == "ES" and rule.get("status") == "vigente"
                    and rule["effective_from"] <= on
                    and (rule.get("effective_to") is None or on < rule["effective_to"])):
                return tuple(Decimal(str(c)) for c in rule["params"]["by_years"])
    raise LookupError(f"Sin coeficientes máximos de la plusvalía vigentes el {on}")


def disagreements(found: list[MunicipalGains], ccaa: str, folder: Path,
                  year: int) -> list[str]:
    """Reglas de ordenanza cuyo tipo no coincide con el del libro de Hacienda."""
    by_code = {f"ES-{ccaa}-{m.code}": m for m in found}
    out = []
    for path in sorted(folder.glob("*.yaml")):
        if path.name == GENERATED:
            continue
        for rule in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            if not (isinstance(rule, dict) and rule.get("kind") == "tipo_plusvalia"
                    and rule.get("status") == "vigente" and rule.get("effective_to") is None):
                continue
            m = by_code.get(str(rule["territory"]))
            if m is None:
                continue
            if not _same(rule["params"], m):
                out.append(f"{rule['id']} ({path.name}): {rule['params']}; Hacienda {year}: "
                           f"{rate_params(m.rates)}")
    return out


def _same(params: dict[str, object], m: MunicipalGains) -> bool:
    if "rate" in params:
        return all(r == Decimal(str(params["rate"])) for r in m.rates)
    steps = params["by_years"]
    assert isinstance(steps, list)
    for years, rate in enumerate(m.rates):
        expected = [s["rate"] for s in steps if s["from_years"] <= years][-1]
        if Decimal(str(expected)) != rate:
            return False
    return True


def main() -> int:
    import time

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--year", type=int, required=True)
    args = parser.parse_args()
    folder = rules_dir()
    existing = existing_territories(folder)
    maximums = legal_maximums(folder, date(args.year, 1, 1))
    generated: list[dict[str, object]] = []
    warnings: list[str] = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for region, (_, ccaa) in REGIONS.items():
            url = region_url(args.year, region)
            response = client.get(url, timeout=120)
            response.raise_for_status()
            text = pdf_text(response.content)
            found = parse(text)
            levied = {m.code for m in found}
            without = [(r.code, r.name) for r in parse_ibi(text) if r.code not in levied]
            generated += rules(found, without, args.year, ccaa, url, existing, maximums)
            warnings += disagreements(found, ccaa, folder, args.year)
            print(f"Plusvalía {args.year} {region}: {len(found)} con el impuesto, "
                  f"{len(without)} sin él")
            time.sleep(1)
    header = (f"# Generado por `python -m housefinder.ingestion.hacienda_plusvalia --year "
              f"{args.year}` (ADR-0044): no editar a mano.\n"
              f"# Tipo y coeficientes de la plusvalía municipal por municipio, Ministerio de "
              f"Hacienda, libro de {args.year}. Sin verificar.\n")
    (folder / GENERATED).write_text(
        header + yaml.safe_dump(generated, allow_unicode=True, sort_keys=False,
                                default_flow_style=None, width=100),
        encoding="utf-8")
    print(f"{len(generated)} reglas en {GENERATED}")
    for w in warnings:
        print(f"No coincide con Hacienda: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
