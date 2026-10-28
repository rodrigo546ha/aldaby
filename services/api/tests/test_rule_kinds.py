from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from housefinder.regulation.check import main as rules_check
from housefinder.regulation.kinds import KINDS, BracketScale, RentalFacts, parse_params
from housefinder.regulation.rules import Rule, RuleBook, default_rules_dir
from housefinder.regulation.validate import check_rules

# Valores de prueba, NO normativa real.


def _rule(**overrides) -> Rule:
    base = Rule(
        id="prueba",
        kind="impuesto_compra_segunda_mano",
        territory="ES-13",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        status="vigente",
        params={"rate": 0.05},
        source_url="https://example.org/ley",
        verified=True,
        verified_by="Rodrigo",
        verified_on=date(2026, 10, 28),
    )
    return replace(base, **overrides)


# --- Catálogo de tipos --------------------------------------------------------


def test_tipo_con_tasa():
    assert parse_params("impuesto_compra_segunda_mano", {"rate": 0.07}).rate == Decimal("0.07")


def test_tasa_fuera_de_rango():
    with pytest.raises(ValueError, match="rate"):
        parse_params("impuesto_compra_segunda_mano", {"rate": 1.5})


def test_parametro_desconocido():
    with pytest.raises(ValueError, match="tipo"):
        parse_params("impuesto_compra_segunda_mano", {"rate": 0.07, "tipo": 0.1})


def test_tipo_desconocido():
    with pytest.raises(ValueError, match="desconocido"):
        parse_params("impuesto_inventado", {"rate": 0.1})


def test_escala_por_tramos():
    scale = parse_params(
        "escala_irpf_general",
        {"brackets": [{"from": 0, "rate": 0.1}, {"from": 10000, "rate": 0.2}]},
    )
    assert isinstance(scale, BracketScale)
    assert scale.brackets[1].from_amount == Decimal(10000)
    assert scale.brackets[0].rate == Decimal("0.1")


def test_escala_debe_empezar_en_cero():
    with pytest.raises(ValueError, match="0"):
        parse_params("escala_irpf_general", {"brackets": [{"from": 100, "rate": 0.1}]})


def test_escala_debe_ser_creciente():
    with pytest.raises(ValueError, match="crecientes"):
        parse_params(
            "escala_irpf_general",
            {"brackets": [{"from": 0, "rate": 0.1}, {"from": 0, "rate": 0.2}]},
        )


def test_reduccion_sin_caso_general_vale():
    params = parse_params(
        "reduccion_irpf_alquiler",
        {"cases": [{"condition": "zona-tensionada", "reduction": 0.9}]},
    )
    assert params.case("zona-tensionada").reduction == Decimal("0.9")


def test_reduccion_con_condiciones_repetidas():
    with pytest.raises(ValueError, match="repetidas"):
        parse_params(
            "reduccion_irpf_alquiler",
            {
                "cases": [
                    {"condition": "general", "reduction": 0.5},
                    {"condition": "general", "reduction": 0.6},
                ]
            },
        )


def test_reduccion_por_casos():
    params = parse_params(
        "reduccion_irpf_alquiler",
        {"cases": [{"condition": "general", "reduction": 0.5}]},
    )
    assert params.case("general").reduction == Decimal("0.5")


def test_cada_tipo_tiene_descripcion():
    assert all(spec.description for spec in KINDS.values())


# --- Validador ----------------------------------------------------------------


def test_reglas_validas_sin_errores():
    assert check_rules([_rule()]) == []


def test_errores_de_una_regla():
    errors = check_rules(
        [
            _rule(id="a", kind="impuesto_inventado"),
            _rule(id="b", territory="ES-13-280"),
            _rule(id="c", effective_to=date(2025, 1, 1)),
            _rule(id="d", verified_by=""),
            _rule(id="e", source_url="boe.es/ley"),
        ]
    )
    joined = "\n".join(errors)
    for rule_id in "abcde":
        assert f"{rule_id}:" in joined


def test_id_repetido():
    errors = check_rules([_rule(), _rule(territory="ES-09")])
    assert any("repetido" in e for e in errors)


def test_vigencias_solapadas_son_un_error():
    vieja = _rule(id="vieja")
    nueva = _rule(id="nueva", effective_from=date(2027, 1, 1))
    errors = check_rules([vieja, nueva])
    assert any("se solapan" in e for e in errors)


def test_vigencias_consecutivas_valen():
    vieja = _rule(id="vieja", effective_to=date(2027, 1, 1))
    nueva = _rule(id="nueva", effective_from=date(2027, 1, 1))
    assert check_rules([vieja, nueva]) == []


def test_pendiente_puede_solaparse_con_la_vigente():
    vigente = _rule(id="vigente")
    pendiente = _rule(id="pendiente", status="pendiente_convalidacion")
    assert check_rules([vigente, pendiente]) == []


def test_distinto_territorio_no_se_solapa():
    assert check_rules([_rule(id="a"), _rule(id="b", territory="ES-09")]) == []


def test_sin_verificar_no_necesita_revisor():
    assert check_rules([_rule(verified=False, verified_by="", verified_on=None)]) == []


# --- Carga y comando ----------------------------------------------------------

MALA = """
- id: mala
  kind: impuesto_compra_segunda_mano
  territory: ES-13
  effective_from: 2026-01-01
  params: {rate: 2}
  source_url: https://example.org/ley
"""


def test_cargar_reglas_invalidas_falla_con_la_lista_de_errores(tmp_path: Path):
    (tmp_path / "mala.yaml").write_text(MALA, encoding="utf-8")
    with pytest.raises(ValueError, match="mala:"):
        RuleBook.from_dir(tmp_path)


def test_las_reglas_del_repositorio_son_validas():
    RuleBook.from_dir(default_rules_dir())


def test_comando_de_comprobacion(tmp_path: Path, capsys):
    assert rules_check([str(default_rules_dir())]) == 0
    (tmp_path / "mala.yaml").write_text(MALA, encoding="utf-8")
    assert rules_check([str(tmp_path)]) == 1
    assert "mala:" in capsys.readouterr().out


# --- Condiciones de los casos ------------------------------------------------

CASOS = {
    "cases": [
        {"condition": "general", "reduction": 0.5},
        {"condition": "zona", "reduction": 0.9, "when": {"stressed_zone": True}},
        {
            "condition": "joven-sin-gran-tenedor",
            "reduction": 0.7,
            "when": {"young_tenant": True, "large_holder": False},
        },
    ]
}


def _facts(**kw) -> RentalFacts:
    return RentalFacts(contract="primer-alquiler", large_holder=False, **kw)


def test_se_aplica_la_mayor_reduccion_de_las_que_cumple():
    casos = parse_params("reduccion_irpf_alquiler", CASOS)
    assert casos.best(_facts()).condition == "general"
    assert casos.best(_facts(young_tenant=True)).condition == "joven-sin-gran-tenedor"
    assert casos.best(_facts(young_tenant=True, stressed_zone=True)).condition == "zona"


def test_una_condicion_falsa_excluye_el_caso():
    casos = parse_params("reduccion_irpf_alquiler", CASOS)
    gran_tenedor = RentalFacts(contract="primer-alquiler", large_holder=True, young_tenant=True)
    assert casos.best(gran_tenedor).condition == "general"


def test_ningun_caso_aplicable():
    casos = parse_params(
        "reduccion_irpf_alquiler",
        {"cases": [{"condition": "zona", "reduction": 0.9, "when": {"stressed_zone": True}}]},
    )
    assert casos.best(_facts()) is None


def test_condicion_desconocida_en_la_regla():
    with pytest.raises(ValueError, match="edad_inventada"):
        parse_params(
            "reduccion_irpf_alquiler",
            {"cases": [{"condition": "x", "reduction": 0.5, "when": {"edad_inventada": True}}]},
        )


def test_gran_tenedor_es_obligatorio():
    with pytest.raises(ValueError):
        RentalFacts(contract="primer-alquiler")
