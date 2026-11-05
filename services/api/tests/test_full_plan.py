"""Plan completo de una oferta (F6.7, ADR-0025): secciones, fija y variable, estrés, normas
pendientes, argumentos para no comprar y hoja de ruta."""

from datetime import date
from decimal import Decimal

import pytest
from test_offer_valuation import database  # noqa: F401
from test_plan_assumptions import references  # noqa: F401
from test_reverse_search import book, org, profile, rules, searchable  # noqa: F401

psycopg = pytest.importorskip("psycopg")

D = Decimal
TODAY = date(2026, 10, 31)


@pytest.mark.db
def test_plan_completo_de_una_oferta(searchable, org):  # noqa: F811
    from test_offer_valuation import confirmed_offer

    from housefinder.plans.service import full_plan

    offer = confirmed_offer(searchable, org, "venta", "150000")
    with psycopg.connect(searchable) as conn:
        plan = full_plan(conn, book(), rules(), profile(management_fee_rate=D("0.08")), org,
                         offer, TODAY)
    sections = {s.id: {f.key for f in s.figures} for s in plan.sections}
    assert list(sections) == ["capacidad", "compra", "hipoteca", "explotacion", "estres",
                              "venta", "supuestos"]
    assert {"affordability.max_price", "affordability.max_payment"} <= sections["capacidad"]
    assert {"mortgage_comparison.fija.expected_total_interest",
            "mortgage_comparison.variable.stressed_max_payment",
            "assumption.variable_spread"} <= sections["hipoteca"]
    assert {"mortgage.stressed_payment", "search.stressed_cashflow",
            "plan.low_rent_cashflow", "term.recommended_years"} <= sections["estres"]
    assert plan.cheapest_mortgage in ("fija", "variable")
    # La venta parte del precio pagado acotado al precio estimado de la oferta (ADR-0059)
    base = next(f for s in plan.sections for f in s.figures if f.key == "irr.sale_base")
    assert "P25" in base.formula and any(s.kind == "dataset" for s in base.sources)
    assert "irr.sale_base" in sections["venta"]
    # Cada clave una vez en todo el plan, todas con fuente
    keys = [f.key for f in plan.figures()]
    assert len(keys) == len(set(keys)) and all(f.sources for f in plan.figures())
    # Cifras provisionales (reglas sin verificar): siempre está ese argumento
    assert "cifras-provisionales" in {a.code for a in plan.arguments}
    assert plan.pending is not None and plan.pending.name == "normas-pendientes"
    assert plan.advice is not None and plan.advice.advice.recommended == "habitual"
    steps = [s.id for s in plan.roadmap]
    assert steps[0] == "nota-simple" and "arras" in steps and "fianza" in steps
    assert "subasta-deposito" not in steps


@pytest.mark.db
def test_reforma_y_avisos_de_estado_y_antiguedad(searchable, org):  # noqa: F811
    # Decisión de Rodrigo (2026-11-05): avisos y reforma, sin descuentos por estado o antigüedad
    import json

    from test_offer_valuation import confirmed_offer

    from housefinder.db.offers import set_renovation
    from housefinder.plans.service import full_plan

    offer = confirmed_offer(searchable, org, "venta", "150000")
    with psycopg.connect(searchable) as conn:
        conn.execute(
            "UPDATE offers SET extracted = jsonb_set(extracted, '{confirmed,fields}', "
            "extracted->'confirmed'->'fields' || %s::jsonb) WHERE id = %s",
            (json.dumps({"condition": {"value": "A reformar", "origin": "extraido"},
                         "year_built": {"value": "1965", "origin": "extraido"}}), offer))
        conn.commit()
        plain = full_plan(conn, book(), rules(), profile(), org, offer, TODAY)
        set_renovation(conn, org, offer, D(30000))
        conn.commit()
        reformed = full_plan(conn, book(), rules(), profile(), org, offer, TODAY)
    assert any("«A reformar»" in n and "Indica lo que costaría" in n for n in plain.notes)
    assert any(f"El edificio es de 1965 ({TODAY.year - 1965} años, según el anuncio)" in n
               for n in plain.notes)
    assert any("suma la reforma que has indicado" in n for n in reformed.notes)
    figures = {f.key: f for s in reformed.sections for f in s.figures}
    plain_figures = {f.key: f for s in plain.sections for f in s.figures}
    assert figures["purchase_costs.renovation"].value == D("30000.00")
    assert "purchase_costs.renovation" in {f.key for s in reformed.sections if s.id == "compra"
                                           for f in s.figures}
    assert "purchase_costs.renovation" not in plain_figures
    assert (figures["cashflow.cash_invested"].value
            - plain_figures["cashflow.cash_invested"].value) == D(30000)
    # La valoración no cambia: la reforma no la sube ni el estado la baja
    assert figures["valuation.price_total"].value == plain_figures["valuation.price_total"].value


@pytest.mark.db
def test_sin_cupo_el_asesor_no_cuenta_el_plan(searchable, org):  # noqa: F811
    # ADR-0041: la herramienta plan_completo pregunta al cupo antes de calcular el plan
    from test_offer_valuation import confirmed_offer

    from housefinder.advisor.tools import MarkerArguments, offer_tools
    from housefinder.agent.loop import ToolFailed

    offer = confirmed_offer(searchable, org, "venta", "150000")
    asked: list[object] = []

    def gate(offer_id):
        asked.append(offer_id)
        return "Has usado los 3 planes completos del nivel gratuito."

    with psycopg.connect(searchable) as conn:
        tools = {t.name: t for t in offer_tools(conn, book(), org, profile(), rules(), gate)}
        with pytest.raises(ToolFailed, match="planes completos"):
            tools["plan_completo"].run(MarkerArguments(oferta=offer.hex[:8]))
        free = {t.name: t for t in offer_tools(conn, book(), org, profile(), rules())}
        assert free["plan_completo"].run(MarkerArguments(oferta=offer.hex[:8])).figures
    assert asked == [offer]


@pytest.mark.db
def test_plan_de_una_oferta_que_no_es_suya(searchable, org):  # noqa: F811
    from uuid import uuid4

    from housefinder.plans.service import PlanUnavailable, full_plan

    with psycopg.connect(searchable) as conn, pytest.raises(PlanUnavailable):
        full_plan(conn, book(), rules(), profile(), org, uuid4(), TODAY)


@pytest.mark.db
def test_el_asesor_explica_el_plan_y_anade_argumentos(searchable, org):  # noqa: F811
    import json

    from test_offer_valuation import confirmed_offer

    from housefinder.advisor.tools import explain_plan
    from housefinder.agent.llm import ChatTurn, FakeLLMClient, ToolCall
    from housefinder.agent.plan_arguments import ExtraArguments
    from housefinder.plans.service import full_plan

    offer = confirmed_offer(searchable, org, "venta", "150000")
    short = offer.hex[:8]
    given = "Hay cifras provisionales: dependen de normas sin verificar o de supuestos estimados."

    def respond(instructions, document, output):
        assert not any(ch.isdigit() for ch in document)  # el resumen va sin cifras
        return ExtraArguments(argumentos=[
            "Una sola vivienda concentra todo tu ahorro en un activo poco líquido.",
            "Si el inquilino deja de pagar 3 meses, lo notarás.",  # con dígitos: fuera
            given])  # repite uno del programa: fuera

    llm = FakeLLMClient(respond=respond, turns=[
        ChatTurn(None, (ToolCall("c1", "plan_completo", json.dumps({"oferta": short})),)),
        ChatTurn(json.dumps({
            "resumen": f"Para {{{{oferta:{short}}}}} puedes pagar hasta "
                       "{{fig:affordability.max_price}}.",
            "claves": [{"titulo": "La cuota", "texto": "Sería de "
                        "{{fig:mortgage.monthly_payment}}.",
                        "cifra": "{{fig:mortgage.monthly_payment}}"}],
            "riesgos": ["Si suben los tipos, la cuota sube."],
            "siguiente_paso": "Pide la nota simple."}, ensure_ascii=False)),
    ])
    with psycopg.connect(searchable) as conn:
        user = profile(management_fee_rate=D("0.08"))
        plan = full_plan(conn, book(), rules(), user, org, offer, TODAY)
        explained = explain_plan(conn, book(), llm, org, plan, user, rules())
    assert explained.answer.failure is None, explained.answer.rejected
    assert explained.answer.output.claves[0].cifra == "{{fig:mortgage.monthly_payment}}"
    assert "esta forma" in llm.chats[0][0]["content"]  # el esquema de las fichas (ADR-0052)
    assert explained.extra_arguments == [
        "Una sola vivienda concentra todo tu ahorro en un activo poco líquido."]
    sent = json.loads(llm.chats[1][-1]["content"])
    assert all("descripcion" in c for c in sent["cifras"])
    assert sent["datos"]["argumentos_para_no_comprar"]
    shown = json.dumps(sent["datos"], ensure_ascii=False)
    assert not any(ch.isdigit() for ch in shown.replace(short, "")), shown


@pytest.mark.db
def test_api_del_plan(searchable, org):  # noqa: F811
    import json
    import os

    from fastapi.testclient import TestClient
    from test_offer_valuation import confirmed_offer

    from housefinder.agent.llm import ChatTurn, FakeLLMClient, ToolCall
    from housefinder.api.deps import (
        get_db,
        get_keys,
        get_llm,
        get_org,
        get_param_book,
        get_rule_book,
    )
    from housefinder.api.main import app
    from housefinder.crypto.envelope import LocalKeyProvider
    from housefinder.profiles import store

    keys = LocalKeyProvider({"prueba": os.urandom(32)}, "prueba")
    offer = confirmed_offer(searchable, org, "venta", "150000")
    short = offer.hex[:8]
    llm = FakeLLMClient(turns=[
        ChatTurn(None, (ToolCall("c1", "plan_completo", f'{{"oferta": "{short}"}}'),)),
        ChatTurn('{"resumen": "Te queda {{fig:cashflow.monthly_after_tax}}.", "claves": '
                 '[{"titulo": "Cada mes", "texto": "Lo que te queda.", '
                 '"cifra": "{{fig:cashflow.monthly_after_tax}}"}], "riesgos": [], '
                 '"siguiente_paso": "Pide la nota simple."}'),
    ])

    def db():
        with psycopg.connect(searchable) as conn:
            yield conn

    app.dependency_overrides.update({get_db: db, get_keys: lambda: keys, get_org: lambda: org,
                                     get_param_book: book, get_rule_book: rules,
                                     get_llm: lambda: llm})
    try:
        client = TestClient(app)
        assert client.get(f"/plans/offers/{offer}").status_code == 409  # sin cliente
        with psycopg.connect(searchable) as conn:
            client_of(conn, org)
            conn.commit()
        assert client.get(f"/plans/offers/{offer}").status_code == 404  # sin perfil
        assert client.get("/plans/conversation").status_code == 404  # «Mi plan», sin asesor
        with psycopg.connect(searchable) as conn:
            store.save_new(conn, keys, org, client_of(conn, org), profile())
            conn.commit()
        plan = client.get(f"/plans/offers/{offer}").json()
        assert plan["sections"][0]["id"] == "capacidad"
        assert plan["roadmap"][0]["id"] == "nota-simple"
        assert any(a["code"] == "cifras-provisionales" for a in plan["arguments"])
        pdf = client.get(f"/plans/offers/{offer}/pdf")
        try:
            import weasyprint  # noqa: F401
        except OSError:  # sin pango: la API lo dice (ADR-0026)
            assert pdf.status_code == 503
        else:
            assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
            assert pdf.headers["cache-control"] == "no-store"
            assert pdf.headers["content-disposition"].endswith(f'plan-{short}.pdf"')
        # Etapas mientras trabaja y, al final, las fichas ya comprobadas (ADR-0052)
        streamed = client.post(f"/plans/offers/{offer}/explanation")
        assert streamed.headers["content-type"].startswith("text/event-stream")
        assert "no-transform" in streamed.headers["cache-control"]
        events = [(block.split("\n")[0].removeprefix("event: "),
                   json.loads(block.split("\n")[1].removeprefix("data: ")))
                  for block in streamed.text.strip().split("\n\n")]
        assert [e for e in events if e[0] == "etapa"][:2] == [
            ("etapa", {"etapa": "modelo", "herramienta": None}),
            ("etapa", {"etapa": "herramienta", "herramienta": "plan_completo"})]
        name, explained = events[-1]
        assert name == "resultado" and explained["failure"] is None
        assert [s["kind"] for s in explained["summary"]] == ["text", "figure", "text"]
        card = explained["cards"][0]
        assert card["title"] == "Cada mes"
        assert card["figure"]["key"] == "cashflow.monthly_after_tax"
        assert explained["next_step"] == [{"kind": "text", "text": "Pide la nota simple.",
                                           "figure": None, "part": None, "offer": None,
                                           "label": None}]
        assert explained["extra_arguments"] == []  # el modelo falso no responde
        # Simulador de puja (ADR-0047): sin valor de subasta en una venta, 404; con él, la tabla
        assert client.post(f"/plans/offers/{offer}/bids", json={}).status_code == 404
        bids = client.post(f"/plans/offers/{offer}/bids",
                           json={"auction_value": "150000", "judicial": True,
                                 "charges": [{"concept": "Hipoteca anterior", "amount": "2500"},
                                             {"concept": "", "amount": "0"}]}).json()
        assert len(bids["levels"]) == 7 and float(bids["deposit"]["value"]) == 30000
        assert float(bids["charges"]["value"]) == 2500  # la de 0 € no cuenta
        assert all(level["stage"] for level in bids["levels"])
        # Preguntas sobre el plan (ADR-0063) en una conversación guardada cifrada (ADR-0064)
        def ask(question: str, answer: str) -> dict:
            llm.turns.extend([
                ChatTurn(None, (ToolCall("c2", "plan_completo", f'{{"oferta": "{short}"}}'),)),
                ChatTurn(answer),
            ])
            asked = client.post(f"/plans/offers/{offer}/questions", json={"question": question})
            assert asked.headers["content-type"].startswith("text/event-stream")
            name, answered = [(block.split("\n")[0].removeprefix("event: "),
                               json.loads(block.split("\n")[1].removeprefix("data: ")))
                              for block in asked.text.strip().split("\n\n")][-1]
            assert name == "resultado" and answered["failure"] is None
            return answered

        first = "Te queda {{fig:cashflow.monthly_after_tax}}."
        assert ask("¿Qué me queda al mes?", first)["text"] == first
        second = "Con el habitual te quedarían {{fig:cashflow.monthly_after_tax}}."
        answered = ask("¿Y si lo alquilo?", second)
        assert [s["kind"] for s in answered["answer"]] == ["text", "figure", "text"]
        # El historial lo pone el servidor con lo guardado, no la web
        seen = llm.chats[-2]  # la primera llamada de la segunda pregunta
        assert seen[1:3] == [{"role": "user", "content": "¿Qué me queda al mes?"},
                             {"role": "assistant", "content": first}]
        assert f"{{{{oferta:{short}}}}}" in seen[3]["content"]
        saved = client.get(f"/plans/offers/{offer}/conversation").json()
        assert [t["question"] for t in saved["turns"]] == ["¿Qué me queda al mes?",
                                                         "¿Y si lo alquilo?"]
        assert saved["turns"][1]["answer"]["text"] == second and saved["retention_days"] == 30
        # Consultas de hoy (ADR-0065): la explicación y las dos preguntas
        assert saved["advisor_left"] == 200 - 3
        with psycopg.connect(searchable) as conn:  # en la base, solo bytes cifrados
            stored = bytes(conn.execute(
                "SELECT data_enc FROM advisor_conversations WHERE offer_id = %s", (offer,)
            ).fetchone()[0])
        assert b"alquilo" not in stored
        too_long = {"question": "x" * 501}
        assert client.post(f"/plans/offers/{offer}/questions", json=too_long).status_code == 422
        assert client.delete(f"/plans/offers/{offer}/conversation").status_code == 204
        assert client.get(f"/plans/offers/{offer}/conversation").json()["turns"] == []
        # «Mi plan», sin oferta fija (ADR-0066): su conversación va aparte y lleva su historial
        def ask_general(question: str, answer: str) -> dict:
            llm.turns.append(ChatTurn(answer))
            asked = client.post("/plans/questions", json={"question": question})
            name, answered = [(block.split("\n")[0].removeprefix("event: "),
                               json.loads(block.split("\n")[1].removeprefix("data: ")))
                              for block in asked.text.strip().split("\n\n")][-1]
            assert name == "resultado" and answered["failure"] is None
            return answered

        ask_general("¿Por dónde empiezo?", "Mira primero las ofertas que encajan.")
        ask_general("¿Y después?", "Abre su plan.")
        seen = llm.chats[-1]
        assert seen[1:3] == [{"role": "user", "content": "¿Por dónde empiezo?"},
                             {"role": "assistant",
                              "content": "Mira primero las ofertas que encajan."}]
        general = client.get("/plans/conversation").json()
        assert [t["question"] for t in general["turns"]] == ["¿Por dónde empiezo?", "¿Y después?"]
        assert client.get(f"/plans/offers/{offer}/conversation").json()["turns"] == []
        assert client.delete("/plans/conversation").status_code == 204
        assert client.get("/plans/conversation").json()["turns"] == []
        # Al llegar al límite del día, 429 antes de llamar al modelo (ADR-0065); la pregunta
        # demasiado larga no contó
        with psycopg.connect(searchable) as conn:
            conn.execute("UPDATE advisor_uses SET uses = 200 WHERE org_id = %s", (org,))
            conn.commit()
        calls = len(llm.chats)
        limited = client.post(f"/plans/offers/{offer}/questions", json={"question": "¿Y ahora?"})
        assert limited.status_code == 429 and "200 consultas" in limited.json()["detail"]
        assert client.post(f"/plans/offers/{offer}/explanation").status_code == 429
        assert client.post("/plans/questions", json={"question": "¿Y ahora?"}).status_code == 429
        assert len(llm.chats) == calls
        assert client.get(f"/plans/offers/{offer}/conversation").json()["advisor_left"] == 0
    finally:
        app.dependency_overrides.clear()


def client_of(conn, org):  # noqa: F811
    """El único cliente de la organización de prueba (ADR-0029): la API lo usa sin elegirlo."""
    from conftest import add_client

    row = conn.execute("SELECT id FROM clients WHERE org_id = %s", (org,)).fetchone()
    return row[0] if row else add_client(conn, org)
