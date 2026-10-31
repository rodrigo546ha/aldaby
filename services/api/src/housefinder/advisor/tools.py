"""Herramientas del agente sobre los motores (F6.4, ADR-0019).

Todas son de lectura y reciben referencias, nunca números: el identificador de una oferta del
usuario y opciones cerradas. Las cifras salen de lo que el usuario confirmó, de los motores de
valoración y territorio y de los parámetros. Si falta algo, la herramienta lo dice y el agente se
lo pregunta al usuario.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from housefinder.advisor.glossary import describe
from housefinder.agent.llm import LLMClient
from housefinder.agent.loop import AgentAnswer, Tool, ToolFailed, ToolResult, run_agent
from housefinder.core.figures import Figure
from housefinder.db.connection import Connection
from housefinder.db.offers import PrivateOffer, get_private_offer, list_private_offers
from housefinder.params.book import ParamBook
from housefinder.profiles.model import UserProfile
from housefinder.regulation.rules import RuleBook
from housefinder.search.service import SearchUnavailable, search
from housefinder.territory.service import Location, SectionNotFound, territory_at
from housefinder.valuation.offer import CannotValue, value_offer
from housefinder.valuation.service import OutsideCoverage

INSTRUCTIONS = """Eres el asesor de HouseFinder, una plataforma independiente que no vende
inmuebles. Ayudas a un inversor particular a entender las ofertas que ha guardado: cuánto se
alquilarían, cuánto valen frente a lo que piden, cómo puede evolucionar su precio y cómo es la zona.

- Usa las herramientas para obtener cada dato; no supongas nada que no te devuelvan.
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
"""
SEARCH_FIGURES = ("offer.price", "valuation.rent_monthly", "cashflow.monthly_after_tax",
                  "search.stressed_cashflow", "irr.rate", "cashflow.cash_invested")
SEARCH_SHOWN = 5  # las primeras del orden: el contexto del modelo es corto
# Partes de clave con números, dichas sin ellos: el modelo nombra el indicador por su clave
# («población de sesenta y cinco…») y el texto se rechaza (ADR-0012)
SPOKEN = {"poblacion_65_y_mas": "poblacion_mayor", "poblacion_menor_18": "poblacion_menor_de_edad",
          "change_5y": "cambio_lustro"}


class NoArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OfferArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    oferta_id: UUID = Field(description="Identificador de la oferta, de ofertas_guardadas")


class ValuationArguments(OfferArguments):
    horizonte_anos: Literal[5, 10, 15, 20] = Field(
        default=10, description="Años de los escenarios de revalorización")


def offer_tools(conn: Connection, book: ParamBook, org_id: UUID,
                profile: UserProfile | None = None, rules: RuleBook | None = None) -> list[Tool]:
    def own(offer_id: UUID) -> PrivateOffer:
        offer = get_private_offer(conn, offer_id, org_id)
        if offer is None:
            raise ToolFailed("No existe esa oferta entre las del usuario")
        return offer

    def saved(_: NoArguments) -> ToolResult:
        offers = []
        for o in list_private_offers(conn, org_id):
            confirmed = (o.extracted or {}).get("confirmed") or {}
            # El municipio, para que el usuario pueda decir «la de Getafe»; la dirección no, que
            # lleva números y el modelo no la necesita
            town = ((confirmed.get("fields") or {}).get("municipality") or {}).get("value")
            offers.append({"oferta_id": str(o.id), "titulo": o.title, "municipio": town,
                           "estado": o.extraction_status, "operacion": confirmed.get("operation"),
                           "ubicada": o.property_id is not None})
        return ToolResult(facts={"ofertas": offers})

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
            facts.append({"marcador": f"{{{{oferta:{short}}}}}", "puesto": position,
                          "pasa": scored.verdict.passes, "motivos": list(scored.verdict.reasons),
                          "origen": "suya" if scored.kind == "enlace" else "subasta del BOE"})
        shown = [*report.market, *keyed.values()]
        notes = list(report.notes)
        if report.skipped:
            notes.append("Hay ofertas que no se han podido puntuar (otro tipo de inmueble, sin "
                         "precio o sin superficie).")
        return ToolResult(figures=report.market, keyed=keyed, offers=offers,
                          facts={"ofertas": facts, "orden": "según el objetivo del usuario"},
                          notes=tuple(notes), descriptions=describe(shown))

    return [
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
