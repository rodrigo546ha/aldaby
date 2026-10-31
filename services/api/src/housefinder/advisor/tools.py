"""Herramientas del agente sobre los motores (F6.4, ADR-0019).

Todas son de lectura y reciben referencias, nunca números: el identificador de una oferta del
usuario y opciones cerradas. Las cifras salen de lo que el usuario confirmó, de los motores de
valoración y territorio y de los parámetros. Si falta algo, la herramienta lo dice y el agente se
lo pregunta al usuario.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from housefinder.agent.llm import LLMClient
from housefinder.agent.loop import AgentAnswer, Tool, ToolFailed, ToolResult, run_agent
from housefinder.db.connection import Connection
from housefinder.db.offers import PrivateOffer, get_private_offer, list_private_offers
from housefinder.params.book import ParamBook
from housefinder.territory.service import Location, SectionNotFound, territory_at
from housefinder.valuation.offer import CannotValue, value_offer
from housefinder.valuation.service import OutsideCoverage

INSTRUCTIONS = """Eres el asesor de HouseFinder, una plataforma independiente que no vende
inmuebles. Ayudas a un inversor particular a entender las ofertas que ha guardado: cuánto se
alquilarían, cuánto valen frente a lo que piden, cómo puede evolucionar su precio y cómo es la zona.

- Usa las herramientas para obtener cada dato; no supongas nada que no te devuelvan.
- Si una herramienta dice que falta un dato, explícale al usuario qué tiene que confirmar.
- Explica con frases cortas y claras, en español, y di los límites de cada estimación (rangos,
  supuestos, avisos de las herramientas).
- No le digas al usuario que compre o que no compre: explícale lo que dicen las cifras.
"""


class NoArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OfferArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    oferta_id: UUID = Field(description="Identificador de la oferta, de ofertas_guardadas")


class ValuationArguments(OfferArguments):
    horizonte_anos: Literal[5, 10, 15, 20] = Field(
        default=10, description="Años de los escenarios de revalorización")


def offer_tools(conn: Connection, book: ParamBook, org_id: UUID) -> list[Tool]:
    def own(offer_id: UUID) -> PrivateOffer:
        offer = get_private_offer(conn, offer_id, org_id)
        if offer is None:
            raise ToolFailed("No existe esa oferta entre las del usuario")
        return offer

    def saved(_: NoArguments) -> ToolResult:
        offers = [{"oferta_id": str(o.id), "titulo": o.title, "estado": o.extraction_status,
                   "operacion": ((o.extracted or {}).get("confirmed") or {}).get("operation"),
                   "ubicada": o.property_id is not None}
                  for o in list_private_offers(conn, org_id)]
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
                          scope=_scope(offer))

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
                          facts={"titulo": offer.title}, scope=_scope(offer))

    return [
        Tool("ofertas_guardadas", "Ofertas que el usuario ha guardado, con su estado: solo las "
             "confirmadas y ubicadas se pueden valorar.", NoArguments, saved),
        Tool("valorar_oferta", "Renta y precio estimados de una oferta confirmada, escenarios de "
             "revalorización y lo que pide el anuncio frente a lo estimado.",
             ValuationArguments, valuation),
        Tool("zona_de_oferta", "Renta de los hogares, población y su evolución en la sección "
             "censal de una oferta ubicada.", OfferArguments, zone),
    ]


def ask(conn: Connection, book: ParamBook, llm: LLMClient, org_id: UUID,
        question: str) -> AgentAnswer:
    """Una pregunta del usuario sobre sus ofertas, contestada con las herramientas."""
    return run_agent(llm, INSTRUCTIONS, question, offer_tools(conn, book, org_id))


def _scope(offer: PrivateOffer) -> str:
    """Prefijo de las claves de una oferta: con varias ofertas, la misma cifra no se pisa."""
    return f"oferta_{offer.id.hex[:8]}"
