"""Trayectoria esperada del Euríbor a un año (F1.7, ADR-0006).

- Ronda (`trayectoria_euribor_3m`): supuesto de tipos a corto plazo de las proyecciones
  del BCE, por trimestre, tal como se publica en la serie `MPD.Q.U2.STN.I.<ronda>.0000`.
- Ancla (`euribor_12m_oficial`): Euríbor a un año oficial del mes anterior al de la fecha
  de corte, tal como lo publica el Banco de España en el BOE.
- Conversión (supuesto propio, declarado):
    prima        = ancla − media(m3[q0..q0+3])
    euribor_12m[q] = media(m3[q..q+3]) + prima
  con q0 el trimestre del ancla y m3 constante tras el último trimestre publicado.

Los valores se guardan en porcentaje, como se publican, y aquí pasan a tanto por uno.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from housefinder.core.dated import to_date
from housefinder.core.figures import SourceRef
from housefinder.engines.rates import RatePath
from housefinder.params.book import Param, ParamBook

ROUND_KIND = "trayectoria_euribor_3m"
ANCHOR_KIND = "euribor_12m_oficial"
TERRITORY = "ES"
HUNDRED = Decimal(100)

CONVERSION = SourceRef("assumption", "conversion-euribor-3m-12m")
FLAT_AFTER_HORIZON = SourceRef("assumption", "euribor-constante-tras-horizonte")


@dataclass(frozen=True)
class Euribor12mPath:
    round: str
    cut_off: date
    premium: Decimal  # tanto por uno
    quarters: tuple[tuple[date, Decimal], ...]  # (inicio del trimestre, Euríbor a un año)
    sources: tuple[SourceRef, ...]

    def rate_path(self, signing: date) -> RatePath:
        """Trayectoria en meses desde la firma (mes 0 = mes de la firma).

        Si la firma es anterior al primer trimestre, se usa el primer valor hasta entonces;
        tras el último trimestre, el último valor.
        """
        current = self.quarters[0][1]
        steps: list[tuple[int, Decimal]] = []
        for start, value in self.quarters:
            offset = (start.year - signing.year) * 12 + start.month - signing.month
            if offset <= 0:
                current = value
            else:
                if not steps:
                    steps.append((0, current))
                steps.append((offset, value))
        return RatePath(tuple(steps) if steps else ((0, current),), self.sources)


def anchor_month(cut_off: date) -> tuple[int, int]:
    """Mes anterior al de la fecha de corte: el último mes completo antes del corte."""
    return (cut_off.year - 1, 12) if cut_off.month == 1 else (cut_off.year, cut_off.month - 1)


def euribor_12m_path(book: ParamBook, on: date) -> Euribor12mPath:
    """Trayectoria a un año de la ronda vigente en `on`, anclada al dato oficial del BOE."""
    round_param = book.resolve(ROUND_KIND, TERRITORY, on)
    if round_param is None:
        raise LookupError(f"No hay ronda de trayectoria del Euríbor vigente el {on}")
    p = round_param.params
    cut_off = to_date(_get(p, "cut_off", round_param.id))
    quarters = _quarters(round_param)

    year, month = anchor_month(cut_off)
    anchor = _anchor(book, year, month)
    q0 = date(year, 3 * ((month - 1) // 3) + 1, 1)
    starts = [start for start, _ in quarters]
    if q0 not in starts:
        raise ValueError(f"La ronda {round_param.id} no incluye el trimestre del ancla ({q0})")
    m3 = [value for _, value in quarters[starts.index(q0) :]]

    def mean_from(i: int) -> Decimal:
        window = [m3[min(j, len(m3) - 1)] for j in range(i, i + 4)]
        return sum(window, Decimal(0)) / 4

    premium = _percent(anchor.params, "value", anchor.id) - mean_from(0)
    path = tuple(
        (start, mean_from(i) + premium) for i, start in enumerate(starts[starts.index(q0) :])
    )
    return Euribor12mPath(
        round=str(_get(p, "round", round_param.id)),
        cut_off=cut_off,
        premium=premium,
        quarters=path,
        sources=(round_param.ref, anchor.ref, CONVERSION, FLAT_AFTER_HORIZON),
    )


@dataclass(frozen=True)
class OfficialEuribor:
    year: int
    month: int
    value: Decimal  # tanto por uno
    source: SourceRef


def official_anchor(book: ParamBook, on: date) -> OfficialEuribor:
    """El Euríbor a un año oficial que ancla la trayectoria vigente en `on` (su mes y valor)."""
    round_param = book.resolve(ROUND_KIND, TERRITORY, on)
    if round_param is None:
        raise LookupError(f"No hay ronda de trayectoria del Euríbor vigente el {on}")
    year, month = anchor_month(to_date(_get(round_param.params, "cut_off", round_param.id)))
    anchor = _anchor(book, year, month)
    return OfficialEuribor(year, month, _percent(anchor.params, "value", anchor.id), anchor.ref)


def _anchor(book: ParamBook, year: int, month: int) -> Param:
    label = f"{year}-{month:02d}"
    for param in book.of_kind(ANCHOR_KIND):
        if str(param.params.get("month")) == label:
            return param
    raise LookupError(f"Falta el Euríbor a un año oficial (BOE) de {label}")


def _quarters(param: Param) -> list[tuple[date, Decimal]]:
    raw = _get(param.params, "quarters", param.id)
    if _get(param.params, "unit", param.id) != "percent":
        raise ValueError(f"unit debe ser 'percent' en {param.id}")
    quarters = sorted((_quarter_start(str(k), param.id), _to_rate(v)) for k, v in raw.items())
    for (a, _), (b, _) in zip(quarters, quarters[1:], strict=False):
        if (b.year - a.year) * 12 + b.month - a.month != 3:
            raise ValueError(f"Trimestres no consecutivos en {param.id}: {a} → {b}")
    return quarters


def _quarter_start(label: str, param_id: str) -> date:
    year, _, q = label.partition("-Q")
    if not (year.isdigit() and q in {"1", "2", "3", "4"}):
        raise ValueError(f"Trimestre no válido en {param_id}: {label!r} (forma 2026-Q3)")
    return date(int(year), 3 * (int(q) - 1) + 1, 1)


def _percent(params: dict[str, Any], key: str, param_id: str) -> Decimal:
    if _get(params, "unit", param_id) != "percent":
        raise ValueError(f"unit debe ser 'percent' en {param_id}")
    return _to_rate(_get(params, key, param_id))


def _to_rate(value: Any) -> Decimal:
    """Porcentaje publicado → tanto por uno, vía str para no arrastrar el float de YAML."""
    return Decimal(str(value)) / HUNDRED


def _get(params: dict[str, Any], key: str, param_id: str) -> Any:
    if key not in params:
        raise ValueError(f"Falta {key} en {param_id}")
    return params[key]
