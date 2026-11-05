"""Juego etiquetado y medida del estado desde las fotos (ADR-0062), con casos de resultado
conocido. Sin imágenes reales: los ficheros se crean vacíos en tmp_path."""

from collections import Counter
from decimal import Decimal

import pytest

from housefinder.evaluations.photos import Prediction, load_cases, problems, score

D = Decimal


def write(tmp_path, text, photos=()):
    for name in photos:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_bytes(b"")
    labels = tmp_path / "fotos.yaml"
    labels.write_text(text, encoding="utf-8")
    return labels


def test_el_juego_del_repositorio_se_lee():
    # Hoy está vacío: las fotos llegan con F0.6 o con fotos propias (ADR-0062)
    assert load_cases() == []


def test_un_caso_valido(tmp_path):
    labels = write(tmp_path, """
- id: piso
  photos: [piso/1.jpg, piso/2.jpg]
  verdict: necesita_reforma
  signs: {cocina_antigua: [2]}
  source: Fotos propias
""", ["piso/1.jpg", "piso/2.jpg"])
    [case] = load_cases(labels, tmp_path)
    assert case.verdict == "necesita_reforma" and case.signs == {"cocina_antigua": {2}}
    assert [p.name for p in case.photos] == ["1.jpg", "2.jpg"]


@pytest.mark.parametrize("body, message", [
    ("verdict: no_necesita\n  signs: {}", "source"),  # sin derechos declarados
    ("verdict: necesita_reforma\n  signs: {}\n  source: x", "sin ninguna señal de reforma"),
    ("verdict: no_necesita\n  signs: {humedades: [1]}\n  source: x", "con señales de reforma"),
    ("verdict: necesita_reforma\n  signs: {humedades: [3]}\n  source: x", "cita la foto 3"),
    ("verdict: necesita_reforma\n  signs: {piscina: [1]}\n  source: x", "fuera del vocabulario"),
    ("verdict: quizas\n  signs: {}\n  source: x", "veredicto desconocido"),
])
def test_etiquetas_que_no_valen(tmp_path, body, message):
    labels = write(tmp_path, f"- id: piso\n  photos: [a.jpg]\n  {body}\n", ["a.jpg"])
    with pytest.raises(ValueError, match=message):
        load_cases(labels, tmp_path)


def test_foto_que_falta_e_id_repetido(tmp_path):
    case = "- id: piso\n  photos: [a.jpg]\n  verdict: no_se_sabe\n  source: x\n"
    with pytest.raises(ValueError, match="faltan las fotos a.jpg"):
        load_cases(write(tmp_path, case), tmp_path)
    assert load_cases(write(tmp_path, case), tmp_path, check_files=False)[0].id == "piso"
    with pytest.raises(ValueError, match="id repetido"):
        load_cases(write(tmp_path, case * 2, ["a.jpg"]), tmp_path)


def test_comprobacion_de_una_respuesta_del_modelo():
    assert problems("necesita_reforma", (("cocina_antigua", 1),), photos=2) == []
    assert problems("no_se_sabe", (), photos=1) == []
    assert problems("necesita_reforma", (("cocina_antigua", 0),), photos=2) == [
        "la señal cocina_antigua cita la foto 0, y hay 2"]


def test_medida_con_valores_conocidos(tmp_path):
    # A: reforma (cocina en la 1), acierta veredicto y señal
    # B: sin reforma (cocina nueva en la 2), dice reforma con una señal que no está
    # C: no se sabe, acierta
    # D: reforma (baño y humedades en la 2), cita la foto 5 de 3: rechazada
    #   veredicto: 2 de 4 = 0,5; precisión de «reforma» 1 de 2 (A, B) = 0,5; exhaustividad 1 de 2
    #   (A, D) = 0,5; no se sabe 1 de 4 = 0,25; señales: 1 bien de 2 dadas = 0,5, de 4 esperadas
    #   = 0,25 (las de D cuentan como esperadas)
    labels = write(tmp_path, """
- {id: a, photos: [a1, a2], verdict: necesita_reforma, signs: {cocina_antigua: [1]}, source: x}
- {id: b, photos: [b1, b2], verdict: no_necesita, signs: {cocina_nueva: [2]}, source: x}
- {id: c, photos: [c1], verdict: no_se_sabe, source: x}
- {id: d, photos: [d1, d2, d3], verdict: necesita_reforma,
   signs: {bano_antiguo: [2], humedades: [2]}, source: x}
""")
    cases = load_cases(labels, tmp_path, check_files=False)
    report = score(cases, {
        "a": Prediction("necesita_reforma", (("cocina_antigua", 1),)),
        "b": Prediction("necesita_reforma", (("suelo_deteriorado", 1),)),
        "c": Prediction("no_se_sabe"),
        "d": Prediction("necesita_reforma", (("bano_antiguo", 5),)),
    })
    assert report.cases == 4 and report.rejected == 1
    assert report.confusion == Counter({
        ("necesita_reforma", "necesita_reforma"): 1, ("no_necesita", "necesita_reforma"): 1,
        ("no_se_sabe", "no_se_sabe"): 1, ("necesita_reforma", "rechazada"): 1})
    assert report.accuracy == D("0.5")
    assert (report.renovation_precision, report.renovation_recall) == (D("0.5"), D("0.5"))
    assert report.abstention == D("0.25")
    assert (report.sign_precision, report.sign_recall) == (D("0.5"), D("0.25"))
    # Sin respuesta también cuenta como rechazada
    assert score(cases, {}).rejected == 4
