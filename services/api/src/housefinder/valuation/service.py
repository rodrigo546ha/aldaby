"""Renta y precio estimados de un inmueble como `Figure` con rango (F5.3, F5.4, ADR-0018).

1. Sección del punto en el seccionado de 2021, el del SERPAVI; si la sección no tiene datos, su
   distrito; si tampoco, el municipio.
2. Renta €/m² mes del último año, contraída hacia el municipio con k (parámetro PROVISIONAL), por
   la superficie del inmueble.
3. Precio €/m²: renta × 12 × relación precio/renta del municipio en ese año (valor tasado / renta
   municipal anual), llevado al último trimestre con el IPV de la comunidad. Supone la misma
   rentabilidad bruta en todo el municipio: va como supuesto en las fuentes de la cifra.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from housefinder.core.figures import Figure, SourceRef, money
from housefinder.db.connection import Connection
from housefinder.db.references import (
    RentRow,
    annual_index,
    annual_mean_of_months,
    latest_index,
    latest_month,
    reference_value,
    rent_stats,
)
from housefinder.db.sections import section_at
from housefinder.engines.valuation import (
    Range,
    RentStats,
    Shrunk,
    index_update,
    price_per_m2,
    price_to_rent_ratio,
    rent_for_area,
    scale,
    shrink,
)
from housefinder.params.book import ParamBook
from housefinder.params.valuation import shrinkage

SERPAVI_VINTAGE = 2021
SERPAVI = "serpavi"
APPRAISAL = "valor-tasado-comunidad-madrid"
IPV = "ine-ipv-80270"
IPC_RENT = "ine-ipc-alquiler"
MONTHS = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre")
# Comunidad autónoma del INE por provincia, para el IPV. MVP: Madrid.
REGION_BY_PROVINCE = {"28": "13"}
LEVEL_NAMES = {"seccion": "la sección censal", "distrito": "el distrito censal",
               "municipio": "el municipio"}
TYPOLOGY_NAMES = {"colectiva": "vivienda colectiva (pisos)",
                  "unifamiliar": "vivienda unifamiliar"}
UNIFORM_YIELD = SourceRef("assumption", "rentabilidad-bruta-uniforme-en-el-municipio",
                          provisional=True)
RENT_MODEL = SourceRef("model", "renta-serpavi-v1")
PRICE_MODEL = SourceRef("model", "precio-desde-renta-v1")
ATTRIBUTION = [
    "SERPAVI, Ministerio de Vivienda y Agenda Urbana (rentas declaradas en el IRPF)",
    "Valor tasado de la vivienda libre, Ministerio de Vivienda y Agenda Urbana, vía Comunidad "
    "de Madrid (CC BY 4.0)",
    "Índice de Precios de Vivienda, INE",
    "Índice de Precios de Consumo, alquiler de vivienda, INE",
]


class OutsideCoverage(LookupError):
    """El punto no está en la cartografía de 2021 o su municipio no tiene referencias."""


@dataclass(frozen=True)
class ValuationReport:
    section_code: str
    level: str  # de dónde sale la renta: 'seccion', 'distrito' o 'municipio'
    figures: list[Figure]
    notes: list[str] = field(default_factory=list)
    attribution: list[str] = field(default_factory=lambda: list(ATTRIBUTION))


def value_property(
    conn: Connection,
    book: ParamBook,
    lon: float,
    lat: float,
    area_m2: Decimal,
    typology: str = "colectiva",
    new_build: bool = False,
    on: date | None = None,
) -> ValuationReport:
    on = on or date.today()
    hit = section_at(conn, lon, lat, SERPAVI_VINTAGE)
    if hit is None:
        raise OutsideCoverage("El punto no cae en ninguna sección de la cartografía de 2021")
    section = hit.code
    municipality_code = section[:5]
    municipal = rent_stats(conn, "municipio", municipality_code, typology)
    if municipal is None:
        raise OutsideCoverage(f"Sin referencias de alquiler de {TYPOLOGY_NAMES[typology]} en "
                              f"el municipio {municipality_code}")
    local = (rent_stats(conn, "seccion", section, typology)
             or rent_stats(conn, "distrito", section[:7], typology) or municipal)
    if local.year != municipal.year:  # contraer siempre contra el municipio del mismo año
        same_year = rent_stats(conn, "municipio", municipality_code, typology, local.year)
        municipal = same_year or municipal
    k = shrinkage(book, "ES", on)
    shrunk = (shrink(_stats(local), _stats(municipal), k.k) if local.level != "municipio"
              else shrink(_stats(local), _stats(municipal), Decimal(0)))

    notes = [_level_note(local, shrunk)]
    rent_sources = (SourceRef("dataset", f"{SERPAVI}@{local.year}"), k.source, RENT_MODEL)
    current, as_of, update = _rent_update(conn, local, shrunk, municipality_code)
    notes.append(update.note)
    figures = _rent_figures(local, current, area_m2, typology, (*rent_sources, *update.sources),
                            as_of, update.formula)

    # El precio sale de la renta del mismo año que el valor tasado; se actualiza con el IPV.
    price = _price_figures(conn, local, municipal, shrunk, area_m2, new_build, rent_sources,
                           notes)
    figures.extend(price)
    return ValuationReport(section, local.level, figures, notes)


@dataclass(frozen=True)
class RentUpdate:
    note: str
    formula: str
    sources: tuple[SourceRef, ...] = ()


def _rent_update(conn: Connection, local: RentRow, shrunk: Shrunk,
                 municipality_code: str) -> tuple[Shrunk, date, RentUpdate]:
    """Renta del último año del SERPAVI llevada al último mes del IPC de alquiler, si lo hay."""
    region = REGION_BY_PROVINCE.get(municipality_code[:2])
    latest = latest_month(conn, IPC_RENT, "comunidad", region, "ipc_alquiler") if region else None
    base = (annual_mean_of_months(conn, IPC_RENT, "comunidad", region, "ipc_alquiler",
                                  local.year) if region else None)
    if latest is None or base is None or (latest.year, latest.month) <= (local.year, 12):
        return shrunk, date(local.year, 12, 31), RentUpdate(
            note=(f"La renta es la declarada en el IRPF en {local.year} (último año del "
                  "SERPAVI), sin actualizar: no hay índice de alquiler posterior cargado."),
            formula=f"renta de {local.year}")
    change = latest.value / base - 1
    month = MONTHS[latest.month - 1]
    return scale(shrunk, base, latest.value), _month_end(latest.year, latest.month), RentUpdate(
        note=(f"Renta declarada en {local.year}, llevada a {month} de {latest.year} con el "
              f"componente de alquiler del IPC de la comunidad ({change:+.1%}). En el "
              "backtesting, una renta actualizada así se quedaba aún corta un 4 % a dos años."),
        formula=f"renta de {local.year} × IPC de alquiler de {month} de {latest.year} / media "
                f"de {local.year}",
        sources=(SourceRef("dataset", f"{IPC_RENT}@{latest.year}-{latest.month:02d}"),))


def _month_end(year: int, month: int) -> date:
    return (date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1))


def _stats(row: RentRow) -> RentStats:
    return RentStats(row.n, row.p25, row.median, row.p75)


def _level_note(local: RentRow, shrunk: Shrunk) -> str:
    where = LEVEL_NAMES[local.level]
    count = f"{local.n} alquileres declarados" if local.n is not None else "alquileres sin contar"
    if local.level == "municipio":
        return f"La sección y su distrito no tienen datos publicados: renta de {where} ({count})."
    if shrunk.weight == 1:
        return f"Renta de {where} ({count}), sin mezclarla con la del municipio."
    return (f"Renta de {where} ({count}), con un peso del {shrunk.weight * 100:.0f} % frente al "
            "municipio.")


def _rent_figures(local: RentRow, shrunk: Shrunk, area_m2: Decimal, typology: str,
                  sources: tuple[SourceRef, ...], as_of: date, update: str) -> list[Figure]:
    rent = rent_for_area(shrunk, area_m2)
    return [
        Figure(
            key="valuation.rent_m2_month", value=shrunk.median, unit="EUR/m2 mes",
            low=shrunk.p25, high=shrunk.p75, as_of=as_of, sources=sources,
            formula=(f"Mediana de la renta por m² de {TYPOLOGY_NAMES[typology]} en "
                     f"{LEVEL_NAMES[local.level]} ({update}); rango P25–P75"),
        ),
        Figure(
            key="valuation.rent_monthly", value=rent.value, unit="EUR/mes", low=rent.low,
            high=rent.high, as_of=as_of, sources=sources,
            formula=f"{shrunk.median} €/m² al mes × {area_m2} m²",
        ),
    ]


def _price_figures(conn: Connection, local: RentRow, municipal: RentRow, shrunk: Shrunk,
                   area_m2: Decimal, new_build: bool, rent_sources: tuple[SourceRef, ...],
                   notes: list[str]) -> list[Figure]:
    appraisal = reference_value(conn, APPRAISAL, "municipio", municipal.code, "valor_tasado_m2",
                                local.year)
    if appraisal is None:
        notes.append(f"Sin precio: el municipio no tiene valor tasado de {local.year} (solo se "
                     "publica para municipios de más de 25.000 habitantes).")
        return []
    ratio = price_to_rent_ratio(appraisal, municipal.median)
    sources = (*rent_sources, SourceRef("dataset", f"{APPRAISAL}@{local.year}"), UNIFORM_YIELD,
               PRICE_MODEL)
    per_m2 = price_per_m2(shrunk, ratio)
    as_of = date(local.year, 12, 31)
    index_note = f"Precio de {local.year}, sin actualizar: no hay índice de precios cargado."
    region = REGION_BY_PROVINCE.get(municipal.code[:2])
    typology = "nueva" if new_build else "segunda_mano"
    latest = latest_index(conn, IPV, region, typology) if region else None
    base = annual_index(conn, IPV, region, typology, local.year) if region else None
    if latest is not None and base is not None:
        per_m2 = Range(*(index_update(v, base, latest.value)
                         for v in (per_m2.low, per_m2.value, per_m2.high)))
        sources = (*sources, SourceRef("dataset", f"{IPV}@{latest.year}T{latest.quarter}"))
        as_of = _quarter_end(latest.year, latest.quarter)
        index_note = (f"Precio llevado de {local.year} al {latest.quarter}.º trimestre de "
                      f"{latest.year} con el índice de precios de vivienda "
                      f"{'nueva' if new_build else 'de segunda mano'} del INE.")
    notes.append(index_note)
    notes.append("El valor tasado es tasación, no precio de compraventa; las rentas son las "
                 "declaradas, no las de los anuncios.")
    return [
        Figure(
            key="valuation.price_rent_ratio", value=ratio, unit="años",
            as_of=date(local.year, 12, 31),
            sources=(SourceRef("dataset", f"{APPRAISAL}@{local.year}"),
                     SourceRef("dataset", f"{SERPAVI}@{local.year}")),
            formula=(f"Valor tasado del municipio ({appraisal} €/m²) / (renta mediana municipal "
                     f"{municipal.median} €/m² al mes × 12), {local.year}"),
        ),
        Figure(
            key="valuation.price_m2", value=per_m2.value, unit="EUR/m2", low=per_m2.low,
            high=per_m2.high, as_of=as_of, sources=sources,
            formula=(f"Renta {shrunk.median} €/m² al mes × 12 × {ratio} años de renta del "
                     "municipio, actualizado con el índice de precios; supone la misma "
                     "rentabilidad bruta en todo el municipio"),
        ),
        Figure(
            key="valuation.price_total", value=money(per_m2.value * area_m2), unit="EUR",
            low=money(per_m2.low * area_m2), high=money(per_m2.high * area_m2), as_of=as_of,
            sources=sources, formula=f"{per_m2.value} €/m² × {area_m2} m²",
        ),
    ]


def _quarter_end(year: int, quarter: int) -> date:
    return {1: date(year, 3, 31), 2: date(year, 6, 30), 3: date(year, 9, 30),
            4: date(year, 12, 31)}[quarter]
