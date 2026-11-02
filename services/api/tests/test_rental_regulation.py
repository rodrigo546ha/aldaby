"""Regulación del alquiler (F2.4): zona tensionada y régimen por tipo de alquiler."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from housefinder.engines.lease import non_renewal_compensation
from housefinder.regulation.kinds import RentalRegime, ZoneDeclaration, parse_params
from housefinder.regulation.resolvers import lease_extension, rental_regime, stressed_zone
from housefinder.regulation.rules import RuleBook, default_rules_dir

D = Decimal
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
        stressed_zone(book, "ES-11-10037", HOY, allow_unverified=True)


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


# --- Duración y prórroga (LAU, arts. 9 y 10; RDL 28/2026) ----------------------------------


def test_prorroga_base_ley_12_2023(book: RuleBook):
    res = lease_extension(book, MADRID, date(2026, 11, 20), allow_unverified=True)
    p = res.params
    assert res.rule.id == "prorroga-alquiler-habitual-ley-12-2023"
    assert (p.minimum_years.natural_person, p.minimum_years.legal_person) == (5, 7)
    assert p.tacit_period_years.natural_person == 1 and p.tacit_max_years == 3
    assert (p.landlord_notice_months, p.tenant_notice_months) == (4, 2)
    assert p.compensation is None


def test_prorroga_con_el_rdl_28_2026(book: RuleBook):
    res = lease_extension(book, MADRID, date(2026, 11, 20), include_pending=True,
                          allow_unverified=True)
    p = res.params
    assert res.rule.id == "prorroga-alquiler-habitual-rdl-28-2026"
    assert (p.tacit_period_years.natural_person, p.tacit_period_years.legal_person) == (5, 7)
    assert p.tacit_max_years is None  # prórrogas sucesivas sin límite
    assert p.landlord_notice_months == 6
    assert p.compensation is not None and p.compensation.flat_months == 12
    assert "nuevo-contrato" in p.compensation.exceptions


def test_el_rdl_28_no_aplica_antes_del_15_de_noviembre(book: RuleBook):
    res = lease_extension(book, MADRID, date(2026, 11, 1), include_pending=True,
                          allow_unverified=True)
    assert res.rule.id == "prorroga-alquiler-habitual-ley-12-2023"


@pytest.mark.parametrize(
    ("years", "expected"),
    [
        ("7.5", "14400.00"),  # 12 mensualidades > 7,5: 12 × 1.200
        ("15", "18000.00"),  # 15 años > 12 mensualidades: 15 × 1.200
        ("12.25", "14700.00"),  # fracción de año prorrateada: 12,25 × 1.200
    ],
)
def test_indemnizacion_por_no_prorrogar(years, expected):
    assert non_renewal_compensation(D(12), D(1), D(1200), D(years)) == D(expected)


# --- Reducción del IRPF por tipo (ADR-0024) ------------------------------------------------


def test_reduccion_del_irpf_segun_el_tipo(book: RuleBook):
    def reduction(kind: str, pending: bool = False) -> bool | None:
        return rental_regime(book, kind, MADRID, HOY, include_pending=pending,
                             allow_unverified=True).irpf_reduction

    assert reduction("habitual") is True
    assert reduction("temporada") is False and reduction("turistico") is False
    assert reduction("habitaciones") is None  # por confirmar en la consulta legal
    assert reduction("habitaciones", pending=True) is True  # con el RDL 29/2026, vivienda
    turistico = rental_regime(book, "turistico", MADRID, HOY, allow_unverified=True)
    assert any("IVA" in note for note in turistico.tax_notes)


def test_la_reduccion_del_nivel_mas_especifico_gana(tmp_path: Path):
    (tmp_path / "x.yaml").write_text(
        """
- id: estatal
  kind: regimen_alquiler_temporada
  territory: ES
  effective_from: 2026-01-01
  verified: false
  params: {regime: "Estatal", irpf_reduction: false}
  source_url: https://example.org/estatal
- id: autonomica
  kind: regimen_alquiler_temporada
  territory: ES-13
  effective_from: 2026-01-01
  verified: false
  params: {regime: "Autonómica", irpf_reduction: true}
  source_url: https://example.org/autonomica
- id: municipal
  kind: regimen_alquiler_temporada
  territory: ES-13-28079
  effective_from: 2026-01-01
  verified: false
  params: {regime: "Municipal"}
  source_url: https://example.org/municipal
""",
        encoding="utf-8",
    )
    res = rental_regime(RuleBook.from_dir(tmp_path), "temporada", MADRID, HOY,
                        allow_unverified=True)
    assert res.irpf_reduction is True  # el municipio no lo dice: manda la comunidad
