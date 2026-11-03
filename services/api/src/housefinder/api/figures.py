"""Cifras en las respuestas de la API: los importes viajan como texto (D11)."""

from __future__ import annotations

from pydantic import BaseModel

from housefinder.core.figures import Figure, Series


class SourceOut(BaseModel):
    kind: str
    id: str
    provisional: bool


class FigureOut(BaseModel):
    key: str
    value: str
    unit: str
    formula: str
    sources: list[SourceOut]
    provisional: bool
    as_of: str | None
    low: str | None
    high: str | None


def figure_out(figure: Figure) -> FigureOut:
    return FigureOut.model_validate(figure.to_dict())


class PointOut(BaseModel):
    x: int
    y: str


class SeriesOut(BaseModel):
    """Una cifra año a año (ADR-0050), con fórmula y fuentes como una cifra."""

    key: str
    unit: str
    x_unit: str
    points: list[PointOut]
    formula: str
    sources: list[SourceOut]
    provisional: bool


def series_out(series: Series) -> SeriesOut:
    return SeriesOut.model_validate(series.to_dict())
