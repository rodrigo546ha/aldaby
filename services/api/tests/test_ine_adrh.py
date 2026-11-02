"""Cargador del Atlas de renta del INE (F3.3), con respuestas sintéticas (no son datos del INE)."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from housefinder.db.indicators import IndicatorRow, indicators_for, load_indicators
from housefinder.db.sections import SectionRow, SourceRecord, upsert_sections
from housefinder.ingestion.ine_adrh import missing_by_year, parse_table, source_record


def series(code: str | None, indicator: str, values: dict[int, float | None],
           level: str = "Secciones") -> dict:
    meta = [{"T3_Variable": "Tipo de dato", "Nombre": "Dato base", "Codigo": ""},
            {"T3_Variable": "SALDOS CONTABLES", "Nombre": indicator, "Codigo": ""}]
    if code is not None:
        meta.insert(0, {"T3_Variable": level, "Nombre": "x", "Codigo": code})
    return {
        "COD": f"ADRH-{code}-{indicator[:5]}",
        "MetaData": meta,
        "Data": [{"Anyo": year, "Valor": value} for year, value in values.items()],
    }


PAYLOAD = [
    series("2807902001", "Renta neta media por persona", {2023: 15000.0, 2024: 16000.0}),
    series("2807902001", "Porcentaje de población de 65 y más años", {2024: 23.5}),
    series("28079", "Renta neta media por persona", {2024: 20000.0}, level="Municipios"),
    series("2807902002", "Renta neta media por persona", {2024: None}),
]


def test_secciones_años_y_porcentajes():
    parsed = parse_table(PAYLOAD, "28")
    assert parsed.skipped_levels == 1  # la serie del municipio
    assert parsed.empty_values == 1
    assert parsed.years == (2023, 2024)
    by_key = {(r.indicator, r.year): r for r in parsed.rows}
    renta = by_key[("renta_neta_media_persona", 2024)]
    assert renta.value == Decimal("16000.0") and renta.unit == "EUR"
    assert renta.section_vintage == 2025  # el año t va sobre el seccionado de t+1
    assert by_key[("renta_neta_media_persona", 2023)].section_vintage == 2024
    mayores = by_key[("poblacion_65_y_mas", 2024)]
    assert mayores.value == Decimal("0.235") and mayores.unit == "ratio"


def test_indicador_desconocido_para_la_carga():
    with pytest.raises(ValueError, match="indicador desconocido"):
        parse_table([series("2807902001", "Renta inventada", {2024: 1.0})], "28")


def test_codigo_de_otra_provincia():
    with pytest.raises(ValueError, match="código de sección"):
        parse_table([series("0807902001", "Población", {2024: 1.0})], "28")


def test_metadatos_con_forma_de_series_tabla():
    s = series("2807902001", "Población", {2024: 1500.0})
    s["MetaData"] = [{"Variable": {"Nombre": m["T3_Variable"]}, **m} for m in s["MetaData"]]
    for m in s["MetaData"]:
        del m["T3_Variable"]
    assert parse_table([s], "28").rows[0].indicator == "poblacion"


def test_fuente_con_años_y_huella():
    source = source_record(31097, "renta", parse_table(PAYLOAD, "28"))
    assert source.id == "ine-adrh-31097"
    assert "2023–2024" in source.notes and "t+1" in source.notes


def test_secciones_sin_poligono_por_año():
    rows = [IndicatorRow("2807999999", 2025, "poblacion", 2024, Decimal(1), "personas"),
            IndicatorRow("2807999999", 2025, "edad_media", 2024, Decimal(1), "años"),
            IndicatorRow("2807999998", 2024, "poblacion", 2023, Decimal(1), "personas")]
    assert list(missing_by_year(rows)) == [(2023, 1), (2024, 1)]


@pytest.mark.db
def test_carga_contra_la_base(migrated_database: str):
    psycopg = pytest.importorskip("psycopg")
    square = {"type": "MultiPolygon", "coordinates": [[[[-3.6, 40.4], [-3.59, 40.4],
                                                        [-3.59, 40.41], [-3.6, 40.4]]]]}
    with psycopg.connect(migrated_database) as conn:
        upsert_sections(conn, [SectionRow("2807902001", "28079", json.dumps(square))], 2025,
                        None)
        conn.commit()
    rows = parse_table(PAYLOAD, "28").rows
    source = SourceRecord("ine-adrh-31097", "prueba", "https://example.org", "CC BY 4.0",
                          datetime.now(UTC))
    report = load_indicators(migrated_database, source, rows)
    # Solo existe la sección en la cartografía de 2025: el dato de 2023 (seccionado 2024) no.
    assert report.loaded == 2
    assert [(r.year, r.section_vintage) for r in report.without_section] == [(2023, 2024)]
    assert load_indicators(migrated_database, source, rows).loaded == 2  # idempotente
    with psycopg.connect(migrated_database) as conn:
        found = indicators_for(conn, "2807902001", 2025)
    assert [(i, y, v, u) for i, y, v, u, _ in found] == [
        ("poblacion_65_y_mas", 2024, Decimal("0.235"), "ratio"),
        ("renta_neta_media_persona", 2024, Decimal("16000.0"), "EUR"),
    ]


def test_tablas_de_las_52_provincias():
    from housefinder.ingestion.ine_adrh import PROVINCE_TABLES

    assert sorted(PROVINCE_TABLES) == [f"{n:02d}" for n in range(1, 53)]
    assert all(set(t) == {"renta", "demografia"} for t in PROVINCE_TABLES.values())
    assert PROVINCE_TABLES["28"] == {"renta": 31097, "demografia": 31105}  # las ya comprobadas
    ids = [i for t in PROVINCE_TABLES.values() for i in t.values()]
    assert len(ids) == len(set(ids))  # ninguna tabla en dos provincias
