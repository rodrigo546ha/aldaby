"""Cargadores de las fuentes de los supuestos (ADR-0022), con trozos con la forma de los ficheros
reales (2026-10-31) y sin red."""

from decimal import Decimal
from pathlib import Path

from housefinder.ingestion import bde_tipos, catastro_urbana, hacienda_ibi, ine_epf, ine_hipotecas

BDE = (
    '"CÓDIGO DE LA SERIE",DN_1TI2T0101,DN_1TI2T0002,DN_1TI2T0003,DN_1TI2T0006\n'
    '"NÚMERO SECUENCIAL",1,2,3,4\n'
    '"DESCRIPCIÓN DE LAS UNIDADES","Porcentaje","Porcentaje","Porcentaje","Porcentaje"\n'
    '"ENE 2003",13.1065,4.2051,4.1735,4.2179\n'
    '"JUL 2026",5.6,3.01,3.2,"_"\n'
    '"AGO 2026",5.5844,3.0444,3.2325,2.7556\n'
    '"FUENTE","","","",""\n'
).encode("latin-1")


def test_bde_en_tanto_por_uno_y_sin_huecos():
    rows = bde_tipos.parse(BDE)
    fixed = {(r.year, r.month): r.value for r in rows if r.typology == "mas_10"}
    assert fixed == {(2003, 1): Decimal("0.042179"), (2026, 8): Decimal("0.027556")}  # «_» fuera
    assert {r.typology for r in rows} == {"total", "hasta_1", "mas_10"}  # descubiertos no
    assert all(r.level == "pais" and r.code == "ES" and r.unit == "ratio" for r in rows)


def test_ine_hipotecas_solo_viviendas_y_tipo_medio():
    def series(finca, concepto, tipo, value):
        return {"MetaData": [
            {"T3_Variable": "Naturaleza de la finca", "Nombre": finca},
            {"T3_Variable": "Concepto financiero", "Nombre": concepto},
            {"T3_Variable": "Tipo de interés", "Nombre": tipo}],
            "Data": [{"T3_Periodo": "M08", "Anyo": 2026, "Valor": value}]}

    rows = ine_hipotecas.parse([
        series("Viviendas", "Tipo de interés medio", "Fijo", 3.16),
        series("Total fincas", "Tipo de interés medio", "Fijo", 3.22),
        series("Viviendas", "Plazo medio", "Fijo", 24.5)])
    assert [(r.typology, r.month, r.value) for r in rows] == [("fijo", 8, Decimal("0.0316"))]


def test_catastro_por_municipio_y_sin_los_ocultos():
    rows = catastro_urbana.parse([
        {"AREF": "2026", "COD_INE_MUNI": "28065", "UU_RES": 80782.0,
         "V_CAT_RES": 8159579782.2, "V_CATASTRAL": 13043011506.01,
         "V_CONSTRUCCION": 4862891287.64, "V_SUELO": 8180120218.37},
        {"AREF": "2026", "COD_INE_MUNI": "28999", "UU_RES": 2.0, "V_CAT_RES": "",  # secreto
         "V_CATASTRAL": "", "V_CONSTRUCCION": "", "V_SUELO": ""},
        {"AREF": "2026", "COD_INE_MUNI": "02003", "UU_RES": 1.0, "V_CAT_RES": 1.0,
         "V_CATASTRAL": 1.0, "V_CONSTRUCCION": 1.0, "V_SUELO": 1.0},  # otra provincia
    ], "28")
    getafe = {r.measure: r.value for r in rows if r.code == "28065"}
    assert getafe["valor_catastral_residencial"] == Decimal("8159579782.2")
    assert {r.measure for r in rows if r.code == "28999"} == {"inmuebles_residenciales"}
    assert not any(r.code == "02003" for r in rows)


def test_epf_por_comunidad_y_nacional():
    def series(region, code, coicop, kind, value, secret=False):
        return {"MetaData": [
            {"T3_Variable": region, "Codigo": code},
            {"T3_Variable": "Clases COICOP/EPF", "Codigo": coicop},
            {"T3_Variable": "Gastos totales, medios, distribución porcentual e índices sobre la "
                            "media del gasto", "Nombre": kind}],
            "Data": [{"Anyo": 2025, "Valor": value, "Secreto": secret}]}

    rows = ine_epf.parse([
        series("Comunidades y Ciudades Autónomas", "13", "04.4.4 T", "Gasto medio por hogar",
               1045.76),
        series("Total Nacional", "00", "12.1.3 T", "Gasto medio por hogar", 251.6),
        series("Comunidades y Ciudades Autónomas", "13", "04.4.4 T", "Gasto medio por persona",
               401.82),
        series("Comunidades y Ciudades Autónomas", "18", "04.3.2 T", "Gasto medio por hogar",
               None, True),
    ])
    assert sorted((r.level, r.code, r.measure, r.value) for r in rows) == [
        ("comunidad", "13", "gasto_comunidad_hogar", Decimal("1045.76")),
        ("pais", "ES", "gasto_seguro_vivienda_hogar", Decimal("251.6"))]


TEXT = """                                  1.M MUNICIPIOS MAYORES DE 1000 HABITANTES
28-002   Ajalvir                    2003       0,55000            0,40000            1,30000
28-065   Getafe                       2009       0,41000            1,01000            1,30000
28-079   Madrid                       2012       0,41400            1,02000            1,30000
28-065 Getafe                           1,76   2,00   1,88   1,88     1,88    1,94    2,00
"""


def test_ibi_primera_tabla_y_sin_pisar_reglas_propias(tmp_path: Path):
    rates = hacienda_ibi.parse(TEXT)
    assert [(r.code, r.rate) for r in rates] == [
        ("28002", Decimal("0.0055")), ("28065", Decimal("0.0041")), ("28079", Decimal("0.00414"))]
    (tmp_path / "madrid.yaml").write_text(
        "- {id: x, kind: tipo_ibi, territory: ES-13-28079}\n", encoding="utf-8")
    (tmp_path / "ibi_hacienda_2025.yaml").write_text(  # el generado no cuenta como propio
        "- {id: y, kind: tipo_ibi, territory: ES-13-28065}\n", encoding="utf-8")
    existing = hacienda_ibi.existing_territories(tmp_path)
    assert existing == {"ES-13-28079"}
    generated = hacienda_ibi.rules(rates, 2026, "13", "https://pdf", existing)
    assert [r["territory"] for r in generated] == ["ES-13-28002", "ES-13-28065"]
    assert generated[1]["verified"] is False and generated[1]["params"] == {"rate": 0.0041}
