"""Regulación del alquiler (F2.4): zona tensionada y régimen por tipo de alquiler."""

from datetime import date
from pathlib import Path

import pytest

from housefinder.regulation.kinds import RentalRegime, ZoneDeclaration, parse_params
from housefinder.regulation.resolvers import rental_regime, stressed_zone
from housefinder.regulation.rules import RuleBook, default_rules_dir

MADRID = "ES-13-28079"
ALCALA = "ES-13-28005"
HOY = date(2026, 10, 28)


@pytest.fixture(scope="module")
def book() -> RuleBook:
    return RuleBook.from_dir(default_rules_dir())


# --- Esquemas -------------------------------------------------------------------------


def test_esquema_de_zona():
    zona = parse_params(
        "zona_tensionada", {"declared": False, "checked_through": "2026-07-29"}
    )
    assert isinstance(zona, ZoneDeclaration)
    assert zona.checked_through == date(2026, 7, 29)


def test_esquema_de_regimen():
    regimen = parse_params(
        "regimen_alquiler_turistico",
        {
            "regime": "Vivienda de uso turístico",
            "requirements": [
                {"code": "aprobacion-comunidad", "description": "Aprobación previa",
                 "source_url": "https://www.boe.es/x"},
            ],
        },
    )
    assert isinstance(regimen, RentalRegime)
    assert regimen.allowed


def test_requisito_sin_fuente_es_un_error():
    with pytest.raises(ValueError, match="source_url"):
        parse_params(
            "regimen_alquiler_turistico",
            {"regime": "x", "requirements": [{"code": "a", "description": "b"}]},
        )


# --- Zona tensionada --------------------------------------------------------------------


def test_madrid_no_es_zona_tensionada(book: RuleBook):
    zona = stressed_zone(book, MADRID, HOY, allow_unverified=True)
    assert zona.declared is False
    assert zona.checked_through == date(2026, 7, 29)
    assert zona.rule.id == "madrid-zonas-tensionadas"


def test_cualquier_municipio_de_la_comunidad_de_madrid(book: RuleBook):
    assert stressed_zone(book, ALCALA, HOY, allow_unverified=True).declared is False


def test_territorio_no_revisado_es_un_error(book: RuleBook):
    with pytest.raises(LookupError, match="zona_tensionada"):
        stressed_zone(book, "ES-09-08019", HOY, allow_unverified=True)


# --- Régimen por tipo de alquiler --------------------------------------------------------


def test_turistico_en_madrid_suma_los_tres_niveles(book: RuleBook):
    res = rental_regime(book, "turistico", MADRID, HOY, allow_unverified=True)
    codigos = {r.code for r in res.requirements}
    # Estatal: comunidad de propietarios y Registro Único; autonómico: declaración, CIVUT…;
    # municipal: licencia urbanística.
    assert {"aprobacion-previa-comunidad", "registro-unico-arrendamientos"} <= codigos
    assert {"declaracion-responsable", "civut", "vivienda-completa"} <= codigos
    assert "licencia-urbanistica-actividad" in codigos
    assert len(res.rules) == 3
    # Cada requisito dice de qué regla sale.
    assert all(r.rule_id in {rule.id for rule in res.rules} for r in res.requirements)


def test_turistico_fuera_de_la_capital_sin_licencia_municipal(book: RuleBook):
    res = rental_regime(book, "turistico", ALCALA, HOY, allow_unverified=True)
    codigos = {r.code for r in res.requirements}
    assert "licencia-urbanistica-actividad" not in codigos
    assert "civut" in codigos


def test_temporada_base_y_escenario_rdl(book: RuleBook):
    base = rental_regime(book, "temporada", MADRID, HOY, allow_unverified=True)
    rdl = rental_regime(
        book, "temporada", MADRID, HOY, include_pending=True, allow_unverified=True
    )
    assert "uso distinto" in base.regime.lower()
    assert "vivienda temporal" in rdl.regime.lower()
    assert "causa-justificada-desplazamiento" in {r.code for r in rdl.requirements}


def test_habitaciones_con_el_rdl_son_vivienda(book: RuleBook):
    rdl = rental_regime(
        book, "habitaciones", MADRID, HOY, include_pending=True, allow_unverified=True
    )
    assert "vivienda habitual" in rdl.regime.lower()


def test_tipo_desconocido(book: RuleBook):
    with pytest.raises(ValueError, match="vacacional"):
        rental_regime(book, "vacacional", MADRID, HOY, allow_unverified=True)


def test_las_reglas_de_alquiler_son_validas():
    book = RuleBook.from_dir(default_rules_dir())
    assert any(r.kind == "zona_tensionada" for r in book.rules)


def test_regimen_no_permitido(tmp_path: Path):
    (tmp_path / "x.yaml").write_text(
        """
- id: prohibido
  kind: regimen_alquiler_turistico
  territory: ES-13
  effective_from: 2026-01-01
  verified: false
  params: {regime: "Prohibido", allowed: false}
  source_url: https://example.org/prohibido
""",
        encoding="utf-8",
    )
    res = rental_regime(
        RuleBook.from_dir(tmp_path), "turistico", MADRID, HOY, allow_unverified=True
    )
    assert res.allowed is False
