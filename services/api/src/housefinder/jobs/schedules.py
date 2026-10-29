"""Programaciones declaradas en `data/jobs/programaciones.yaml` (ADR-0010).

El fichero manda: aplicarlo crea o cambia cada programación y desactiva las de la base que ya no
están en él. Una programación que necesita configuración (el LLM, por ejemplo) no se programa si
falta, para no fallar cada día; se informa de ello.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from housefinder.db.connection import Connection
from housefinder.db.jobs import disable_schedules_except, upsert_schedule


@dataclass(frozen=True)
class ScheduleSpec:
    name: str
    kind: str
    at: time
    every_hours: int
    payload: dict[str, Any] = field(default_factory=dict)
    requires_env: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScheduleFile:
    timezone: ZoneInfo
    schedules: list[ScheduleSpec]


@dataclass
class SyncReport:
    programmed: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)  # nombre → motivo
    disabled: list[str] = field(default_factory=list)


def default_path() -> Path:
    """services/api/data/jobs/programaciones.yaml"""
    return Path(__file__).resolve().parents[3] / "data" / "jobs" / "programaciones.yaml"


def load(path: Path | None = None) -> ScheduleFile:
    data = yaml.safe_load((path or default_path()).read_text(encoding="utf-8"))
    specs = []
    for item in data["schedules"]:
        hour, minute = (int(p) for p in str(item["at"]).split(":"))
        specs.append(ScheduleSpec(
            name=item["name"], kind=item["kind"], at=time(hour, minute),
            every_hours=int(item["every_hours"]), payload=dict(item.get("payload") or {}),
            requires_env=tuple(item.get("requires_env") or ()),
        ))
    names = [s.name for s in specs]
    if len(set(names)) != len(names):
        raise ValueError("Hay programaciones con el mismo nombre")
    return ScheduleFile(ZoneInfo(data.get("timezone", "Europe/Madrid")), specs)


def first_run(at: time, tz: ZoneInfo, now: datetime) -> datetime:
    """La próxima vez que el reloj de `tz` marque `at`, a partir de `now`."""
    local = now.astimezone(tz)
    candidate = datetime.combine(local.date(), at, tzinfo=tz)
    if candidate <= local:
        candidate = datetime.combine(local.date() + timedelta(days=1), at, tzinfo=tz)
    return candidate


def sync(
    conn: Connection,
    schedule_file: ScheduleFile,
    known_kinds: set[str],
    env: Mapping[str, str],
    now: datetime,
) -> SyncReport:
    report = SyncReport()
    for spec in schedule_file.schedules:
        if spec.kind not in known_kinds:
            raise ValueError(f"{spec.name}: tipo de trabajo desconocido «{spec.kind}»")
        missing = [name for name in spec.requires_env if not env.get(name)]
        if missing:
            report.skipped[spec.name] = f"falta {', '.join(missing)}"
            continue
        upsert_schedule(conn, spec.name, spec.kind, spec.payload, spec.every_hours * 3600,
                        first_run(spec.at, schedule_file.timezone, now))
        report.programmed.append(spec.name)
    report.disabled = disable_schedules_except(conn, report.programmed)
    return report
