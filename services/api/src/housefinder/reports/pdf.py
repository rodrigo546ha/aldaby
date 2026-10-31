"""El plan completo en HTML y en PDF, con notas a sus fuentes (F6.8, ADR-0026).

Solo lo calculado: las cifras del plan con su fórmula, el tipo de alquiler, los argumentos del
programa y la hoja de ruta. La explicación del asesor no va: el mismo plan da el mismo PDF.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from html import escape

from housefinder.core.figures import Figure
from housefinder.db.connection import Connection
from housefinder.db.sections import sources_by_id
from housefinder.params.book import ParamBook
from housefinder.planning.rental_advice import LABELS as RENTAL_LABELS
from housefinder.plans.service import FullPlan
from housefinder.regulation.rules import RuleBook
from housefinder.reports.format import format_value
from housefinder.reports.labels import label
from housefinder.reports.sources import SourceCatalog, catalog, dataset_id

STAGES = {"antes": "Antes de comprometerte", "compra": "La compra",
          "despues": "Después de comprar"}
REDUCTION = {True: "sí", False: "no", None: "por confirmar"}
RENTAL_FIGURE = {"income": "Renta al mes", "cashflow": "Cash flow al mes con su gestión",
                 "delegation_cost": "Lo que cuesta delegar al mes"}
MORTGAGE = {"fija": "la fija", "variable": "la variable"}
CSS = """
@page { size: A4; margin: 18mm 16mm 20mm;
        @bottom-right { content: "Página " counter(page) " de " counter(pages);
                        font: 8pt "Helvetica Neue", Helvetica, Arial, sans-serif; color: #666; }
        @bottom-left { content: "HouseFinder · plan de inversión";
                       font: 8pt "Helvetica Neue", Helvetica, Arial, sans-serif; color: #666; } }
body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 9.5pt;
       color: #1d1d1f; line-height: 1.4; }
h1 { font-size: 18pt; margin: 0 0 4pt; }
h2 { font-size: 12.5pt; margin: 16pt 0 6pt; padding-bottom: 3pt; border-bottom: 1px solid #ccc;
     break-after: avoid; }
h3 { font-size: 10.5pt; margin: 10pt 0 4pt; break-after: avoid; }
p, li { margin: 0 0 4pt; }
.meta { color: #555; }
.verdict { font-weight: bold; }
.pass { color: #1f7a4d; } .fail { color: #a33a1f; }
table { width: 100%; border-collapse: collapse; margin: 4pt 0 8pt; table-layout: fixed; }
table.figures col.name { width: 22%; } table.figures col.value { width: 21%; }
table.figures col.formula { width: 43%; } table.figures col.notes { width: 14%; }
table.rental col.type { width: 15%; } table.rental col.allowed { width: 9%; }
table.rental col.reduction { width: 12%; } table.rental col.management { width: 26%; }
table.rental col.figures { width: 38%; }
th, td { text-align: left; vertical-align: top; padding: 3pt 4pt;
         border-bottom: 1px solid #e3e3e3; }
th { font-size: 8.5pt; color: #555; font-weight: normal; }
td.value { white-space: nowrap; font-weight: bold; }
td.formula { color: #444; font-size: 8.5pt; }
.notes { font-size: 7.5pt; color: #555; }
.prov { font-size: 7pt; color: #8a5a00; text-transform: uppercase; }
.small { font-size: 8pt; color: #555; }
.url { font-size: 7.5pt; color: #555; word-break: break-all; }
ol.sources li { margin-bottom: 3pt; }
tr, li { break-inside: avoid; }
"""


def plan_html(plan: FullPlan, sources: SourceCatalog, today: date) -> str:
    title = plan.title or ("Oferta pegada" if plan.kind == "enlace" else "Lote del BOE")
    parts = [
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>",
        f"<title>Plan · {escape(title)}</title><style>{CSS}</style></head><body>",
        "<h1>Tu plan de inversión</h1>",
        f"<p class='meta'>{escape(title)}"
        + (" · subasta" if plan.auction else "")
        + f" · generado el {today.isoformat()}</p>",
    ]
    if plan.url:
        parts.append(f"<p class='url'>{escape(plan.url)}</p>")
    passes = plan.verdict.passes
    verdict = "Encaja con tu plan" if passes else "No encaja con tu plan"
    parts.append(f"<p class='verdict {'pass' if passes else 'fail'}'>{verdict}</p>")
    parts += _list(plan.verdict.reasons)
    parts.append("<p class='small'>Cifras calculadas con los datos de tu perfil y fuentes "
                 "públicas. Los números entre corchetes remiten al anexo de fuentes; lo marcado "
                 "como provisional depende de normas sin verificar o de supuestos.</p>")
    for section in plan.sections:
        parts.append(f"<h2>{escape(section.title)}</h2>")
        if section.id == "hipoteca" and plan.cheapest_mortgage:
            parts.append(
                f"<p>Con la trayectoria esperada del Euríbor paga menos intereses "
                f"{MORTGAGE.get(plan.cheapest_mortgage, plan.cheapest_mortgage)}; con la subida "
                f"de tipos, la cuota más alta es menor en "
                f"{MORTGAGE.get(plan.safest_mortgage or '', '—')}.</p>")
        parts.append(_table(section.figures, sources))
    if plan.pending is not None and plan.pending.changed:
        parts.append("<h2>Si se convalidan las normas pendientes</h2><table>"
                     "<tr><th>Cifra</th><th>Ahora</th><th>Con las normas pendientes</th>"
                     "<th>Cambio</th><th>Fuentes</th></tr>")
        for change in plan.pending.changed:
            parts.append(
                f"<tr><td>{escape(label(change.key))}</td>"
                f"<td class='value'>{_value(change.base)}</td>"
                f"<td class='value'>{_value(change.scenario)}</td>"
                f"<td class='value'>{_value(change.delta)}</td>"
                f"<td class='notes'>{_notes(change.delta, sources)}</td></tr>")
        parts.append("</table>")
    parts += _rental(plan, sources)
    parts.append("<h2>Argumentos para no comprar</h2>")
    if plan.arguments:
        parts.append("<ul>")
        for argument in plan.arguments:
            cited = ", ".join(escape(label(f.key)) for f in argument.figures)
            parts.append(f"<li>{escape(argument.text)}"
                         + (f" <span class='small'>({cited})</span>" if cited else "")
                         + "</li>")
        parts.append("</ul>")
    else:
        parts.append("<p>Las cifras del plan no dan ninguno.</p>")
    parts.append("<h2>Hoja de ruta de compra</h2><p class='small'>Pasos sin verificar todavía: "
                 "lee la fuente de cada uno.</p>")
    for stage, stage_title in STAGES.items():
        steps = [s for s in plan.roadmap if s.stage == stage]
        if not steps:
            continue
        parts.append(f"<h3>{stage_title}</h3><ol>")
        parts += [f"<li><strong>{escape(s.title)}.</strong> {escape(s.detail)} "
                  f"<span class='url'>{escape(s.source_url)}</span></li>" for s in steps]
        parts.append("</ol>")
    if plan.notes:
        parts.append("<h2>Avisos</h2>")
        parts += _list(plan.notes)
    parts.append("<h2>Fuentes</h2><ol class='sources'>")
    for entry in sources.entries:
        url = f" <span class='url'>{escape(entry.url)}</span>" if entry.url else ""
        prov = " <span class='prov'>provisional</span>" if entry.provisional else ""
        parts.append(f"<li value='{entry.number}'><strong>{escape(entry.kind)}:</strong> "
                     f"{escape(entry.title)}{prov}. {escape(entry.detail)}{url}</li>")
    parts.append("</ol></body></html>")
    return "".join(parts)


def plan_sources(conn: Connection, plan: FullPlan, rules: RuleBook,
                 params: ParamBook) -> SourceCatalog:
    """El anexo de fuentes de todas las cifras que salen en el PDF, en el orden del documento."""
    figures = [*plan.figures(),
               *(c.delta for c in (plan.pending.changed if plan.pending else ()))]
    ids = sorted({dataset_id(s) for f in figures for s in f.sources if s.kind == "dataset"})
    return catalog(figures, rules, params, sources_by_id(conn, ids))


def plan_pdf(html: str) -> bytes:
    from weasyprint import HTML  # necesita pango (ADR-0026): solo se carga al generar el PDF

    pdf = HTML(string=html).write_pdf()
    if pdf is None:  # write_pdf sin destino devuelve los bytes
        raise RuntimeError("WeasyPrint no ha devuelto el PDF")
    return pdf


def _rental(plan: FullPlan, sources: SourceCatalog) -> list[str]:
    if plan.advice is None:
        return []
    advice = plan.advice.advice
    parts = ["<h2>Tipo de alquiler y gestión</h2>"]
    if advice.recommended:
        parts.append(f"<p><strong>Recomendado: alquiler "
                     f"{escape(RENTAL_LABELS[advice.recommended])}.</strong></p>")
    parts += _list(advice.reasons)
    parts.append("<table class='rental'><col class='type'><col class='allowed'>"
                 "<col class='reduction'><col class='management'><col class='figures'>"
                 "<thead><tr><th>Tipo</th><th>¿Se puede?</th><th>Reducción del IRPF</th>"
                 "<th>Gestión</th><th>Cifras</th></tr></thead>")
    for t in advice.types:
        figures = "<br>".join(
            f"{RENTAL_FIGURE.get(f.key.split('.')[-1], escape(f.key))}: {_value(f)} "
            f"<span class='notes'>{_notes(f, sources)}</span>" for f in t.figures()) or "—"
        parts.append(
            f"<tr><td>{escape(RENTAL_LABELS[t.option.rental_type].capitalize())}</td>"
            f"<td>{'sí' if t.option.allowed else 'no'}</td>"
            f"<td>{REDUCTION[t.option.irpf_reduction]}</td>"
            f"<td>{escape(t.management_reason)}</td><td>{figures}</td></tr>")
    parts.append("</table>")
    chosen = advice.chosen()
    if chosen and chosen.option.requirements:
        kind = escape(RENTAL_LABELS[chosen.option.rental_type])
        parts.append(f"<h3>Requisitos del alquiler {kind}</h3><ul>")
        parts += [f"<li>{escape(r.description)} <span class='url'>{escape(r.source_url)}</span>"
                  "</li>" for r in chosen.option.requirements]
        parts.append("</ul>")
    others = (*plan.advice.notes, *plan.advice.scenario)
    if others:
        parts.append("<h3>Zona y normas pendientes</h3>")
        parts += _list(others)
    return parts


def _table(figures: Iterable[Figure], sources: SourceCatalog) -> str:
    rows = ["<table class='figures'><col class='name'><col class='value'><col class='formula'>"
            "<col class='notes'><thead><tr><th>Cifra</th><th>Valor</th><th>Cómo se calcula</th>"
            "<th>Fuentes</th></tr></thead>"]
    for f in figures:
        prov = " <span class='prov'>provisional</span>" if f.provisional else ""
        rows.append(f"<tr><td>{escape(label(f.key))}{prov}</td><td class='value'>{_value(f)}"
                    f"</td><td class='formula'>{escape(f.formula)}</td>"
                    f"<td class='notes'>{_notes(f, sources)}</td></tr>")
    rows.append("</table>")
    return "".join(rows)


def _value(f: Figure) -> str:
    text = escape(format_value(f.value, f.unit))
    if f.low is not None and f.high is not None:
        text += (f"<br><span class='small'>entre {escape(format_value(f.low, f.unit))} y "
                 f"{escape(format_value(f.high, f.unit))}</span>")
    return text


def _notes(f: Figure, sources: SourceCatalog) -> str:
    return "[" + ", ".join(str(n) for n in sources.notes(f)) + "]" if f.sources else ""


def _list(items: Iterable[str]) -> list[str]:
    items = list(items)
    if not items:
        return []
    return ["<ul>", *(f"<li>{escape(i)}</li>" for i in items), "</ul>"]
