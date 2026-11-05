"""Las fuentes de las cifras para leerlas en la web (D11, ADR-0026).

Una cifra cita sus fuentes por identificador («madrid-itp-inmuebles-2014»). La web las pide aquí
para enseñar qué es cada una («ITP de la vivienda usada · Comunidad de Madrid»), su cita legal o de
dónde salen los valores, y su enlace oficial. No hay datos personales: solo normas, parámetros,
tablas públicas y qué es cada supuesto.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from housefinder.api.deps import DbDep, ParamBookDep, RuleBookDep
from housefinder.core.figures import SourceRef
from housefinder.db.sections import sources_by_id
from housefinder.profiles.interview import regions
from housefinder.reports.sources import KIND, dataset_id, describe
from housefinder.territory.municipalities import load_municipalities

router = APIRouter(prefix="/sources", tags=["fuentes"])

MAX_REFS = 200


class SourceInfoOut(BaseModel):
    ref: str  # lo que se pidió: «rule:madrid-itp-inmuebles-2014» o solo el identificador
    kind: str  # rule, param, dataset, model, assumption, user_input
    kind_label: str  # «Norma», «Parámetro»…
    name: str
    detail: str
    url: str | None


@router.get("", response_model=list[SourceInfoOut])
def source_info(
    db: DbDep,
    rules: RuleBookDep,
    params: ParamBookDep,
    ref: Annotated[list[str], Query(max_length=MAX_REFS)] = [],  # noqa: B006 (FastAPI)
) -> list[SourceInfoOut]:
    """Qué es cada fuente. `ref` es `tipo:identificador`; sin tipo, se busca entre las normas y
    después entre los parámetros (los avisos del plan citan solo el identificador)."""
    rule_ids = {r.id for r in rules.rules}
    param_ids = {p.id for p in params.params}
    wanted: list[tuple[str, SourceRef]] = []
    for raw in dict.fromkeys(ref):
        kind, _, code = raw.partition(":") if ":" in raw else ("", "", raw)
        if not kind:
            kind = "rule" if code in rule_ids else "param" if code in param_ids else "assumption"
        if kind in KIND and code:
            wanted.append((raw, SourceRef(kind, code)))
    datasets = sorted({dataset_id(r) for _, r in wanted if r.kind == "dataset"})
    records = sources_by_id(db, datasets) if datasets else {}
    entries = describe([r for _, r in wanted], rules, params, records, territory_name)
    return [
        SourceInfoOut(ref=raw, kind=r.kind, kind_label=e.kind, name=e.name or e.title,
                      detail=e.detail, url=e.url)
        for (raw, r), e in zip(wanted, entries, strict=True)
    ]


def territory_name(code: str) -> str:
    """ES → España; ES-13 → Comunidad de Madrid; ES-16-48 → Bizkaia; ES-13-28079 → Madrid."""
    if code == "ES":
        return "España"
    parts = code.split("-")
    names = regions()
    if len(parts) == 2:
        return (names.get(parts[1]) or [code])[0]
    if len(parts) == 3 and len(parts[2]) == 2:  # territorio histórico (ADR-0046)
        return (names.get(f"{parts[1]}-{parts[2]}") or [code])[0]
    if len(parts) == 3:
        town = load_municipalities().get(parts[2])
        return town.name if town else code
    return code

