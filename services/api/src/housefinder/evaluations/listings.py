"""Extracción de anuncios contra el juego etiquetado de `data/evaluation/anuncios.yaml`.

Cada campo esperado se compara con lo que queda tras la comprobación de citas (ADR-0013): correcto,
falta (el documento lo da y no se extrajo), distinto (se extrajo otro valor) o sobra (se extrajo
algo que el documento no da). Los lotes del BOE se comparan por orden; los que sobran o faltan se
cuentan aparte.
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal

import yaml

from housefinder.agent.extraction import FIELD_KINDS, LISTING_KINDS, CheckedDocument, CheckedListing

Outcome = Literal["correcto", "falta", "distinto", "sobra", "vacio"]
LOT_FIELDS = ("label", "property_type", "address", "municipality", "province", "cadastral_ref",
              "built_area_m2", "floor", "price", "deposit")
LISTING_FIELDS = ("operation", "property_type", *LISTING_KINDS)


@dataclass(frozen=True)
class Case:
    id: str
    kind: Literal["anuncio", "boe"]
    text: str
    expected: dict[str, Any] = field(default_factory=dict)  # anuncio
    lots: list[dict[str, Any]] = field(default_factory=list)  # boe


@dataclass(frozen=True)
class FieldResult:
    case: str
    field: str
    outcome: Outcome
    expected: Any
    got: Any


@dataclass
class ExtractionReport:
    fields: list[FieldResult] = field(default_factory=list)
    extra_lots: int = 0
    missing_lots: int = 0
    errors: list[str] = field(default_factory=list)  # documentos que el modelo no extrajo

    def by_field(self) -> dict[str, Counter[str]]:
        result: dict[str, Counter[str]] = {}
        for r in self.fields:
            result.setdefault(r.field, Counter())[r.outcome] += 1
        return result

    def metrics(self) -> dict[str, int]:
        """`con_valor`: campos en los que el documento da un valor (aunque admita dejarlo
        vacío); `correctos` cuenta los acertados de esos."""
        counted = Counter(r.outcome for r in self.fields)
        with_value = sum(1 for r in self.fields if _accepts_value(r.expected))
        return {"correctos": counted["correcto"], "con_valor": with_value,
                "campos": len(self.fields), "falta": counted["falta"],
                "distinto": counted["distinto"], "sobra": counted["sobra"],
                "lotes_de_mas": self.extra_lots, "lotes_de_menos": self.missing_lots,
                "errores": len(self.errors)}


def default_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "evaluation" / "anuncios.yaml"


def load_cases(path: Path | None = None) -> list[Case]:
    path = path or default_path()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [Case(item["id"], item["kind"],
                 (path.parent / item["file"]).read_text(encoding="utf-8"),
                 item.get("expected") or {}, item.get("lots") or []) for item in raw]


def evaluate(cases: list[Case],
             extract_listing: Callable[[str], CheckedListing],
             extract_document: Callable[[str], CheckedDocument]) -> ExtractionReport:
    report = ExtractionReport()
    for case in cases:
        try:
            if case.kind == "anuncio":
                listing = extract_listing(case.text)
                got = {"operation": listing.operation, "property_type": listing.property_type,
                       **{n: listing.value(n) for n in LISTING_KINDS}}
                report.fields += _compare(case.id, case.expected, got, LISTING_FIELDS)
            else:
                document = extract_document(case.text)
                _compare_lots(case, document, report)
        except Exception as exc:  # noqa: BLE001 - un documento que falla no para la evaluación
            report.errors.append(f"{case.id}: {exc}")
    return report


def _compare_lots(case: Case, document: CheckedDocument, report: ExtractionReport) -> None:
    for i, expected in enumerate(case.lots):
        if i >= len(document.lots):
            report.missing_lots += 1
            report.fields += [FieldResult(f"{case.id}#{i + 1}", n, "falta", expected.get(n), None)
                              for n in LOT_FIELDS if _accepts_value(expected.get(n))]
            continue
        lot = document.lots[i]
        got = {"property_type": lot.property_type, **{n: lot.value(n) for n in FIELD_KINDS}}
        report.fields += _compare(f"{case.id}#{i + 1}", expected, got, LOT_FIELDS)
    report.extra_lots += max(0, len(document.lots) - len(case.lots))


def _compare(case: str, expected: Mapping[str, Any], got: Mapping[str, Any],
             names: tuple[str, ...]) -> list[FieldResult]:
    results = []
    for name in names:
        want = expected.get(name)
        options = want if isinstance(want, list) else [want]
        value = got.get(name)
        if value is None:
            outcome: Outcome = "vacio" if None in options else "falta"
        elif any(o is not None and _same(o, value, name) for o in options):
            outcome = "correcto"
        else:
            outcome = "sobra" if options == [None] else "distinto"
        results.append(FieldResult(case, name, outcome, want, value))
    return results


def _accepts_value(want: Any) -> bool:
    options = want if isinstance(want, list) else [want]
    return any(o is not None for o in options)


def _same(expected: Any, got: Any, name: str) -> bool:
    kind = LISTING_KINDS.get(name) or FIELD_KINDS.get(name)
    if kind == "number":
        try:
            return Decimal(str(expected)) == Decimal(str(got))
        except InvalidOperation:
            return False
    if kind == "cadastral":
        return str(expected).upper() == str(got).upper()
    a, b = _fold(str(expected)), _fold(str(got))
    return bool(b) and (a in b or b in a)


def _fold(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text.lower())
    return " ".join("".join(c for c in plain if not unicodedata.combining(c)).split())
