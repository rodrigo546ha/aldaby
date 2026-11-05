"""Anexo de fuentes del PDF: cada fuente una vez, numerada, con lo que es y de dónde sale.

Una cifra cita sus fuentes con `SourceRef` (D11). Aquí cada referencia se resuelve a algo que se
pueda leer y comprobar (ADR-0026):
- norma: su enlace oficial, su vigencia y si está verificada;
- parámetro: de dónde salen sus valores y su enlace;
- datos: nombre, enlace, licencia y fecha de descarga de la tabla `sources` (el identificador de la
  cifra lleva el periodo detrás de «@»);
- modelo, supuesto o dato del usuario: qué es, en una frase.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import date

from housefinder.core.figures import Figure, SourceRef
from housefinder.db.sections import SourceRecord
from housefinder.params.book import ParamBook
from housefinder.regulation.rules import RuleBook

KIND = {"rule": "Norma", "param": "Parámetro", "dataset": "Datos", "model": "Modelo",
        "assumption": "Supuesto", "user_input": "Dato tuyo"}
# Qué es cada supuesto, modelo o dato del usuario que citan las cifras
DESCRIPTIONS = {
    "conversion-euribor-3m-12m": "Paso del Euríbor a tres meses de las proyecciones del BCE al "
                                 "Euríbor a un año con la prima del último dato oficial "
                                 "(ADR-0006).",
    "euribor-constante-tras-horizonte": "Tras el último trimestre proyectado, el Euríbor se "
                                        "mantiene constante.",
    "diferencial-variable-estimado": "Diferencial de la hipoteca variable estimado con la media "
                                     "nacional del Banco de España, no la oferta de un banco "
                                     "(ADR-0025).",
    "el-ciclo-futuro-como-el-historico-del-ipv": "Los escenarios de revalorización suponen que el "
                                                 "ciclo futuro se parece al histórico del índice "
                                                 "de precios de vivienda del INE.",
    "el-precio-sigue-a-la-renta-frente-a-la-provincia": "El precio estimado se mueve con la renta "
                                                        "de la zona frente a la de la provincia.",
    "escenario-estres": "Subida de tipos de la prueba de estrés.",
    "gastos-de-venta": "Gastos de venta (agencia y otros) que pusiste en tu perfil.",
    "gestoria-tasacion-y-copias": "Gestoría, tasación y copias que pusiste en tu perfil.",
    "minimo-absorbido-por-la-base-general": "El mínimo personal se aplica primero a la base "
                                            "general del IRPF.",
    "normativa-conocida-hoy-en-la-venta": "En la venta se aplica la normativa que se conoce hoy.",
    "rentabilidad-bruta-uniforme-en-el-municipio": "La relación entre precio y renta es la misma "
                                                   "en todo el municipio.",
    "revalorizacion": "Revalorización anual supuesta.",
    "seccion-estable-1-por-ciento": "La sección censal se da por estable si su geometría cambia "
                                    "menos de un uno por ciento entre seccionados.",
    "sin-escenario-de-revalorizacion": "Sin escenarios de revalorización para el municipio: la "
                                       "venta se calcula sin revalorizar.",
    "situacion-personal-constante-hasta-la-venta": "Tu situación fiscal y familiar se mantiene "
                                                   "hasta la venta.",
    "tipo-marginal": "Tipo marginal del IRPF que indicaste.",
    "renta-esperada-temporada": "Lo que esperas sacar al mes con el alquiler de temporada.",
    "renta-esperada-habitaciones": "Lo que esperas sacar al mes con el alquiler por habitaciones.",
    "renta-esperada-turistico": "Lo que esperas sacar al mes con el alquiler turístico.",
    "escenarios-revalorizacion-v1": "Escenarios de revalorización desde el índice de precios de "
                                    "vivienda del INE (F5.5).",
    "precio-desde-renta-v1": "Precio estimado desde la renta y la relación entre precio y renta "
                             "del municipio (ADR-0018).",
    "renta-serpavi-v1": "Renta estimada con las referencias del SERPAVI por sección, con "
                        "contracción hacia el municipio (ADR-0018).",
    "alquiler": "Datos del alquiler del plan.",
    "anuncio-confirmado": "Lo que dice el anuncio y confirmaste.",
    "comprador": "Tus datos del perfil: ingresos, ahorro, edad y residencia.",
    "financiacion": "Condiciones de financiación del plan.",
    "finanzas-del-comprador": "Tus ingresos, deudas y ahorro del perfil.",
    "inmueble": "Datos del inmueble del plan.",
    "pacto-gastos-escritura": "Quién paga la escritura según lo pactado.",
    "tasa-de-gastos-de-compra": "Tasa de gastos de compra indicada.",
    "tipo-de-interes": "Tipo de interés indicado.",
    "boe-tipo-de-subasta": "Tipo de salida que publica el anuncio de la subasta en el BOE.",
}


# Nombre de cada tipo de regla y de parámetro para quien lee el plan; el identificador se queda
# para el anexo del PDF y para buscarla en data/rules
RULE_KINDS = {
    "ajd_compra_vivienda": "AJD de la compra",
    "amortizacion_inmueble_alquiler": "Amortización del inmueble en el IRPF",
    "arancel_notarial": "Aranceles notariales",
    "arancel_registral": "Aranceles del Registro de la Propiedad",
    "bonificacion_ajd": "Bonificación del AJD",
    "bonificacion_ibi": "Bonificación del IBI",
    "bonificacion_itp": "Bonificación del ITP",
    "bonificacion_plusvalia": "Bonificación de la plusvalía municipal",
    "coeficientes_plusvalia": "Coeficientes de la plusvalía municipal",
    "deduccion_irpf_rentas_territorio": "Deducción del IRPF por rentas del territorio",
    "deducciones_cuota_irpf_foral": "Deducciones de la cuota del IRPF foral",
    "escala_irpf_ahorro_autonomica": "Escala autonómica del ahorro del IRPF",
    "escala_irpf_ahorro_estatal": "Escala estatal del ahorro del IRPF",
    "escala_irpf_ahorro_foral": "Escala foral del ahorro del IRPF",
    "escala_irpf_general_autonomica": "Escala autonómica del IRPF",
    "escala_irpf_general_estatal": "Escala estatal del IRPF",
    "escala_irpf_general_foral": "Escala foral del IRPF",
    "impuesto_compra_segunda_mano": "ITP de la vivienda usada",
    "iva_tipo_general": "IVA, tipo general",
    "iva_vivienda_nueva": "IVA de la vivienda nueva",
    "limite_intereses_reparacion": "Límite de intereses y reparación del IRPF",
    "minimo_contribuyente": "Mínimo del contribuyente del IRPF",
    "minimo_descendientes": "Mínimo por descendientes del IRPF",
    "pagador_escritura_compraventa": "Quién paga la escritura",
    "prorroga_alquiler_habitual": "Prórroga del alquiler de vivienda",
    "reduccion_irpf_alquiler": "Reducción del IRPF por alquiler de vivienda",
    "regimen_alquiler_habitaciones": "Alquiler por habitaciones",
    "regimen_alquiler_habitual": "Alquiler de vivienda habitual",
    "regimen_alquiler_temporada": "Alquiler de temporada",
    "regimen_alquiler_turistico": "Alquiler turístico",
    "regimen_irpf": "Régimen del IRPF, común o foral",
    "rendimiento_alquiler_irpf": "Rendimiento del alquiler en el IRPF",
    "subasta_judicial_inmuebles": "Subasta judicial de inmuebles",
    "tipo_ibi": "Tipo del IBI",
    "tipo_plusvalia": "Tipo de la plusvalía municipal",
    "zona_tensionada": "Zona de mercado residencial tensionado",
}
PARAM_KINDS = {
    "contraccion_renta": "Contracción de la renta estimada",
    "convergencia_municipal": "Convergencia de la revalorización del municipio",
    "criterios_bancarios": "Criterios bancarios",
    "euribor_12m_oficial": "Euríbor a un año oficial",
    "trayectoria_euribor_3m": "Trayectoria esperada del Euríbor",
}
MONTHS = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre")
# Las referencias internas (ADR, tareas del roadmap) no son para quien lee el plan
_INTERNAL = re.compile(r"\s*\((?:ADR-\d+|F\d+\.\d+)\)")


@dataclass(frozen=True)
class SourceEntry:
    number: int
    kind: str  # «Norma», «Datos»…
    title: str  # el identificador de la fuente (el anexo del PDF)
    url: str | None
    detail: str  # vigencia, licencia y fecha, o qué es
    provisional: bool
    name: str = ""  # lo que es, para leerlo: «ITP de la vivienda usada · Comunidad de Madrid»


@dataclass(frozen=True)
class SourceCatalog:
    entries: tuple[SourceEntry, ...]
    numbers: Mapping[SourceRef, int]

    def notes(self, figure: Figure) -> tuple[int, ...]:
        return tuple(sorted({self.numbers[s] for s in figure.sources}))


def dataset_id(ref: SourceRef) -> str:
    """«bde-be1904@2026-08» → «bde-be1904»."""
    return ref.id.split("@", 1)[0]


def describe(refs: Iterable[SourceRef], rules: RuleBook, params: ParamBook,
             records: Mapping[str, SourceRecord],
             place: Callable[[str], str] = lambda territory: territory) -> list[SourceEntry]:
    """Las fuentes para leerlas en la web: qué es cada una, de dónde sale y su enlace. `place` da
    el nombre de un territorio (ES-13 → «Comunidad de Madrid»)."""
    rule_by_id = {r.id: r for r in rules.rules}
    param_by_id = {p.id: p for p in params.params}
    out = []
    for ref in refs:
        entry = _entry(0, ref, rule_by_id, param_by_id, records, place)
        rule = rule_by_id.get(ref.id) if ref.kind == "rule" else None
        # En la web, la cita legal de la norma; el PDF da la vigencia y enlaza en su anexo
        detail = (rule_detail(rule.notes, rule.effective_from, rule.verified) if rule
                  else _INTERNAL.sub("", entry.detail))
        # Un supuesto ya se explica con su nombre: no se repite debajo
        if detail.rstrip(".") == entry.name:
            detail = ""
        out.append(replace(entry, detail=detail))
    return out


def catalog(figures: Iterable[Figure], rules: RuleBook, params: ParamBook,
            records: Mapping[str, SourceRecord]) -> SourceCatalog:
    """Las fuentes de las cifras, numeradas en el orden en que aparecen."""
    rule_by_id = {r.id: r for r in rules.rules}
    param_by_id = {p.id: p for p in params.params}
    numbers: dict[SourceRef, int] = {}
    entries: list[SourceEntry] = []
    for figure in figures:
        for ref in figure.sources:
            if ref in numbers:
                continue
            numbers[ref] = len(entries) + 1
            entries.append(_entry(numbers[ref], ref, rule_by_id, param_by_id, records))
    return SourceCatalog(tuple(entries), numbers)


def _entry(number: int, ref: SourceRef, rule_by_id: Mapping, param_by_id: Mapping,
           records: Mapping[str, SourceRecord],
           place: Callable[[str], str] = lambda territory: territory) -> SourceEntry:
    kind = KIND.get(ref.kind, ref.kind)
    if ref.kind == "rule" and ref.id in rule_by_id:
        rule = rule_by_id[ref.id]
        until = f" hasta el {rule.effective_to.isoformat()}" if rule.effective_to else ""
        checked = ("verificada" if rule.verified else "sin verificar")
        state = "" if rule.status == "vigente" else f", {rule.status.replace('_', ' ')}"
        name = f"{RULE_KINDS.get(rule.kind, _humane(rule.kind))} · {place(rule.territory)}"
        return SourceEntry(number, kind, ref.id, rule.source_url,
                           f"Vigente desde el {rule.effective_from.isoformat()}{until}{state}; "
                           f"{checked}.", ref.provisional, name)
    if ref.kind == "param" and ref.id in param_by_id:
        param = param_by_id[ref.id]
        name = PARAM_KINDS.get(param.kind, _humane(param.kind))
        return SourceEntry(number, kind, ref.id, param.source_url, param.source,
                           ref.provisional, name)
    if ref.kind == "dataset":
        record = records.get(dataset_id(ref))
        if record is not None:
            period = ref.id.split("@", 1)[1] if "@" in ref.id else ""
            fetched = (f", descargado el {record.fetched_at.date().isoformat()}"
                       if record.fetched_at else "")
            detail = (f"Periodo {period}. " if period else "") + \
                f"Licencia: {record.license or 'sin indicar'}{fetched}."
            return SourceEntry(number, kind, record.name, record.url or None, detail,
                               ref.provisional, record.name)
    base = ref.id.split("@", 1)[0]
    detail = DESCRIPTIONS.get(base, f"«{ref.id}»")
    name = _INTERNAL.sub("", DESCRIPTIONS[base]).rstrip(".") if base in DESCRIPTIONS \
        else _humane(base)
    return SourceEntry(number, kind, ref.id, None, detail, ref.provisional, name)


def rule_detail(notes: str, effective_from: date, verified: bool) -> str:
    """La cita legal de una regla, su vigencia y si alguien ha leído ya la fuente."""
    since = f"{effective_from.day} de {MONTHS[effective_from.month - 1]} de {effective_from.year}"
    checked = "verificada" if verified else "sin verificar todavía"
    return " ".join(p for p in (notes.strip(), f"Vigente desde el {since}; {checked}.") if p)


def _humane(code: str) -> str:
    """«gestoria-tasacion-y-copias» → «Gestoria tasacion y copias»: solo si no hay nombre."""
    text = re.sub(r"[-_]+", " ", code).strip()
    return text[:1].upper() + text[1:]
