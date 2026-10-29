"""Cifras del territorio (F3.6): último año, cambio a 5 años, series y avisos. Sin base."""

from decimal import Decimal

from housefinder.core.figures import SourceRef
from housefinder.db.indicators import IndicatorRow
from housefinder.territory.figures import Context, territory_figures

D = Decimal
CODE = "2807999001"


def row(indicator, year, value, unit):
    return IndicatorRow(CODE, year + 1, indicator, year, D(value), unit)


HISTORY = [
    row("renta_neta_media_persona", 2019, "20000", "EUR"),
    row("renta_neta_media_persona", 2024, "23000", "EUR"),
    row("poblacion_65_y_mas", 2019, "0.20", "ratio"),
    row("poblacion_65_y_mas", 2024, "0.25", "ratio"),
    row("edad_media", 2019, "40.0", "años"),
    row("edad_media", 2024, "42.5", "años"),
    row("poblacion", 2024, "1500", "personas"),
]


def context(stable_maps=(2020, 2025)):
    return Context(
        code=CODE,
        vintage=2025,
        location_sources=(SourceRef("dataset", "cartociudad-geocoder"),),
        map_sources={v: SourceRef("dataset", f"ine-secciones-{v}-28") for v in stable_maps},
        value_sources={(r.indicator, r.year): "ine-adrh-31097" for r in HISTORY},
    )


def by_key(figures):
    return {f.key: f for f in figures}


def test_ultimo_año_y_cambios_a_cinco_años():
    figures, series, notes = territory_figures(HISTORY, {2020, 2025}, context())
    f = by_key(figures)
    assert f["territory.renta_neta_media_persona"].value == D("23000")
    assert f["territory.renta_neta_media_persona"].unit == "EUR/año"
    # Renta: cambio relativo, (23.000 − 20.000) / 20.000 = 15 %.
    assert f["territory.renta_neta_media_persona.change_5y"].value == D("0.1500")
    # Porcentajes: diferencia en puntos, 0,25 − 0,20.
    assert f["territory.poblacion_65_y_mas.change_5y"].value == D("0.0500")
    # Edad: diferencia en años.
    assert f["territory.edad_media.change_5y"].value == D("2.5")
    assert f["territory.edad_media.change_5y"].unit == "años"
    assert [x.key for x in series["renta_neta_media_persona"]] == [
        "territory.renta_neta_media_persona.2019", "territory.renta_neta_media_persona.2024"]
    # La ventana 2019–2024 cruza el cambio de fuente de población de 2023: se avisa.
    assert len(notes) == 1 and "Censo Anual" in notes[0]


def test_fuentes_de_cada_cifra():
    figures, _, _ = territory_figures(HISTORY, {2020, 2025}, context())
    change = by_key(figures)["territory.renta_neta_media_persona.change_5y"]
    ids = {s.id for s in change.sources}
    assert {"ine-adrh-31097", "ine-secciones-2020-28", "ine-secciones-2025-28",
            "cartociudad-geocoder", "seccion-estable-1-por-ciento"} <= ids


def test_seccion_redibujada_sin_tendencia():
    figures, series, notes = territory_figures(HISTORY, {2025}, context((2025,)))
    keys = by_key(figures)
    assert "territory.renta_neta_media_persona" in keys
    assert not any(k.endswith("change_5y") for k in keys)
    assert [x.key for x in series["renta_neta_media_persona"]] == [
        "territory.renta_neta_media_persona.2024"]
    assert any("redibujó" in n for n in notes)


def test_seccion_pequeña_con_renta_asignada():
    small = [r if r.indicator != "poblacion" else row("poblacion", 2024, "80", "personas")
             for r in HISTORY]
    figures, _, notes = territory_figures(small, {2020, 2025}, context())
    renta = by_key(figures)["territory.renta_neta_media_persona"]
    assert "asignado por el INE" in renta.formula
    assert "asignado" not in by_key(figures)["territory.edad_media"].formula
    assert any("menos de 100 habitantes" in n for n in notes)
