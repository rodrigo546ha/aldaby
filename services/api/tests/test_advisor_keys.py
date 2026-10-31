"""Claves sin números para el modelo (ADR-0012): nombra el indicador por su clave."""

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
