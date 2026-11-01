"""Hoja de ruta de compra (F6.7, ADR-0025): pasos de datos elegidos por canal, hipoteca y tipo."""

from housefinder.plans.roadmap import load_steps, roadmap


def test_los_pasos_son_validos_y_ninguno_esta_verificado():
    steps = load_steps()
    assert steps and not any(s.verified for s in steps)
    assert all(s.source_url.startswith("https://") for s in steps)


def test_anuncio_con_hipoteca_y_alquiler_habitual():
    ids = [s.id for s in roadmap("enlace", True, "habitual")]
    assert ids[0] == "nota-simple"
    assert {"fein", "arras", "acta-transparencia", "escritura", "fianza"} <= set(ids)
    assert not {"subasta-deposito", "registro-unico"} & set(ids)


def test_subasta_sin_hipoteca_y_turistico():
    ids = [s.id for s in roadmap("lote", False, "turistico")]
    assert {"subasta-cargas-y-posesion", "subasta-deposito", "subasta-pago",
            "registro-unico"} <= set(ids)
    assert not {"fein", "arras", "fianza", "deudas-comunidad"} & set(ids)


def test_orden_por_etapas():
    stages = [s.stage for s in roadmap("enlace", True, "habitual")]
    order = {"antes": 0, "compra": 1, "despues": 2}
    assert stages == sorted(stages, key=order.__getitem__)
