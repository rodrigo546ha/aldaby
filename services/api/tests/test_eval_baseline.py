"""Línea base de las evaluaciones (F6.9, ADR-0027)."""

from housefinder.evaluations.baseline import compare


def test_lo_que_no_depende_del_modelo_tiene_que_ser_cero():
    assert compare({"agente": {"cifras_fuera": 0}, "coherencia": {"incoherencias": 0}},
                   None) == []
    assert compare({"agente": {"cifras_fuera": 2}}, None) == [
        "agente.cifras_fuera = 2: tiene que ser cero"]


def test_se_compara_con_la_base_guardada():
    saved = {"metricas": {"extraccion": {"correctos": 120, "sobra": 2},
                          "agente": {"mostrados": 7}}}
    now = {"extraccion": {"correctos": 118, "sobra": 1}, "agente": {"mostrados": 8}}
    assert compare(now, saved) == ["extraccion.correctos baja de 120 a 118"]
    assert compare({"extraccion": {"correctos": 121, "sobra": 3}}, saved) == [
        "extraccion.sobra sube de 2 a 3"]
