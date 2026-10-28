from datetime import date
from pathlib import Path

import pytest

from housefinder.regulation.rules import RuleBook

YAML = """
- id: prueba-es
  kind: impuesto_compra_segunda_mano
  territory: ES
  effective_from: 2020-01-01
  status: vigente
  verified: true
  verified_by: Prueba
  verified_on: 2026-10-28
  params: {rate: 0.08}
  source_url: https://example.org/es
- id: prueba-ccaa
  kind: impuesto_compra_segunda_mano
  territory: ES-13
  effective_from: 2021-01-01
  status: vigente
  verified: true
  verified_by: Prueba
  verified_on: 2026-10-28
  params: {rate: 0.06}
  source_url: https://example.org/ccaa
- id: prueba-ccaa-nueva
  kind: impuesto_compra_segunda_mano
  territory: ES-13
  effective_from: 2027-01-01
  status: pendiente_convalidacion
  verified: true
  verified_by: Prueba
  verified_on: 2026-10-28
  params: {rate: 0.05}
  source_url: https://example.org/ccaa-nueva
- id: prueba-sin-verificar
  kind: reduccion_irpf_alquiler
  territory: ES
  effective_from: 2020-01-01
  status: vigente
  verified: false
  params: {cases: [{condition: general, reduction: 0.5}]}
  source_url: https://example.org/sin-verificar
"""


@pytest.fixture()
def book(tmp_path: Path) -> RuleBook:
    (tmp_path / "prueba.yaml").write_text(YAML, encoding="utf-8")
    return RuleBook.from_dir(tmp_path)


def test_gana_la_regla_mas_especifica(book):
    rule = book.resolve("impuesto_compra_segunda_mano", "ES-13-28079", date(2026, 10, 27))
    assert rule.id == "prueba-ccaa"


def test_otra_comunidad_usa_la_estatal(book):
    rule = book.resolve("impuesto_compra_segunda_mano", "ES-09-08019", date(2026, 10, 27))
    assert rule.id == "prueba-es"


def test_pendiente_solo_en_escenario(book):
    d = date(2027, 2, 1)
    assert book.resolve("impuesto_compra_segunda_mano", "ES-13", d).id == "prueba-ccaa"
    rule = book.resolve("impuesto_compra_segunda_mano", "ES-13", d, include_pending=True)
    assert rule.id == "prueba-ccaa-nueva"


def test_no_verificada_no_se_aplica_por_defecto(book):
    d = date(2026, 10, 27)
    assert book.resolve("reduccion_irpf_alquiler", "ES", d) is None
    assert book.resolve("reduccion_irpf_alquiler", "ES", d, allow_unverified=True) is not None
