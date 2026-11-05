"""Fuentes de las cifras para leerlas en la web: nombre, cita legal y enlace (GET /sources)."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from housefinder.api.deps import get_db, get_param_book, get_rule_book
from housefinder.api.main import app
from housefinder.api.sources import territory_name
from housefinder.core.figures import SourceRef
from housefinder.params.book import Param, ParamBook
from housefinder.regulation.rules import Rule, RuleBook
from housefinder.reports.sources import describe, rule_detail

RULE = Rule(
    id="madrid-itp-prueba",
    kind="impuesto_compra_segunda_mano",
    territory="ES-13",
    effective_from=date(2014, 1, 1),
    effective_to=None,
    status="vigente",
    params={"rate": "0.06"},
    source_url="https://www.boe.es/buscar/act.php?id=prueba",
    notes="Decreto Legislativo de prueba, art. 28.",
)
PARAM = Param(
    id="criterios-prueba",
    kind="criterios_bancarios",
    territory="ES",
    effective_from=date(2026, 1, 1),
    effective_to=None,
    params={},
    source="Valores de prueba, sin fuente documentada",
)


def books() -> tuple[RuleBook, ParamBook]:
    return RuleBook([RULE]), ParamBook([PARAM])


def test_una_norma_se_lee_por_lo_que_es_y_donde_y_no_por_su_identificador() -> None:
    rules, params = books()
    [entry] = describe([SourceRef("rule", RULE.id)], rules, params, {},
                       lambda t: "Comunidad de Madrid" if t == "ES-13" else t)
    assert entry.name == "ITP de la vivienda usada · Comunidad de Madrid"
    assert entry.title == RULE.id  # el anexo del PDF sigue citando el identificador
    assert entry.url == RULE.source_url
    assert entry.detail == ("Decreto Legislativo de prueba, art. 28. Vigente desde el 1 de enero "
                            "de 2014; sin verificar todavía.")


def test_un_supuesto_se_explica_sin_referencias_internas_y_sin_repetirse() -> None:
    rules, params = books()
    [entry] = describe([SourceRef("assumption", "diferencial-variable-estimado")], rules, params,
                       {})
    assert "ADR" not in entry.name
    assert entry.name.startswith("Diferencial de la hipoteca variable")
    assert entry.detail == ""  # el nombre ya lo dice todo


def test_la_cita_de_una_norma_verificada_lo_dice() -> None:
    detail = rule_detail("", date(2026, 7, 9), True)
    assert detail == "Vigente desde el 9 de julio de 2026; verificada."


def test_nombres_de_territorio() -> None:
    assert territory_name("ES") == "España"
    assert territory_name("ES-13") == "Comunidad de Madrid"
    assert territory_name("ES-16-48") == "Bizkaia"
    assert territory_name("ES-13-28079") == "Madrid"
    assert territory_name("ES-99") == "ES-99"  # sin nombre conocido, el código


def test_la_api_resuelve_identificadores_con_y_sin_tipo() -> None:
    rules, params = books()
    app.dependency_overrides[get_db] = lambda: None  # sin tablas de datos: no hace falta la base
    app.dependency_overrides[get_rule_book] = lambda: rules
    app.dependency_overrides[get_param_book] = lambda: params
    try:
        resp = TestClient(app).get(
            "/sources",
            params=[("ref", f"rule:{RULE.id}"), ("ref", PARAM.id), ("ref", "user_input:comprador"),
                    ("ref", "rule:no-existe"), ("ref", f"rule:{RULE.id}")],
        )
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    body = {s["ref"]: s for s in resp.json()}
    assert list(body) == [f"rule:{RULE.id}", PARAM.id, "user_input:comprador", "rule:no-existe"]
    assert body[f"rule:{RULE.id}"]["name"] == "ITP de la vivienda usada · Comunidad de Madrid"
    assert body[PARAM.id]["kind"] == "param" and body[PARAM.id]["name"] == "Criterios bancarios"
    assert body["user_input:comprador"]["kind_label"] == "Dato tuyo"
    assert body["rule:no-existe"]["name"] == "No existe"  # sin datos, el identificador legible
