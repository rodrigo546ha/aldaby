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
        ChatTurn(f"Para {{{{oferta:{short}}}}} puedes pagar hasta "
                 "{{fig:affordability.max_price}} y la cuota sería "
                 "{{fig:mortgage.monthly_payment}}."),
    ])
    with psycopg.connect(searchable) as conn:
        user = profile(management_fee_rate=D("0.08"))
        plan = full_plan(conn, book(), rules(), user, org, offer, TODAY)
        explained = explain_plan(conn, book(), llm, org, plan, user, rules())
    assert explained.answer.failure is None, explained.answer.rejected
    assert explained.extra_arguments == [
        "Una sola vivienda concentra todo tu ahorro en un activo poco líquido."]
    sent = json.loads(llm.chats[1][-1]["content"])
    assert all("descripcion" in c for c in sent["cifras"])
    assert sent["datos"]["argumentos_para_no_comprar"]
    shown = json.dumps(sent["datos"], ensure_ascii=False)
    assert not any(ch.isdigit() for ch in shown.replace(short, "")), shown


@pytest.mark.db
def test_api_del_plan(searchable, org):  # noqa: F811
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
        ChatTurn("Te queda {{fig:cashflow.monthly_after_tax}}."),
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
        explained = client.post(f"/plans/offers/{offer}/explanation").json()
        assert explained["failure"] is None
        assert [s["kind"] for s in explained["segments"]] == ["text", "figure", "text"]
        assert explained["extra_arguments"] == []  # el modelo falso no responde
    finally:
        app.dependency_overrides.clear()


def client_of(conn, org):  # noqa: F811
    """El único cliente de la organización de prueba (ADR-0029): la API lo usa sin elegirlo."""
    from conftest import add_client

    row = conn.execute("SELECT id FROM clients WHERE org_id = %s", (org,)).fetchone()
    return row[0] if row else add_client(conn, org)
