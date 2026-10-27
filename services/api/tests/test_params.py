from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from housefinder.core.figures import SourceRef
from housefinder.params.bank import bank_criteria
from housefinder.params.book import ParamBook, default_params_dir

# Valores de prueba, NO criterios reales de ningún banco.
YAML = """
- id: criterios-es-2026
  kind: criterios_bancarios
  territory: ES
  effective_from: 2026-01-01
  provisional: true
  params: {max_ltv: 0.70, max_dti: 0.35, max_age_at_end: 75, max_years: 30}
  source: "Prueba"
- id: criterios-es-2027
  kind: criterios_bancarios
  territory: ES
  effective_from: 2027-01-01
  provisional: false
  params: {max_ltv: 0.80, max_dti: 0.40, max_age_at_end: 70, max_years: 25}
  source: "Prueba calibrada"
  source_url: https://example.org/banco
- id: criterios-madrid-2026
  kind: criterios_bancarios
  territory: ES-13
  effective_from: 2026-06-01
  effective_to: 2026-12-31
  provisional: true
  params: {max_ltv: 0.60, max_dti: 0.30, max_age_at_end: 75, max_years: 30}
  source: "Prueba Madrid"
"""


@pytest.fixture
def book(tmp_path: Path) -> ParamBook:
    (tmp_path / "criterios.yaml").write_text(YAML, encoding="utf-8")
    return ParamBook.from_dir(tmp_path)


def test_resuelve_el_mas_reciente_vigente(book: ParamBook):
    assert book.resolve("criterios_bancarios", "ES", date(2026, 3, 1)).id == "criterios-es-2026"
    assert book.resolve("criterios_bancarios", "ES", date(2027, 3, 1)).id == "criterios-es-2027"


def test_resuelve_el_mas_especifico(book: ParamBook):
    madrid = "ES-13-28079"
    assert book.resolve("criterios_bancarios", madrid, date(2026, 7, 1)).id == (
        "criterios-madrid-2026"
    )
    # Fuera de su vigencia, vuelve la regla nacional.
    assert book.resolve("criterios_bancarios", madrid, date(2027, 3, 1)).id == "criterios-es-2027"


def test_sin_parametro_vigente_devuelve_none(book: ParamBook):
    assert book.resolve("criterios_bancarios", "ES", date(2025, 1, 1)) is None


def test_la_referencia_lleva_la_marca_provisional(book: ParamBook):
    param = book.resolve("criterios_bancarios", "ES", date(2026, 3, 1))
    assert param.ref == SourceRef("param", "criterios-es-2026", provisional=True)


def test_id_repetido_es_un_error(tmp_path: Path):
    (tmp_path / "a.yaml").write_text(YAML, encoding="utf-8")
    (tmp_path / "b.yaml").write_text(YAML, encoding="utf-8")
    with pytest.raises(ValueError, match="repetido"):
        ParamBook.from_dir(tmp_path)


def test_falta_la_fuente_es_un_error(tmp_path: Path):
    (tmp_path / "a.yaml").write_text(
        "- {id: x, kind: k, territory: ES, effective_from: 2026-01-01, params: {}}",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="source"):
        ParamBook.from_dir(tmp_path)


def test_criterios_bancarios_en_decimal(book: ParamBook):
    c = bank_criteria(book, "ES-13-28079", date(2027, 3, 1))
    assert c.max_ltv == Decimal("0.80")
    assert isinstance(c.max_ltv, Decimal) and isinstance(c.max_dti, Decimal)
    assert (c.max_age_at_end, c.max_years) == (70, 25)
    assert c.source == SourceRef("param", "criterios-es-2027")


def test_sin_criterios_vigentes_es_un_error(book: ParamBook):
    with pytest.raises(LookupError):
        bank_criteria(book, "ES", date(2025, 1, 1))


def test_criterios_fuera_de_rango_son_un_error(tmp_path: Path):
    (tmp_path / "a.yaml").write_text(
        YAML.replace("max_ltv: 0.70", "max_ltv: 1.70"), encoding="utf-8"
    )
    book = ParamBook.from_dir(tmp_path)
    with pytest.raises(ValueError, match="max_ltv"):
        bank_criteria(book, "ES", date(2026, 3, 1))


def test_un_booleano_no_es_un_plazo(tmp_path: Path):
    (tmp_path / "a.yaml").write_text(
        YAML.replace("max_years: 30}", "max_years: true}", 1), encoding="utf-8"
    )
    book = ParamBook.from_dir(tmp_path)
    with pytest.raises(ValueError, match="max_years"):
        bank_criteria(book, "ES", date(2026, 3, 1))


def test_los_datos_del_repositorio_cargan_y_son_provisionales():
    # Mientras F1.5 no esté calibrada, los criterios del repositorio son provisionales.
    book = ParamBook.from_dir(default_params_dir())
    c = bank_criteria(book, "ES-13-28079", date(2026, 10, 27))
    assert c.source.provisional
