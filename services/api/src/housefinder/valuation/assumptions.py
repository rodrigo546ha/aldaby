"""Supuestos del plan estimados desde fuentes públicas, para una oferta (ADR-0022).

Cada supuesto es un `Figure` con su fuente y su límite en la fórmula: el tipo de la hipoteca fija y
la subida del estrés salen del Banco de España; el valor catastral y la parte de construcción, del
Catastro del municipio; la comunidad, los seguros y el mantenimiento, de la EPF de la comunidad
autónoma (o del anuncio, si dice la comunidad). Son medias de zona o nacionales, no datos del
inmueble: la fórmula lo dice y el usuario puede corregirlos en el plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from housefinder.core.figures import Figure, SourceRef, money, ratio
from housefinder.db.connection import Connection
from housefinder.db.references import SeriesPoint, latest_values, national_series

RATE_MEASURE = "tedr_vivienda_nuevas"
FIXED_BAND = "mas_10"  # la hipoteca del simulador es a tipo fijo
SHOCK_MONTHS = 24
CATASTRO = ("inmuebles_residenciales", "valor_catastral_residencial", "valor_catastral",
            "valor_construccion")
EPF = ("gasto_comunidad_hogar", "gasto_seguro_vivienda_hogar",
       "gasto_mantenimiento_vivienda_hogar")
MONTHS = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre")
LISTING = SourceRef("user_input", "anuncio-confirmado")


class MissingData(LookupError):
    """Falta la fuente de un supuesto: el mensaje dice cuál y cómo cargarla."""


@dataclass(frozen=True)
class MarketAssumptions:
    """Los mismos para todas las ofertas."""

    mortgage_rate: Figure
    rate_shock: Figure


@dataclass(frozen=True)
class PropertyAssumptions:
    cadastral_value: Figure
    cadastral_land_value: Figure  # para la plusvalía municipal de la venta
    construction_value: Figure
    community_fees_monthly: Figure
    insurance_annual: Figure
    maintenance_annual: Figure

    def figures(self) -> tuple[Figure, ...]:
        return (self.cadastral_value, self.cadastral_land_value, self.construction_value,
                self.community_fees_monthly,
                self.insurance_annual, self.maintenance_annual)


def market_assumptions(conn: Connection) -> MarketAssumptions:
    series = national_series(conn, RATE_MEASURE, FIXED_BAND)
    if not series:
        raise MissingData("Faltan los tipos del Banco de España: `make supuestos`")
    last = series[-1]
    source = _dataset(last.source_id, f"{last.year}-{last.month:02d}")
    rate = Figure(
        "assumption.mortgage_rate", ratio(last.value), "ratio",
        f"TEDR de las nuevas hipotecas a más de diez años de fijación, {MONTHS[last.month - 1]} "
        f"de {last.year} (Banco de España): tipo de mercado nacional, no el de tu perfil, y sin "
        "comisiones", (source,), as_of=date(last.year, last.month, 1))
    rise, start, end = largest_rise(series, SHOCK_MONTHS)
    shock = Figure(
        "assumption.rate_shock", ratio(rise), "ratio",
        f"Mayor subida de ese tipo en {SHOCK_MONTHS} meses desde {series[0].year}: de "
        f"{MONTHS[start.month - 1]} de {start.year} a {MONTHS[end.month - 1]} de {end.year}",
        (_dataset(last.source_id, f"{series[0].year}-{last.year}"),))
    return MarketAssumptions(rate, shock)


def largest_rise(series: list[SeriesPoint],
                 months: int) -> tuple[Decimal, SeriesPoint, SeriesPoint]:
    """La mayor subida de la serie en una ventana de `months` meses de calendario (la serie puede
    tener huecos: los meses sin dato del Banco de España), con sus extremos."""
    best = (Decimal(0), series[0], series[0])
    for j, end in enumerate(series):
        for start in series[:j]:
            within = (end.year - start.year) * 12 + end.month - start.month <= months
            if within and end.value - start.value > best[0]:
                best = (end.value - start.value, start, end)
    return best


def property_assumptions(conn: Connection, municipality: str, region: str, price: Decimal,
                         listing_fees: Decimal | None) -> PropertyAssumptions:
    """`municipality`: código INE de cinco cifras; `region`: el de la comunidad (13)."""
    cat = latest_values(conn, "municipio", municipality, CATASTRO)
    if not all(m in cat for m in CATASTRO) or cat["inmuebles_residenciales"].value <= 0:
        raise MissingData(f"Faltan las estadísticas del Catastro del municipio {municipality}: "
                          "`make supuestos`")
    epf = latest_values(conn, "comunidad", region, EPF)
    if not all(m in epf for m in EPF):
        raise MissingData(f"Falta el gasto de la vivienda de la EPF de la comunidad {region}: "
                          "`make supuestos`")
    year = cat["valor_catastral"].year
    cat_source = _dataset(cat["valor_catastral"].source_id, str(year))
    average = money(cat["valor_catastral_residencial"].value
                    / cat["inmuebles_residenciales"].value)
    cadastral = Figure(
        "assumption.cadastral_value", average, "EUR",
        f"Valor catastral residencial del municipio / inmuebles residenciales ({year}): la media "
        "del municipio, sin ajustar por superficie (el Catastro no la publica)", (cat_source,))
    share = ratio(cat["valor_construccion"].value / cat["valor_catastral"].value)
    land = Figure(
        "assumption.cadastral_land_value", money(average * (1 - share)), "EUR",
        f"Valor catastral estimado × parte de suelo del municipio ({1 - share}, {year}, todos los "
        "usos): para la plusvalía municipal de la venta", (cat_source,))
    construction = Figure(
        "assumption.construction_value", money(price * share), "EUR",
        f"Precio × parte de construcción del valor catastral del municipio ({share}, {year}, "
        "todos los usos): base de la amortización", (cat_source,))
    epf_year = epf["gasto_comunidad_hogar"].year
    epf_source = _dataset(epf["gasto_comunidad_hogar"].source_id, str(epf_year))
    if listing_fees is not None:
        fees = Figure("assumption.community_fees_monthly", money(listing_fees), "EUR/mes",
                      "Gastos de comunidad que dice el anuncio, confirmados", (LISTING,))
    else:
        fees = Figure(
            "assumption.community_fees_monthly",
            money(epf["gasto_comunidad_hogar"].value / 12), "EUR/mes",
            f"Gasto medio por hogar en gastos comunitarios de la comunidad / 12 ({epf_year}, EPF): "
            "media de todos los hogares, también los que no pagan comunidad; se queda corta",
            (epf_source,))
    insurance = Figure(
        "assumption.insurance_annual", money(epf["gasto_seguro_vivienda_hogar"].value), "EUR/año",
        f"Gasto medio por hogar en seguros ligados a la vivienda ({epf_year}, EPF): seguro de "
        "hogar, sin el de impago", (epf_source,))
    maintenance = Figure(
        "assumption.maintenance_annual",
        money(epf["gasto_mantenimiento_vivienda_hogar"].value), "EUR/año",
        f"Gasto medio por hogar en mantenimiento y reparaciones corrientes ({epf_year}, EPF): "
        "media de todos los hogares, no de las viviendas alquiladas", (epf_source,))
    return PropertyAssumptions(cadastral, land, construction, fees, insurance, maintenance)


def _dataset(source_id: str, period: str) -> SourceRef:
    return SourceRef("dataset", f"{source_id}@{period}")
