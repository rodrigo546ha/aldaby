"""Estado de la vivienda desde sus fotos contra el juego etiquetado (ADR-0062).

`data/evaluation/fotos.yaml` dice, para cada inmueble, si necesita reforma y qué señales se ven en
qué fotos. Las fotos están en `tests/fixtures/private/fotos/`, fuera de git. Aquí se lee el juego,
se comprueba una respuesta del modelo como se comprueba una cita (vocabulario cerrado, fotos que
existen y veredicto coherente con las señales) y se mide el acierto.

El modelo nunca da cifras: solo el veredicto y las señales, cada una con su foto.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import yaml

Verdict = Literal["necesita_reforma", "no_necesita", "no_se_sabe"]
VERDICTS: tuple[Verdict, ...] = ("necesita_reforma", "no_necesita", "no_se_sabe")
# Señal → si pide reforma (True) o dice que está en buen estado (False)
SIGNS: dict[str, bool] = {
    "cocina_antigua": True, "bano_antiguo": True, "suelo_deteriorado": True,
    "paredes_deterioradas": True, "humedades": True, "carpinteria_antigua": True,
    "instalacion_vista": True, "obra_sin_terminar": True,
    "reformado_reciente": False, "cocina_nueva": False, "bano_nuevo": False,
}


def default_labels_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "evaluation" / "fotos.yaml"


def default_photos_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "private" / "fotos"


@dataclass(frozen=True)
class Case:
    id: str
    photos: tuple[Path, ...]
    verdict: Verdict
    signs: dict[str, frozenset[int]]  # señal → fotos en las que se ve (desde 1)
    source: str  # de dónde salen las fotos y con qué derechos


@dataclass(frozen=True)
class Prediction:
    verdict: str
    signs: tuple[tuple[str, int], ...] = ()  # (señal, foto en la que la ve)


def problems(verdict: str, signs: dict[str, Any] | tuple[tuple[str, int], ...],
             photos: int) -> list[str]:
    """Lo que hace inválida una etiqueta o una respuesta del modelo (ADR-0062, punto 2)."""
    found: list[str] = []
    pairs = ([(s, i) for s, indices in signs.items() for i in indices]
             if isinstance(signs, dict) else list(signs))
    if verdict not in VERDICTS:
        found.append(f"veredicto desconocido: {verdict}")
    for sign, index in pairs:
        if sign not in SIGNS:
            found.append(f"señal fuera del vocabulario: {sign}")
        if not isinstance(index, int) or not 1 <= index <= photos:
            found.append(f"la señal {sign} cita la foto {index}, y hay {photos}")
    renovation = any(SIGNS.get(sign, False) for sign, _ in pairs)
    if verdict == "necesita_reforma" and not renovation:
        found.append("necesita_reforma sin ninguna señal de reforma")
    if verdict == "no_necesita" and renovation:
        found.append("no_necesita con señales de reforma")
    return found


def load_cases(path: Path | None = None, photos_dir: Path | None = None,
               check_files: bool = True) -> list[Case]:
    """El juego etiquetado; un error de etiqueta o una foto que falta paran la carga."""
    photos_dir = photos_dir or default_photos_dir()
    data = yaml.safe_load((path or default_labels_path()).read_text(encoding="utf-8")) or []
    cases, seen = [], set()
    for raw in data:
        case_id = str(raw["id"])
        if case_id in seen:
            raise ValueError(f"{case_id}: id repetido")
        seen.add(case_id)
        photos = tuple(photos_dir / str(p) for p in raw.get("photos") or [])
        if not photos:
            raise ValueError(f"{case_id}: sin fotos")
        if not str(raw.get("source") or "").strip():
            raise ValueError(f"{case_id}: falta `source` (de dónde salen las fotos y sus derechos)")
        signs = {str(s): [int(i) for i in indices]
                 for s, indices in (raw.get("signs") or {}).items()}
        wrong = problems(str(raw.get("verdict")), signs, len(photos))
        if wrong:
            raise ValueError(f"{case_id}: " + "; ".join(wrong))
        missing = [p.name for p in photos if check_files and not p.is_file()]
        if missing:
            raise ValueError(f"{case_id}: faltan las fotos {', '.join(missing)} en {photos_dir}")
        cases.append(Case(case_id, photos, raw["verdict"],
                          {s: frozenset(i) for s, i in signs.items()}, str(raw["source"])))
    return cases


@dataclass(frozen=True)
class PhotoReport:
    cases: int
    rejected: int  # respuestas que no pasan la comprobación: cuentan como fallo
    confusion: Counter[tuple[str, str]] = field(default_factory=Counter)  # (esperado, dado)
    signs_right: int = 0  # señal y foto que coinciden con la etiqueta
    signs_given: int = 0
    signs_expected: int = 0

    def ratio(self, part: int, whole: int) -> Decimal | None:
        return (Decimal(part) / Decimal(whole)).quantize(Decimal("0.0001")) if whole else None

    @property
    def accuracy(self) -> Decimal | None:
        right = sum(n for (expected, given), n in self.confusion.items() if expected == given)
        return self.ratio(right, self.cases)

    @property
    def renovation_precision(self) -> Decimal | None:
        """De los que dice que necesitan reforma, cuántos la necesitan."""
        said = sum(n for (_, given), n in self.confusion.items() if given == "necesita_reforma")
        return self.ratio(self.confusion[("necesita_reforma", "necesita_reforma")], said)

    @property
    def renovation_recall(self) -> Decimal | None:
        """De los que necesitan reforma, cuántos encuentra."""
        need = sum(n for (expected, _), n in self.confusion.items()
                   if expected == "necesita_reforma")
        return self.ratio(self.confusion[("necesita_reforma", "necesita_reforma")], need)

    @property
    def abstention(self) -> Decimal | None:
        """Cuántas veces dice no_se_sabe."""
        said = sum(n for (_, given), n in self.confusion.items() if given == "no_se_sabe")
        return self.ratio(said, self.cases)

    @property
    def sign_precision(self) -> Decimal | None:
        return self.ratio(self.signs_right, self.signs_given)

    @property
    def sign_recall(self) -> Decimal | None:
        return self.ratio(self.signs_right, self.signs_expected)


def score(cases: list[Case], predictions: dict[str, Prediction]) -> PhotoReport:
    """Mide las respuestas del modelo frente al juego. Una respuesta que falta o que no pasa la
    comprobación cuenta como «rechazada»: en el plan no se enseñaría nada."""
    confusion: Counter[tuple[str, str]] = Counter()
    rejected = right = given = expected = 0
    for case in cases:
        expected += sum(len(i) for i in case.signs.values())
        prediction = predictions.get(case.id)
        if prediction is None or problems(prediction.verdict, prediction.signs,
                                          len(case.photos)):
            rejected += 1
            confusion[(case.verdict, "rechazada")] += 1
            continue
        confusion[(case.verdict, prediction.verdict)] += 1
        given += len(prediction.signs)
        right += sum(1 for sign, photo in prediction.signs
                     if photo in case.signs.get(sign, frozenset()))
    return PhotoReport(len(cases), rejected, confusion, right, given, expected)
