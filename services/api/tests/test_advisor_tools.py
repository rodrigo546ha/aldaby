"""Herramientas del agente sobre los motores (F6.4, ADR-0019), con un modelo falso y las
referencias de prueba de test_offer_valuation (piso de 80 m² en venta por 400.000 €)."""

import json
from uuid import uuid4

import pytest
from test_offer_valuation import BOOK, confirmed_offer, database  # noqa: F401

from housefinder.advisor.tools import ask
from housefinder.agent.llm import ChatTurn, FakeLLMClient, ToolCall
from housefinder.agent.references import FigureSegment

pytestmark = pytest.mark.db
psycopg = pytest.importorskip("psycopg")


@pytest.fixture
def org(database):  # noqa: F811
    from housefinder.db.profiles import create_organization

    with psycopg.connect(database) as conn:
        org_id = create_organization(conn, f"Agente {uuid4()}", "particular")
        conn.commit()
    return org_id


def call(name, arguments, id_):
    return ChatTurn(None, (ToolCall(id_, name, json.dumps(arguments)),))


def test_el_agente_lista_valora_y_explica_con_marcadores(database, org):  # noqa: F811
    offer_id = confirmed_offer(database, org, "venta", "400000")
    scope = f"oferta_{offer_id.hex[:8]}"
    llm = FakeLLMClient(turns=[
        call("ofertas_guardadas", {}, "c1"),
        call("valorar_oferta", {"oferta_id": str(offer_id), "horizonte_anos": 10}, "c2"),
        ChatTurn(f"Piden {{{{fig:{scope}.offer.asking_price}}}}, que queda "
                 f"{{{{fig:{scope}.offer.asking_gap}}}} frente al precio estimado."),
    ])
    with psycopg.connect(database) as conn:
        answer = ask(conn, BOOK, llm, org, "¿Está cara mi oferta?")
    assert answer.failure is None
    assert [s.tool for s in answer.steps] == ["ofertas_guardadas", "valorar_oferta"]
    listed = json.loads(llm.chats[1][-1]["content"])["datos"]["ofertas"]
    assert listed[0]["oferta_id"] == str(offer_id) and listed[0]["ubicada"] is True
    cited = [s.figure for s in answer.segments if isinstance(s, FigureSegment)]
    assert [(f.key, str(f.value)) for f in cited] == [("offer.asking_price", "400000"),
                                                      ("offer.asking_gap", "-0.0817")]
    assert any("no es un margen de negociación" in n for n in answer.notes)


def test_oferta_ajena_o_sin_datos(database, org):  # noqa: F811
    foreign = uuid4()
    garage = confirmed_offer(database, org, "venta", "20000", property_type="garaje")
    llm = FakeLLMClient(turns=[
        call("valorar_oferta", {"oferta_id": str(foreign)}, "c1"),
        call("valorar_oferta", {"oferta_id": str(garage)}, "c2"),
        call("valorar_oferta", {"oferta_id": str(garage), "horizonte_anos": 7}, "c3"),
        ChatTurn("No puedo valorar esas ofertas."),
    ])
    with psycopg.connect(database) as conn:
        answer = ask(conn, BOOK, llm, org, "Valora mis ofertas")
    errors = [json.loads(m["content"])["error"] for m in llm.chats[-1] if m["role"] == "tool"]
    assert errors[0] == "No existe esa oferta entre las del usuario"
    assert "garaje" in errors[1]
    assert errors[2] == "Argumentos no válidos: horizonte_anos"  # opción fuera de la lista
    assert answer.figures == {}
