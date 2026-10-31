"""Búsqueda inversa (F6.5): restricciones según el riesgo, orden según el objetivo, y el plan del
usuario en cada oferta con los supuestos de las fuentes públicas."""

from decimal import Decimal

import pytest
from test_offer_valuation import database  # noqa: F401
from test_plan_assumptions import references  # noqa: F401

from housefinder.core.figures import Figure
from housefinder.planning.ranking import Outcome, judge, rank, stress_rent

D = Decimal


def cash(value: str) -> Figure:
    return Figure("cashflow.monthly_after_tax", D(value), "EUR/mes", "x")


def outcome(base="100", stressed="20", irr="0.05", budget=True, savings=True) -> Outcome:
    return Outcome(cash(base), None if stressed is None else Figure(
        "search.stressed_cashflow", D(stressed), "EUR/mes", "x"),
        Figure("irr.rate", D(irr), "ratio", "x") if irr else None, budget, savings)


def test_la_prueba_de_estres_depende_del_riesgo():
    assert stress_rent("baja") == "p25"
    assert stress_rent("media") == stress_rent(None) == "mediana"
    assert stress_rent("alta") is None


def test_restricciones_con_sus_motivos():
    assert judge(outcome(), "media", "renta", D(0)).passes
    failed = judge(outcome(base="50", stressed="-10", budget=False, savings=False), "baja",
                   "renta", D(60))
    assert not failed.passes
    assert failed.reasons == (
        "El precio pasa de tu capacidad de compra",
        "No te llega el ahorro para la entrada y los gastos",
        "El cash flow no llega a tu mínimo",
        "Con la subida de tipos y la renta baja de la zona el cash flow no llega a tu mínimo")
    # Riesgo alto: sin prueba de estrés
    assert judge(outcome(stressed=None), "alta", "renta", D(0)).passes


def test_orden_por_objetivo_y_primero_las_que_pasan():
    verdicts = {
        "a": judge(outcome(base="300", irr="0.03"), "media", "renta", D(0)),
        "b": judge(outcome(base="150", irr="0.08"), "media", "renta", D(0)),
        "c": judge(outcome(base="900", budget=False), "media", "renta", D(0)),  # no pasa
    }
    assert rank(verdicts) == ["a", "b", "c"]  # renta: por cash flow
    by_irr = {k: judge(outcome(base=b, irr=i), "media", "patrimonio", D(0))
              for k, b, i in [("a", "300", "0.03"), ("b", "150", "0.08"), ("n", "200", None)]}
    assert rank(by_irr) == ["b", "a", "n"]  # patrimonio: por TIR; sin TIR, al final


# --- Contra la base temporal ------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")


@pytest.fixture
def searchable(database, references):  # noqa: F811
    """Las referencias de valoración (test_offer_valuation) y de los supuestos
    (test_plan_assumptions) sobre el mismo municipio de prueba, 28993."""
    return database


@pytest.fixture
def org(searchable):
    from uuid import uuid4

    from housefinder.db.profiles import create_organization

    with psycopg.connect(searchable) as conn:
        org_id = create_organization(conn, f"Búsqueda {uuid4()}", "particular")
        conn.commit()
    return org_id


def rules():
    from housefinder.regulation.rules import RuleBook, _parse_rule, default_rules_dir

    book = RuleBook.from_dir(default_rules_dir())
    ibi = _parse_rule({"id": "ibi-28993", "kind": "tipo_ibi", "territory": "ES-13-28993",
                       "effective_from": "2026-01-01", "effective_to": None,
                       "status": "vigente", "verified": False, "params": {"rate": 0.005},
                       "source_url": "https://example", "notes": "prueba"})
    return RuleBook([*book.rules, ibi])


def book():
    """Los parámetros del proyecto: criterios bancarios, Euríbor y valoración."""
    from housefinder.params.book import ParamBook, default_params_dir

    return ParamBook.from_dir(default_params_dir())


def profile(**overrides):
    from housefinder.profiles.model import UserProfile

    base = dict(net_monthly_income=D("4500"), existing_monthly_debt=D(0),
                available_savings=D("150000"), birth_year=1985, residence="ES-13",
                taxable_base=D("50000"), goal="renta", risk_tolerance="media",
                management="activa", vacancy_rate=D("0.05"), other_purchase_cost_rate=D("0.005"),
                sale_cost_rate=D("0.03"), min_monthly_cashflow=D("-1000"), large_holder=False)
    return UserProfile(**(base | overrides))


@pytest.mark.db
def test_busqueda_con_el_plan_del_usuario(searchable, org):
    from test_offer_valuation import confirmed_offer

    from housefinder.search.service import search

    cheap = confirmed_offer(searchable, org, "venta", "150000")
    dear = confirmed_offer(searchable, org, "venta", "900000")
    garage = confirmed_offer(searchable, org, "venta", "20000", property_type="garaje")
    with psycopg.connect(searchable) as conn:
        report = search(conn, book(), rules(), profile(), org)
    assert [s.offer_id for s in report.ranked] == [cheap, dear], report.skipped
    first, second = report.ranked
    assert first.verdict.passes and first.verdict.metric.key == "cashflow.monthly_after_tax"
    assert "El precio pasa de tu capacidad de compra" in second.verdict.reasons
    keys = {f.key for f in first.figures}
    assert {"offer.price", "valuation.rent_monthly", "search.stressed_cashflow",
            "assumption.cadastral_value", "holding_costs.ibi_annual"} <= keys
    ibi = next(f for f in first.figures if f.key == "holding_costs.ibi_annual")
    assert ibi.value == D("450.00")  # 90.000 € de valor catastral estimado × 0,5 %
    assert any("plusvalía" in n for n in first.notes)  # el municipio de prueba no tiene regla
    assert [s.offer_id for s in report.skipped] == [garage]
    assert report.market[0].key == "assumption.mortgage_rate"


@pytest.mark.db
def test_sin_lo_necesario_dice_que_falta(searchable, org):
    from housefinder.search.service import SearchUnavailable, search

    with psycopg.connect(searchable) as conn, pytest.raises(SearchUnavailable) as exc:
        search(conn, book(), rules(), profile(taxable_base=None, sale_cost_rate=None,
                                            management="pasiva"), org)
    assert exc.value.reasons == [
        "Falta tu base liquidable general: sube tu declaración de la renta o escríbela en el "
        "perfil",
        "Faltan supuestos de búsqueda en tu perfil: los gastos de venta, lo que cobra la gestión"]


@pytest.mark.db
def test_api_de_busqueda(searchable, org):
    import os

    from fastapi.testclient import TestClient
    from test_offer_valuation import confirmed_offer

    from housefinder.api.deps import get_db, get_keys, get_org, get_param_book, get_rule_book
    from housefinder.api.main import app
    from housefinder.crypto.envelope import LocalKeyProvider
    from housefinder.profiles import store

    keys = LocalKeyProvider({"prueba": os.urandom(32)}, "prueba")

    def db():
        with psycopg.connect(searchable) as conn:
            yield conn

    app.dependency_overrides.update({get_db: db, get_keys: lambda: keys, get_org: lambda: org,
                                     get_param_book: book, get_rule_book: rules})
    try:
        client = TestClient(app)
        assert client.get("/search").status_code == 404  # sin perfil confirmado
        offer = confirmed_offer(searchable, org, "venta", "150000")
        with psycopg.connect(searchable) as conn:
            store.save_new(conn, keys, org, "local", profile(vacancy_rate=None))
            conn.commit()
        missing = client.get("/search")
        assert missing.status_code == 422 and "meses vacío" in missing.json()["detail"][0]
        with psycopg.connect(searchable) as conn:
            store.save_new(conn, keys, org, "local", profile())
            conn.commit()
        found = client.get("/search").json()
        assert [r["offer_id"] for r in found["ranked"]] == [str(offer)]
        assert found["ranked"][0]["passes"] is True
        assert found["market"][0]["key"] == "assumption.mortgage_rate"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.db
def test_herramienta_del_agente(searchable, org):
    import json

    from test_offer_valuation import confirmed_offer

    from housefinder.advisor.tools import ask
    from housefinder.agent.llm import ChatTurn, FakeLLMClient, ToolCall
    from housefinder.agent.references import OfferSegment

    offer = confirmed_offer(searchable, org, "venta", "150000")
    short = offer.hex[:8]
    llm = FakeLLMClient(turns=[
        ChatTurn(None, (ToolCall("c1", "buscar_ofertas", "{}"),)),
        ChatTurn(f"Te encaja {{{{oferta:{short}}}}}: te deja "
                 f"{{{{fig:oferta_{short}.cashflow.monthly_after_tax}}}}."),
    ])
    with psycopg.connect(searchable) as conn:
        answer = ask(conn, book(), llm, org, "¿Qué ofertas me encajan?", profile(), rules())
    assert answer.failure is None
    assert any(isinstance(s, OfferSegment) and s.offer == short for s in answer.segments)
    sent = json.loads(llm.chats[1][-1]["content"])
    assert sent["datos"]["ofertas"][0] == {"marcador": f"{{{{oferta:{short}}}}}", "puesto": 1,
                                         "pasa": True, "motivos": [], "origen": "suya"}
    assert all("descripcion" in c for c in sent["cifras"])  # el glosario cubre lo que se envía
    # Sin perfil, la herramienta lo dice
    llm = FakeLLMClient(turns=[ChatTurn(None, (ToolCall("c1", "buscar_ofertas", "{}"),)),
                               ChatTurn("Confirma tu perfil.")])
    with psycopg.connect(searchable) as conn:
        ask(conn, book(), llm, org, "¿Qué me encaja?")
    assert "perfil" in json.loads(llm.chats[1][-1]["content"])["error"]
