"""Lo que el modelo ve de cada cifra: clave sin números y descripción sin números (ADR-0012)."""

import re
from decimal import Decimal

from housefinder.advisor.tools import _spoken_keys
from housefinder.core.figures import Figure

TERRITORY = ["territory.poblacion", "territory.poblacion.change_5y",
             "territory.poblacion_65_y_mas", "territory.poblacion_65_y_mas.change_5y",
             "territory.poblacion_menor_18", "territory.renta_bruta_media_hogar.change_5y"]


def test_las_claves_de_la_zona_llegan_sin_numeros():
    figures = [Figure(key, Decimal("0.1"), "ratio", "x") for key in TERRITORY]
    keys = _spoken_keys(figures)
    assert keys == {
        "territory.poblacion.change_5y": "territory.poblacion.cambio_lustro",
        "territory.poblacion_65_y_mas": "territory.poblacion_mayor",
        "territory.poblacion_65_y_mas.change_5y": "territory.poblacion_mayor.cambio_lustro",
        "territory.poblacion_menor_18": "territory.poblacion_menor_de_edad",
        "territory.renta_bruta_media_hogar.change_5y":
            "territory.renta_bruta_media_hogar.cambio_lustro",
    }
    assert not any(re.search(r"\d", keys.get(k, k)) for k in TERRITORY)


def test_cada_cifra_tiene_descripcion_sin_numeros():
    from housefinder.advisor.glossary import DESCRIPTIONS, describe
    from housefinder.territory.figures import LABELS

    keys = list(DESCRIPTIONS)
    for indicator in LABELS:
        keys += [f"territory.{indicator}", f"territory.{indicator}.change_5y"]
    units = {"territory.poblacion_65_y_mas": "ratio", "territory.edad_media": "años",
             "territory.poblacion": "personas"}
    figures = [Figure(key, Decimal("1"), units.get(key, "EUR"), "x") for key in keys]
    described = describe(figures)
    assert set(described) == set(keys)
    assert not [k for k, text in described.items() if re.search(r"\d", text)]
    # la tendencia de un porcentaje es una diferencia en puntos, no un cambio relativo
    assert "en puntos" in described["territory.poblacion_65_y_mas.change_5y"]
    assert "en años" in described["territory.edad_media.change_5y"]
    assert "relativa" in described["territory.poblacion.change_5y"]
    assert "edad avanzada" in described["territory.poblacion_65_y_mas"]
    assert describe([Figure("otra.cifra", Decimal("1"), "EUR", "x")]) == {}
