from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from housefinder.api.deps import get_param_book
from housefinder.api.main import app
from housefinder.params.book import ParamBook

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_affordability_devuelve_cifras_trazables():
    resp = client.post(
        "/simulate/affordability",
        json={
            "net_monthly_income": 4000,
            "available_savings": 60000,
            "age": 30,
            "annual_rate": 0.03,
            "purchase_cost_rate": 0.10,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["max_price"]["key"] == "affordability.max_price"
    assert body["max_price"]["value"] == "150000.00"
    assert body["max_price"]["formula"]
    # Criterios bancarios y tasa de gastos de compra aún sin fuente firme: provisional.
    assert body["max_price"]["provisional"] is True
    kinds = {s["kind"] for s in body["max_price"]["sources"]}
    assert {"param", "user_input"} <= kinds


def test_affordability_usa_los_criterios_del_repositorio():
    resp = client.post(
        "/simulate/affordability",
        json={
            "net_monthly_income": 4000,
            "available_savings": 60000,
            "age": 30,
            "annual_rate": 0.03,
            "purchase_cost_rate": 0.10,
        },
    )
    ids = {s["id"] for s in resp.json()["max_price"]["sources"]}
    assert "criterios-bancarios-por-defecto" in ids


def test_affordability_sin_criterios_vigentes_responde_503():
    app.dependency_overrides[get_param_book] = lambda: ParamBook([])
    try:
        resp = client.post(
            "/simulate/affordability",
            json={
                "net_monthly_income": 4000,
                "available_savings": 60000,
                "age": 30,
                "annual_rate": 0.03,
                "purchase_cost_rate": 0.10,
            },
        )
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 503


# --- Inversión de punta a punta (F1.10) ---------------------------------------------------

PLAN = Path(__file__).parent / "fixtures" / "planes" / "sintetico-01.yaml"


def peticion(**changes) -> dict:
    body = yaml.safe_load(PLAN.read_text(encoding="utf-8"))["request"]
    for path, value in changes.items():
        section, field = path.split("__")
        body[section][field] = value
    return body


def test_inversion_devuelve_cifras_por_clave_y_avisos():
    resp = client.post("/simulate/investment", json=peticion())
    assert resp.status_code == 200
    body = resp.json()
    fig = body["figures"]["cashflow.monthly_after_tax"]
    assert fig["unit"] == "EUR/mes" and fig["formula"] and fig["sources"]
    assert fig["provisional"] is True  # reglas sin verificar
    assert body["within_budget"] is True
    assert body["term_feasible"] is True
    assert any("PROVISIONALES" in w for w in body["warnings"])
    assert body["comparison"] is None


def test_inversion_con_escenario_normativo():
    situation = {"contract": "primer-alquiler", "large_holder": False, "young_tenant": True}
    body = client.post(
        "/simulate/investment",
        json=peticion(rental__contract_date="2026-12-15", rental__situation=situation),
    ).json()
    scenario = body["pending_scenario"]
    assert scenario["name"] == "normativa-pendiente"
    assert "cashflow.annual_tax" in {c["key"] for c in scenario["changes"]}
    assert "irpf-reduccion-alquiler-rdl-29-2026" in {r["id"] for r in scenario["new_rules"]}


def test_inversion_con_ofertas_alternativas():
    offers = [
        {"label": "fija", "initial_rate": 0.03, "initial_months": 600},
        {"label": "variable", "initial_rate": 0.025, "initial_months": 12, "spread": 0.008},
    ]
    body = client.post("/simulate/investment", json=peticion(financing__alternatives=offers))
    comparison = body.json()["comparison"]
    assert comparison["labels"] == ["fija", "variable"]
    assert "mortgage_comparison.variable.first_payment" in body.json()["figures"]


def test_inversion_sin_base_ni_tipo_marginal_es_422():
    resp = client.post("/simulate/investment", json=peticion(buyer__taxable_base=None))
    assert resp.status_code == 422
    assert "base liquidable" in resp.json()["detail"]


def test_inversion_vivienda_nueva_con_iva_y_ajd():
    resp = client.post("/simulate/investment", json=peticion(property__new_build=True))
    assert resp.status_code == 200
    figures = resp.json()["figures"]
    assert {"purchase_costs.vat", "purchase_costs.stamp_duty"} <= figures.keys()


def test_inversion_sin_reglas_del_territorio_es_503():
    # Barcelona: no hay ITP cargado.
    resp = client.post("/simulate/investment", json=peticion(property__territory="ES-09-08019"))
    assert resp.status_code == 503
    assert "impuesto_compra_segunda_mano" in resp.json()["detail"]


def test_inversion_sin_revalorizacion_usa_los_escenarios_del_municipio():
    # F5.5: sin revalorización, base al plan y TIR de los otros dos escenarios
    from decimal import Decimal

    from housefinder.api.deps import get_scenario_finder
    from housefinder.core.figures import Figure, SourceRef
    from housefinder.valuation.scenarios import AppreciationReport, Scenario

    calls = []
    sources = (SourceRef("dataset", "ine-ipv-80270@2026T2"),
               SourceRef("model", "escenarios-revalorizacion-v1"))

    def find(municipality, horizon_years, new_build):
        calls.append((municipality, horizon_years, new_build))
        rates = {"conservative": "-0.0009", "base": "0.0203", "optimistic": "0.0599"}
        return AppreciationReport(
            scenarios={k: Scenario(k, Decimal(v), sources) for k, v in rates.items()},
            figures=[Figure(f"valuation.appreciation_{k}", Decimal(v), "ratio", "prueba",
                            sources) for k, v in rates.items()],
            notes=["Ciclo de la comunidad: prueba"])

    app.dependency_overrides[get_scenario_finder] = lambda: find
    try:
        body = client.post("/simulate/investment",
                           json=peticion(exit__appreciation_rate=None)).json()
        bad = client.post("/simulate/investment", json=peticion(
            exit__appreciation_rate=None, property__territory="ES-13"))
    finally:
        app.dependency_overrides.clear()
    figures = body["figures"]
    assert calls == [("28079", 10, False)]
    irr = {k: Decimal(figures[f"irr.rate{k}"]["value"])
           for k in ("_conservative", "", "_optimistic")}
    assert irr["_conservative"] < irr[""] < irr["_optimistic"]
    assert figures["valuation.appreciation_base"]["value"] == "0.0203"
    assert body["appreciation_notes"] == ["Ciclo de la comunidad: prueba"]
    assert bad.status_code == 422
