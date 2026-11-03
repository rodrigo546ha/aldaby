"""Plusvalía municipal del libro de Hacienda (ADR-0044), con un texto con la forma del PDF.

Los nombres y códigos son reales; las cifras de Toledo y Gijón son las del libro de 2026, que
coinciden con sus ordenanzas (toledo.es, Ordenanza n.º 2, art. 11; gijon.es, Ordenanza 1.03,
art. 8.1). El resto, sintéticas.
"""

from datetime import date
from decimal import Decimal

import pytest

from housefinder.ingestion import hacienda_plusvalia as hp

D = Decimal
MAX = ("0,15 0,15 0,14 0,14 0,16 0,18 0,19 0,20 0,19 0,15 0,12 "
       "0,10 0,09 0,09 0,09 0,09 0,10 0,13 0,17 0,23 0,40")
OLD = ("0,14 0,13 0,14 0,14 0,16 0,17 0,16 0,12 0,10 0,09 0,08 "
       "0,08 0,08 0,08 0,09 0,09 0,10 0,13 0,17 0,23 0,40")
TOLEDO = " ".join(["29,88"] * 6 + ["28,88"] * 5 + ["26,89"] * 5 + ["25,90"] * 5)
GIJON = " ".join(["25,00"] * 6 + ["22,00"] * 14 + ["18,00"])
FLAT = " ".join(["30,00"] * 21)

TEXT = f"""
 1.CM MUNICIPIOS MAYORES DE 1000 HABITANTES
45-168   Toledo                 2008   0,44400   0,84800   1,29500   3,79   2,74
45-165   Talavera de la Reina   2009   0,55000   0,80000   1,10000   3,00   2,00
45-901   Santo Domingo-Caudilla 2010   0,60000   0,80000   1,10000   3,00   2,00
IMPUESTO SOBRE EL INCREMENTO DEL VALOR DE                         CASTILLA-MANCHA
 3.CM MUNICIPIOS MAYORES DE 1000 HABITANTES
       QUE TIENEN ESTABLECIDO EL IMPUESTO
       Coeficiente sobre la Base Imponible
 Inferior a  1     2   ...   Igual o  Porc.
45-168   Toledo                 {MAX}   0,00
45-165   Talavera de la         {OLD}   5,00
         Reina
       Tipo de Gravamen
45-168   Toledo                 {TOLEDO}   0,00
45-165   Talavera de la         {FLAT}   0,00
         Reina
 4.CM MUNICIPIOS MAYORES DE 1000 HABITANTES
       Tipo de Gravamen
45-168   Toledo   3,98
"""


def test_las_dos_tablas_de_la_tercera_parte():
    found = {m.code: m for m in hp.parse(TEXT)}
    assert set(found) == {"45165", "45168"}  # Santo Domingo no tiene el impuesto
    toledo = found["45168"]
    assert toledo.rates[0] == D("0.2988") and toledo.rates[20] == D("0.259")
    assert found["45165"].coefficients[1] == D("0.13") and found["45165"].reduction == D(5)


def test_tipo_unico_o_por_años():
    assert hp.rate_params(tuple([D("0.3")] * 21)) == {"rate": 0.3}
    gijon = tuple(D(v.replace(",", ".")) / 100 for v in GIJON.split())
    assert hp.rate_params(gijon) == {"by_years": [
        {"from_years": 0, "rate": 0.25}, {"from_years": 6, "rate": 0.22},
        {"from_years": 20, "rate": 0.18}]}


def test_reglas_de_una_comunidad():
    found = hp.parse(TEXT)
    maximums = tuple(D(v.replace(",", ".")) for v in MAX.split())
    existing = {"tipo_plusvalia": {"ES-08-45168"}, "coeficientes_plusvalia": set()}
    rules = hp.rules(found, [("45901", "Santo Domingo-Caudilla")], 2026, "08", "https://pdf",
                     existing, maximums)
    by_id = {r["id"]: r for r in rules}
    # Toledo tiene su regla de ordenanza y aplica los máximos: nada que generar
    assert not any("45168" in i for i in by_id)
    talavera = by_id["plusvalia-tipo-45165"]
    assert talavera["params"] == {"rate": 0.3} and talavera["effective_to"] is None
    assert "Porc. reducc." in str(talavera["notes"])
    assert by_id["plusvalia-coeficientes-45165"]["params"]["by_years"][1] == 0.13
    assert by_id["plusvalia-tipo-45901"]["params"] == {"rate": 0.0}  # sin el impuesto
    assert all(r["verified"] is False for r in rules)


def test_maximos_y_choques_con_las_ordenanzas(tmp_path):
    (tmp_path / "venta.yaml").write_text(f"""
- id: max
  kind: coeficientes_plusvalia
  territory: ES
  effective_from: 2024-01-01
  effective_to: null
  status: vigente
  params: {{by_years: [{MAX.replace(",", ".").replace(" ", ", ")}]}}
- id: toledo
  kind: tipo_plusvalia
  territory: ES-08-45168
  effective_from: 2022-03-12
  effective_to: null
  status: vigente
  params: {{rate: 0.30}}
""", encoding="utf-8")
    (tmp_path / hp.GENERATED).write_text(  # el generado no cuenta como propio
        "- {id: y, kind: tipo_plusvalia, territory: ES-08-45165}\n", encoding="utf-8")
    assert hp.legal_maximums(tmp_path, date(2026, 1, 1))[20] == D("0.40")
    assert hp.existing_territories(tmp_path)["tipo_plusvalia"] == {"ES-08-45168"}
    warnings = hp.disagreements(hp.parse(TEXT), "08", tmp_path, 2026)
    assert len(warnings) == 1 and warnings[0].startswith("toledo (venta.yaml)")
    with pytest.raises(LookupError):
        hp.legal_maximums(tmp_path, date(2023, 1, 1))
