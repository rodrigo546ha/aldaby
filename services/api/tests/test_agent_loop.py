"""Bucle del agente con herramientas (ADR-0019) y cliente de chat del servidor propio, sin red."""

import json
from decimal import Decimal

import httpx
import pytest
from pydantic import BaseModel

from housefinder.agent.llm import (
    ChatTurn,
    FakeLLMClient,
    LLMOutputError,
    OpenAICompatibleLLMClient,
    ToolCall,
    ToolSpec,
)
from housefinder.agent.loop import Tool, ToolFailed, ToolResult, run_agent
from housefinder.agent.references import FigureSegment, TextSegment
from housefinder.core.figures import Figure

D = Decimal
RENT = Figure("valuation.rent_monthly", D("839.80"), "EUR/mes", "9,88 €/m² × 85 m²",
              low=D("718.25"), high=D("1037.00"))


class OfferArgs(BaseModel):
    oferta_id: str


def value(args: OfferArgs) -> ToolResult:
    if args.oferta_id == "garaje":
        raise ToolFailed("Solo se valoran viviendas")
    return ToolResult(figures=(RENT,), facts={"municipio": "Getafe"},
                      notes=("Renta de la sección censal.",), scope=f"oferta_{args.oferta_id}")


TOOLS = [Tool("valorar_oferta", "Renta y precio estimados de una oferta", OfferArgs, value)]


def call(arguments: str, name: str = "valorar_oferta", id_: str = "c1") -> ChatTurn:
    return ChatTurn(None, (ToolCall(id_, name, arguments),))


def test_pide_una_herramienta_y_explica_con_marcadores():
    llm = FakeLLMClient(turns=[
        call('{"oferta_id": "a1"}'),
        ChatTurn("La renta estimada es {{fig:oferta_a1.valuation.rent_monthly:range}}."),
    ])
    answer = run_agent(llm, "Eres un asesor.", "¿Cuánto se alquilaría?", TOOLS)
    assert answer.failure is None
    assert answer.segments == [TextSegment("La renta estimada es "),
                               FigureSegment(RENT, "range"), TextSegment(".")]
    assert answer.figures == {"oferta_a1.valuation.rent_monthly": RENT}
    assert answer.notes == ["Renta de la sección censal."]
    # El resultado vuelve al modelo como mensaje de herramienta, marcado como dato
    tool_message = llm.chats[1][-1]
    assert tool_message["role"] == "tool" and tool_message["tool_call_id"] == "c1"
    result = json.loads(tool_message["content"])
    assert result["cifras"][0] == {
        "clave": "oferta_a1.valuation.rent_monthly", "valor": "839.80", "unidad": "EUR/mes",
        "rango": ["718.25", "1037.00"], "formula": "9,88 €/m² × 85 m²"}
    assert result["datos"] == {"municipio": "Getafe"}
    assert "marcador" in llm.chats[0][0]["content"]  # las reglas de ADR-0012 van en el sistema


def test_texto_con_cifras_a_mano_se_reintenta_una_vez():
    llm = FakeLLMClient(turns=[
        call('{"oferta_id": "a1"}'),
        ChatTurn("Se alquilaría por unos 840 € al mes."),
        ChatTurn("Se alquilaría por {{fig:oferta_a1.valuation.rent_monthly}}."),
    ])
    answer = run_agent(llm, "x", "¿Renta?", TOOLS)
    assert answer.failure is None and len(answer.segments) == 3
    retry = llm.chats[2][-1]
    assert retry["role"] == "user" and "número escrito a mano" in retry["content"]


def test_si_vuelve_a_fallar_quedan_las_cifras_sin_texto():
    llm = FakeLLMClient(turns=[
        call('{"oferta_id": "a1"}'), ChatTurn("Unos 840 €."), ChatTurn("Ya te dije, 840 €."),
    ])
    answer = run_agent(llm, "x", "¿Renta?", TOOLS)
    assert answer.segments is None and answer.failure == "texto_rechazado"
    assert len(answer.rejected) == 2 and "número escrito a mano" in answer.rejected[0][0]
    assert "oferta_a1.valuation.rent_monthly" in answer.figures


def test_errores_de_herramienta_vuelven_al_modelo():
    llm = FakeLLMClient(turns=[
        call('{"oferta_id": "garaje"}', id_="c1"),
        call('{"oferta": 1}', id_="c2"),  # argumentos que no validan
        call("{}", name="borrar_todo", id_="c3"),  # herramienta que no existe
        call("no es json", id_="c4"),
        ChatTurn("No he podido valorarla."),
    ])
    answer = run_agent(llm, "x", "Valora el garaje", TOOLS)
    assert answer.failure is None and answer.figures == {}
    errors = [json.loads(m["content"])["error"] for m in llm.chats[-1] if m["role"] == "tool"]
    assert errors[0] == "Solo se valoran viviendas"
    assert errors[1].startswith("Argumentos no válidos")
    assert errors[2] == "No existe la herramienta «borrar_todo»"
    assert errors[3].startswith("Argumentos no válidos")
    assert [s.ok for s in answer.steps] == [False, False, False, False]


def test_pasos_agotados_y_modelo_caido():
    llm = FakeLLMClient(turns=[call('{"oferta_id": "a1"}', id_=f"c{i}") for i in range(3)])
    answer = run_agent(llm, "x", "?", TOOLS, max_steps=3)
    assert answer.failure == "pasos_agotados" and answer.segments is None
    assert run_agent(FakeLLMClient(), "x", "?", TOOLS).failure == "modelo_no_disponible"


# --- Cliente de chat del servidor propio contra un transporte simulado -----------------------


def server(reply: dict, status: int = 200):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=reply)

    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def test_chat_con_herramientas_en_formato_openai():
    reply = {"choices": [{"finish_reason": "tool_calls", "message": {
        "role": "assistant", "content": "",
        "tool_calls": [{"id": "call_1", "type": "function", "function": {
            "name": "valorar_oferta", "arguments": '{"oferta_id": "a1"}'}}]}}]}
    http, seen = server(reply)
    client = OpenAICompatibleLLMClient("http://llm.test/v1", "qwen3:8b", client=http)
    spec = ToolSpec("valorar_oferta", "Valora", OfferArgs.model_json_schema())
    turn = client.chat([{"role": "user", "content": "hola"}], [spec])
    assert turn == ChatTurn(None, (ToolCall("call_1", "valorar_oferta", '{"oferta_id": "a1"}'),))
    body = json.loads(seen[0].content)
    assert body["temperature"] == 0
    assert body["tools"] == [{"type": "function", "function": {
        "name": "valorar_oferta", "description": "Valora",
        "parameters": OfferArgs.model_json_schema()}}]
    assert turn.as_message()["tool_calls"][0]["function"]["name"] == "valorar_oferta"


def test_chat_argumentos_como_objeto_y_respuestas_malas():
    reply = {"choices": [{"message": {"content": None, "tool_calls": [
        {"function": {"name": "valorar_oferta", "arguments": {"oferta_id": "a1"}}}]}}]}
    http, _ = server(reply)
    turn = OpenAICompatibleLLMClient("http://llm.test/v1", "m", client=http).chat([], [])
    assert turn.tool_calls[0] == ToolCall("llamada-0", "valorar_oferta", '{"oferta_id": "a1"}')
    for bad in ({"choices": []}, {"choices": [{"message": {"tool_calls": [{"x": 1}]}}]},
                {"choices": [{"message": {"content": "a"}, "finish_reason": "length"}]}):
        http, _ = server(bad)
        with pytest.raises(LLMOutputError):
            OpenAICompatibleLLMClient("http://llm.test/v1", "m", client=http).chat([], [])
