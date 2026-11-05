"""Herramientas del agente sobre los motores (F6.4, ADR-0019).

Todas son de lectura y reciben referencias, nunca números: el identificador de una oferta del
usuario y opciones cerradas. Las cifras salen de lo que el usuario confirmó, de los motores de
valoración y territorio y de los parámetros. Si falta algo, la herramienta lo dice y el agente se
lo pregunta al usuario.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from housefinder.advisor.glossary import describe
from housefinder.agent.llm import LLMClient, Message
from housefinder.agent.loop import (
    AgentAnswer,
    Progress,
    Tool,
    ToolFailed,
    ToolResult,
    run_agent,
)
from housefinder.agent.plan_arguments import extra_arguments
from housefinder.agent.references import without_numbers
from housefinder.core.figures import Figure
from housefinder.db.connection import Connection
from housefinder.db.offers import (
    PrivateOffer,
    get_private_offer,
    list_private_offers,
    search_candidates,
)
from housefinder.params.book import ParamBook
from housefinder.plans.service import FullPlan, PlanUnavailable, full_plan
from housefinder.profiles.model import UserProfile
from housefinder.regulation.rules import RuleBook
from housefinder.search.service import SearchUnavailable, search
from housefinder.territory.service import Location, SectionNotFound, territory_at
from housefinder.valuation.offer import CannotValue, value_offer
from housefinder.valuation.service import OutsideCoverage

INSTRUCTIONS = """Eres el asesor de Aldaby, una plataforma independiente que no vende
inmuebles. Ayudas a un inversor particular a entender las ofertas que ha guardado: cuánto se
alquilarían, cuánto valen frente a lo que piden, cómo puede evolucionar su precio y cómo es la zona.

- Usa las herramientas para obtener cada dato; no supongas nada que no te devuelvan.
- Si el usuario nombra una oferta por su municipio, busca su oferta_id con ofertas_guardadas y
  úsalo: no se lo pidas.
- Si el usuario pregunta por una oferta que está confirmada y ubicada, valórala directamente:
  no le pidas que lo confirme.
- Si una herramienta dice que falta un dato, explícale al usuario qué tiene que confirmar.
- Explica con frases cortas y claras, en español, y di los límites de cada estimación (rangos y
  supuestos). Los avisos de las herramientas se muestran solos debajo de tu respuesta: no hagas
  una lista de avisos ni los copies.
- Contesta en pocas frases, unas seis como mucho, y no repitas ninguna.
- No le digas al usuario que compre o que no compre: explícale lo que dicen las cifras.
- Si pregunta qué ofertas le encajan, usa buscar_ofertas: el orden lo hace el programa con su plan;
  tú explicas por qué cada una está donde está, con sus motivos.
- Si pide su plan completo de una oferta, usa plan_completo: explica su capacidad, la hipoteca,
  el cash flow, la prueba de estrés, las normas pendientes y los argumentos para no comprar que
  da el programa, sin dejar ninguno.
- Si pregunta cómo alquilar una oferta (habitual, temporada, habitaciones o turístico) o si
  delegar la gestión, usa recomendar_alquiler con el identificador de su marcador: la
  recomendación la hace el programa; tú la explicas con sus motivos y requisitos.
"""
# Forma de la explicación del plan (ADR-0052): la web la pinta en fichas
PLAN_OUTPUT = """
Cuando tengas el plan, contesta solo con un objeto JSON, sin texto alrededor, con esta forma:
{"resumen": "una frase con lo que dicen las cifras para este usuario",
 "claves": [{"titulo": "pocas palabras y sin cifras", "texto": "una o dos frases con marcadores",
             "cifra": "{{fig:clave}}"}],
 "riesgos": ["una frase por riesgo"],
 "siguiente_paso": "una frase con lo primero que conviene hacer"}
- «claves» son las tres cosas más importantes del plan para este usuario, de más a menos
  importante: por ejemplo lo que le queda cada mes, lo que pone de su bolsillo o qué pasa si suben
  los tipos. Cada una dice algo distinto.
- «cifra» es solo el marcador de la cifra que resume la ficha, sin texto; si ninguna la resume,
  null.
- «riesgos»: hasta tres, de la prueba de estrés, las normas pendientes y los argumentos para no
  comprar que da el programa. No repitas lo que ya dicen las fichas.
- «siguiente_paso»: el primer paso de la hoja de ruta del plan, dicho en una frase.
"""
PLAN_FIGURE = r"^\{\{fig:[a-z0-9_]+(\.[a-z0-9_]+)+\}\}$"
SEARCH_FIGURES = ("offer.price", "valuation.rent_monthly", "cashflow.monthly_after_tax",
                  "search.stressed_cashflow", "irr.rate", "cashflow.cash_invested")
SEARCH_SHOWN = 5  # las primeras del orden: el contexto del modelo es corto
# Partes de clave con números, dichas sin ellos: el modelo nombra el indicador por su clave
# («población de sesenta y cinco…») y el texto se rechaza (ADR-0012)
SPOKEN = {"poblacion_65_y_mas": "poblacion_mayor", "poblacion_menor_18": "poblacion_menor_de_edad",
          "change_5y": "cambio_lustro"}


class KeyPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(description="Lo importante en pocas palabras, sin cifras ni marcadores")
    texto: str = Field(description="Una o dos frases con marcadores {{fig:clave}}")
    cifra: str | None = Field(default=None, pattern=PLAN_FIGURE,
                              description="El marcador de la cifra que resume la ficha")

    @field_validator("titulo")
    @classmethod
    def _plain(cls, value: str) -> str:
        if "{{" in value:
            raise ValueError("el título va sin marcadores: la cifra va en «cifra»")
        return value


class PlanExplanation(BaseModel):
    """La explicación del plan en fichas (ADR-0052); cada texto pasa `check_text`."""

    model_config = ConfigDict(extra="forbid")

    resumen: str = Field(description="Una frase con lo que dicen las cifras")
    claves: list[KeyPoint] = Field(min_length=1, max_length=3)
    riesgos: list[str] = Field(default_factory=list, max_length=3)
    siguiente_paso: str


class NoArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OfferArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    oferta_id: UUID = Field(description="Identificador de la oferta, de ofertas_guardadas")


class MarkerArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    oferta: str = Field(
        pattern=r"^[0-9a-fA-F]{8}(-?[0-9a-fA-F]{4}){0,3}(-?[0-9a-fA-F]{12})?$",
        description="La oferta: los ocho caracteres de su marcador {{oferta:…}} de "
                    "buscar_ofertas, o su oferta_id de ofertas_guardadas")

    def short(self) -> str:
        return self.oferta.replace("-", "").lower()[:8]


class ValuationArguments(OfferArguments):
    horizonte_anos: Literal[5, 10, 15, 20] = Field(
        default=10, description="Años de los escenarios de revalorización")


PlanGate = Callable[[UUID], str | None]  # None: se puede ver el plan; si no, el motivo


def offer_tools(conn: Connection, book: ParamBook, org_id: UUID,
                profile: UserProfile | None = None, rules: RuleBook | None = None,
                plan_gate: PlanGate | None = None) -> list[Tool]:
    """`plan_gate`: el cupo del nivel gratuito (ADR-0041). Sin él, el plan completo no se limita
    (profesionales, terminal y evaluaciones)."""
    def own(offer_id: UUID) -> PrivateOffer:
        offer = get_private_offer(conn, offer_id, org_id)
        if offer is None:
            raise ToolFailed("No existe esa oferta entre las del usuario")
        return offer

    def saved(_: NoArguments) -> ToolResult:
        offers = []
        named: dict[str, str] = {}
        for o in list_private_offers(conn, org_id):
            confirmed = (o.extracted or {}).get("confirmed") or {}
            # El municipio, para que el usuario pueda decir «la de Getafe»; la dirección no, que
            # lleva números y el modelo no la necesita
            town = ((confirmed.get("fields") or {}).get("municipality") or {}).get("value")
            # El marcador corto para nombrarla en el texto (F6.9: qwen3 escribía el UUID entero)
            named[o.id.hex[:8]] = o.title or "Oferta pegada"
            offers.append({"oferta_id": str(o.id), "marcador": f"{{{{oferta:{o.id.hex[:8]}}}}}",
                           "titulo": o.title, "municipio": town,
                           "estado": o.extraction_status, "operacion": confirmed.get("operation"),
                           "ubicada": o.property_id is not None})
        return ToolResult(facts={"ofertas": offers}, offers=named)

    def valuation(args: ValuationArguments) -> ToolResult:
        offer = own(args.oferta_id)
        try:
            valued = value_offer(conn, book, offer, args.horizonte_anos)
        except (CannotValue, OutsideCoverage) as exc:
            raise ToolFailed(str(exc)) from exc
        return ToolResult(figures=tuple(valued.figures), notes=tuple(valued.notes),
                          facts={"titulo": offer.title,
                                 "renta_de": valued.report.level},
                          scope=_scope(offer), keys=_spoken_keys(valued.figures),
                          descriptions=describe(valued.figures))

    def zone(args: OfferArguments) -> ToolResult:
        offer = own(args.oferta_id)
        if offer.lon is None or offer.lat is None:
            raise ToolFailed("La oferta no está ubicada: el usuario tiene que confirmar la "
                             "dirección o la referencia catastral")
        try:
            report = territory_at(conn, Location(offer.lon, offer.lat))
        except SectionNotFound as exc:
            raise ToolFailed(str(exc)) from exc
        return ToolResult(figures=tuple(report.figures), notes=tuple(report.notes),
                          facts={"titulo": offer.title}, scope=_scope(offer),
                          keys=_spoken_keys(report.figures), descriptions=describe(report.figures))

    def find(_: NoArguments) -> ToolResult:
        if profile is None or rules is None:
            raise ToolFailed("El usuario no ha confirmado su perfil: tiene que hacerlo en /perfil")
        try:
            report = search(conn, book, rules, profile, org_id)
        except SearchUnavailable as exc:
            raise ToolFailed("; ".join(exc.reasons)) from exc
        keyed: dict[str, Figure] = {}
        offers: dict[str, str] = {}
        facts = []
        for position, scored in enumerate(report.ranked[:SEARCH_SHOWN], 1):
            short = scored.offer_id.hex[:8]
            offers[short] = scored.title or ("Oferta pegada" if scored.kind == "enlace"
                                             else "Lote del BOE")
            for figure in scored.figures:
                if figure.key in SEARCH_FIGURES:
                    keyed[f"oferta_{short}.{figure.key}"] = figure
            chosen = scored.advice.advice.chosen() if scored.advice else None
            facts.append({"marcador": f"{{{{oferta:{short}}}}}", "puesto": position,
                          "pasa": scored.verdict.passes, "motivos": list(scored.verdict.reasons),
                          "origen": "suya" if scored.kind == "enlace" else "subasta del BOE",
                          # El detalle de cada tipo, con recomendar_alquiler (F6.6)
                          "alquiler_recomendado": chosen.option.rental_type if chosen else None,
                          "gestion_recomendada": chosen.management if chosen else None})
        shown = [*report.market, *keyed.values()]
        notes = list(report.notes)
        if report.skipped:
            notes.append("Hay ofertas que no se han podido puntuar (otro tipo de inmueble, sin "
                         "precio o sin superficie).")
        return ToolResult(figures=report.market, keyed=keyed, offers=offers,
                          facts={"ofertas": facts, "orden": "según el objetivo del usuario"},
                          notes=tuple(notes), descriptions=describe(shown))

    def rental(args: MarkerArguments) -> ToolResult:
        if profile is None or rules is None:
            raise ToolFailed("El usuario no ha confirmado su perfil: tiene que hacerlo en /perfil")
        try:
            report = search(conn, book, rules, profile, org_id)
        except SearchUnavailable as exc:
            raise ToolFailed("; ".join(exc.reasons)) from exc
        short = args.short()
        scored = next((s for s in report.ranked if s.offer_id.hex.startswith(short)), None)
        if scored is None:
            raise ToolFailed("Esa oferta no está entre las que se pueden puntuar: usa antes "
                             "buscar_ofertas")
        if scored.advice is None:
            raise ToolFailed("No hay recomendación de tipo de alquiler para esa oferta")
        advice = scored.advice.advice
        # Los requisitos van por su código: sus descripciones llevan números (ADR-0012)
        types = [{"tipo": t.option.rental_type, "se_puede": t.option.allowed,
                  "reduccion_irpf": {True: "sí", False: "no", None: "por confirmar"}
                  [t.option.irpf_reduction],
                  "gestion": t.management, "motivo_gestion": t.management_reason,
                  "con_cifras": t.cashflow is not None,
                  "requisitos": [without_numbers(r.code) for r in t.option.requirements]}
                 for t in advice.types]
        figures = advice.figures()
        notes = (*scored.advice.notes, *scored.advice.scenario,
                 *(n for t in advice.types for n in t.notes))
        return ToolResult(figures=figures, notes=notes,
                          offers={short: scored.title or ("Oferta pegada"
                                                          if scored.kind == "enlace"
                                                          else "Lote del BOE")},
                          facts={"oferta": f"{{{{oferta:{short}}}}}",
                                 "recomendado": advice.recommended,
                                 "motivos": list(advice.reasons), "tipos": types},
                          descriptions=describe(figures))

    def full(args: MarkerArguments) -> ToolResult:
        if profile is None or rules is None:
            raise ToolFailed("El usuario no ha confirmado su perfil: tiene que hacerlo en /perfil")
        offer_id = _offer_id(args.short())
        if offer_id is None:
            raise ToolFailed("Esa oferta no está entre las que se pueden puntuar: usa antes "
                             "buscar_ofertas")
        refusal = plan_gate(offer_id) if plan_gate is not None else None
        if refusal is not None:
            raise ToolFailed(refusal)
        try:
            plan = full_plan(conn, book, rules, profile, org_id, offer_id)
        except SearchUnavailable as exc:
            raise ToolFailed("; ".join(exc.reasons)) from exc
        except PlanUnavailable as exc:
            raise ToolFailed(str(exc)) from exc
        return plan_result(plan)

    def _offer_id(short: str) -> UUID | None:
        return next((c.offer_id for c in search_candidates(conn, org_id)
                     if c.offer_id.hex.startswith(short)), None)

    return [
        Tool("plan_completo", "Plan completo del usuario para una oferta: capacidad, hipoteca "
             "fija y variable, cash flow, prueba de estrés, normas pendientes, tipo de alquiler, "
             "argumentos para no comprar y hoja de ruta.", MarkerArguments, full),
        Tool("recomendar_alquiler", "Tipo de alquiler (habitual, temporada, habitaciones o "
             "turístico) y gestión recomendados para una oferta de buscar_ofertas, con la "
             "normativa de cada tipo y lo que cuesta delegar.", MarkerArguments, rental),
        Tool("buscar_ofertas", "Ofertas que encajan con el plan del usuario (su capacidad, su "
             "riesgo y su objetivo), en orden, con los motivos de las que no pasan.",
             NoArguments, find),
        Tool("ofertas_guardadas", "Ofertas que el usuario ha guardado, con su estado: solo las "
             "confirmadas y ubicadas se pueden valorar.", NoArguments, saved),
        Tool("valorar_oferta", "Renta y precio estimados de una oferta confirmada, escenarios de "
             "revalorización y lo que pide el anuncio frente a lo estimado.",
             ValuationArguments, valuation),
        Tool("zona_de_oferta", "Renta de los hogares, población y su evolución en la sección "
             "censal de una oferta ubicada.", OfferArguments, zone),
    ]


PLAN_FIGURES = ("affordability.max_price", "offer.price", "purchase_costs.total",
                "cashflow.cash_invested", "financing.loan", "financing.years",
                "mortgage.monthly_payment", "assumption.mortgage_rate",
                "mortgage.stressed_payment", "valuation.rent_monthly",
                "cashflow.monthly_after_tax", "search.stressed_cashflow",
                "plan.low_rent_cashflow", "term.recommended_years", "irr.rate",
                "mortgage_comparison.fija.expected_total_interest",
                "mortgage_comparison.variable.expected_total_interest")
STAGES = {"antes": "antes de comprometerte", "compra": "la compra", "despues": "después"}


def plan_result(plan: FullPlan) -> ToolResult:
    """Lo que el modelo ve del plan: las cifras clave con su descripción, los argumentos y los
    pasos en palabras (sin números: las cifras van con marcador, ADR-0012)."""
    every = {f.key: f for f in plan.figures()}
    chosen = [every[k] for k in PLAN_FIGURES if k in every]
    picked = plan.advice.advice.chosen() if plan.advice else None
    extra = [*(picked.figures() if picked else ()),
             *(f for a in plan.arguments for f in a.figures)]
    figures = list({f.key: f for f in (*chosen, *extra)}.values())
    keys = {f.key: "normas_pendientes.cash_flow" for f in figures
            if f.key.startswith("scenario.")}
    short = plan.offer_id.hex[:8]
    facts = {
        "oferta": f"{{{{oferta:{short}}}}}",
        "encaja": plan.verdict.passes, "motivos": list(plan.verdict.reasons),
        "hipoteca_mas_barata": plan.cheapest_mortgage,
        "hipoteca_mas_segura_en_estres": plan.safest_mortgage,
        "alquiler_recomendado": picked.option.rental_type if picked else None,
        "gestion_recomendada": picked.management if picked else None,
        "argumentos_para_no_comprar": [
            {"argumento": a.text,
             "cifras": [keys.get(f.key, f.key) for f in a.figures]} for a in plan.arguments],
        "hoja_de_ruta": [f"{STAGES[s.stage]}: {without_numbers(s.title)}" for s in plan.roadmap],
    }
    notes = plan.notes
    if plan.pending is not None and plan.pending.changed:
        notes = (*notes, "Si se convalidan las normas pendientes cambian cifras del plan.")
    return ToolResult(figures=tuple(figures), facts=facts, notes=tuple(notes), keys=keys,
                      offers={short: plan.title or ("Oferta pegada" if plan.kind == "enlace"
                                                    else "Lote del BOE")},
                      descriptions=describe(figures))


def plan_summary(plan: FullPlan) -> str:
    """El plan en palabras y sin cifras, para los argumentos que añade el asesor."""
    picked = plan.advice.advice.chosen() if plan.advice else None
    lines = [
        "Inmueble: " + ("subasta del BOE" if plan.auction else "vivienda de un anuncio"),
        "Encaja con sus restricciones: " + ("sí" if plan.verdict.passes else
                                            "no (" + "; ".join(plan.verdict.reasons) + ")"),
    ]
    if picked:
        lines.append(f"Alquiler recomendado: {picked.option.rental_type}, gestión "
                     f"{picked.management}")
    lines.append("Argumentos ya calculados:")
    lines += [f"- {a.text}" for a in plan.arguments]
    return without_numbers("\n".join(lines))


@dataclass(frozen=True)
class ExplainedPlan:
    answer: AgentAnswer
    extra_arguments: list[str]


def explain_plan(conn: Connection, book: ParamBook, llm: LLMClient, org_id: UUID,
                 plan: FullPlan, profile: UserProfile, rules: RuleBook,
                 progress: Callable[[Progress], None] | None = None,
                 plan_gate: PlanGate | None = None) -> ExplainedPlan:
    """El asesor explica el plan en fichas con marcadores (ADR-0052) y añade sus argumentos
    (ADR-0025). `answer.output` es un `PlanExplanation` si el texto pasa la comprobación."""
    short = plan.offer_id.hex[:8]
    question = (f"Explícame mi plan completo para la oferta {{{{oferta:{short}}}}} (usa "
                f"plan_completo con oferta {short}): qué puedo pagar, la hipoteca, lo que me "
                "queda cada mes, qué pasa si suben los tipos y por qué podría no comprarla.")
    answer = run_agent(llm, INSTRUCTIONS + PLAN_OUTPUT, question,
                       offer_tools(conn, book, org_id, profile, rules, plan_gate),
                       output=PlanExplanation, progress=progress)
    if progress is not None:
        progress(Progress("argumentos"))
    extra = extra_arguments(llm, plan_summary(plan), [a.text for a in plan.arguments])
    return ExplainedPlan(answer, extra)


# Conversación en la web (ADR-0063): las cifras de las vueltas anteriores no se pueden citar
CONVERSATION = """
- Es una conversación: puedes leer tus respuestas anteriores, pero sus marcadores ya no valen. Si
  vuelves a citar una cifra, pide otra vez la herramienta que la calcula.
- Contesta solo a la última pregunta.
"""


def ask_about_offer(conn: Connection, book: ParamBook, llm: LLMClient, org_id: UUID,
                    offer_id: UUID, question: str, history: Sequence[Message] = (),
                    profile: UserProfile | None = None, rules: RuleBook | None = None,
                    progress: Callable[[Progress], None] | None = None,
                    plan_gate: PlanGate | None = None) -> AgentAnswer:
    """Una pregunta sobre una oferta en la conversación de su plan (ADR-0063)."""
    short = offer_id.hex[:8]
    framed = (f"Pregunta sobre la oferta {{{{oferta:{short}}}}} (para su plan, usa plan_completo "
              f"con oferta {short}): {question}")
    return run_agent(llm, INSTRUCTIONS + CONVERSATION, framed,
                     offer_tools(conn, book, org_id, profile, rules, plan_gate),
                     progress=progress, history=history)


def ask_in_plan(conn: Connection, book: ParamBook, llm: LLMClient, org_id: UUID, question: str,
                history: Sequence[Message] = (), profile: UserProfile | None = None,
                rules: RuleBook | None = None,
                progress: Callable[[Progress], None] | None = None,
                plan_gate: PlanGate | None = None) -> AgentAnswer:
    """Una pregunta en la conversación general de «Mi plan», sin oferta fija (ADR-0066)."""
    return run_agent(llm, INSTRUCTIONS + CONVERSATION, question,
                     offer_tools(conn, book, org_id, profile, rules, plan_gate),
                     progress=progress, history=history)


def ask(conn: Connection, book: ParamBook, llm: LLMClient, org_id: UUID, question: str,
        profile: UserProfile | None = None, rules: RuleBook | None = None) -> AgentAnswer:
    """Una pregunta del usuario sobre sus ofertas, contestada con las herramientas."""
    return run_agent(llm, INSTRUCTIONS, question,
                     offer_tools(conn, book, org_id, profile, rules))


def _scope(offer: PrivateOffer) -> str:
    """Prefijo de las claves de una oferta: con varias ofertas, la misma cifra no se pisa."""
    return f"oferta_{offer.id.hex[:8]}"


def _spoken_keys(figures: Sequence[Figure]) -> dict[str, str]:
    """Clave del Figure → clave sin números para el modelo, solo las que cambian."""
    keys = {}
    for figure in figures:
        spoken = ".".join(SPOKEN.get(part, part) for part in figure.key.split("."))
        if spoken != figure.key:
            keys[figure.key] = spoken
    return keys
