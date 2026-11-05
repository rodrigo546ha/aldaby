"""Estado y antigüedad del inmueble: avisos, no descuentos (planning/condition.py)."""

from decimal import Decimal

import pytest

from housefinder.planning.condition import condition_notes, needs_renovation


@pytest.mark.parametrize("text, expected", [
    ("A reformar", True),
    ("para REFORMAR por completo", True),
    ("Necesita reforma", True),
    ("Para actualizar", True),
    ("Reformado", False),  # ya está reformado
    ("Buen estado", False),
    ("Obra nueva", False),
    (None, False),
])
def test_palabras_que_piden_reforma(text, expected):
    assert needs_renovation(text) is expected


def test_avisos_sin_reforma_indicada():
    notes = condition_notes("a reformar", 1965, "el Catastro", 2026, Decimal(0))
    assert len(notes) == 2
    assert "«a reformar»" in notes[0] and "Indica lo que costaría" in notes[0]
    assert "1965 (61 años, según el Catastro)" in notes[1] and "derramas" in notes[1]


def test_con_reforma_indicada_y_sin_ano():
    notes = condition_notes("A reformar", None, "el anuncio", 2026, Decimal(25000))
    assert notes == ["El anuncio dice «A reformar»: el plan suma la reforma que has indicado a "
                     "la compra y a lo que pones."]


def test_sin_estado_ni_ano_no_hay_avisos():
    assert condition_notes("Buen estado", None, "el anuncio", 2026, Decimal(0)) == []
    assert condition_notes(None, 2031, "el anuncio", 2026, Decimal(0)) == []  # año imposible
