"""Worker de la cola (ADR-0010).

Cada vuelta: encola las programaciones vencidas, devuelve a la cola los préstamos caducados,
reserva un trabajo, lo ejecuta y apunta el resultado. Si falla, reintenta con espera creciente;
agotados los intentos, avisa.
"""

from __future__ import annotations

import os
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from housefinder.db.connection import connect
from housefinder.db.jobs import Job, claim, complete, enqueue_due, fail, requeue_stale
from housefinder.jobs.alerts import alert_failed
from housefinder.jobs.retry import backoff

Handler = Callable[[dict[str, Any]], dict[str, Any] | None]
MAX_ERROR = 2000


def default_name() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


@dataclass
class Worker:
    conninfo: str
    handlers: dict[str, Handler]
    name: str = field(default_factory=default_name)
    lease: timedelta = timedelta(hours=1)
    retry_delay: Callable[[int], timedelta] = backoff
    alert: Callable[[Job, str], None] = alert_failed

    def run_once(self) -> Job | None:
        """Una vuelta. Devuelve el trabajo ejecutado, o None si no había ninguno listo."""
        with connect(self.conninfo, autocommit=True) as conn:
            enqueue_due(conn)
            for job in requeue_stale(conn, self.lease):
                self.alert(job, "préstamo caducado")
            job = claim(conn, self.name, sorted(self.handlers))
            if job is None:
                return None
            try:
                result = self.handlers[job.kind](job.payload)
            except Exception as exc:  # cualquier fallo del trabajo se apunta y se reintenta
                error = f"{type(exc).__name__}: {exc}"[:MAX_ERROR]
                retry_in = None if job.exhausted else self.retry_delay(job.attempts)
                fail(conn, job, self.name, error, retry_in)
                if retry_in is None:
                    self.alert(job, error)
                return job
            complete(conn, job, self.name, result)
            return job

    def run_forever(self, poll_seconds: float = 5.0) -> None:
        """Ejecuta trabajos mientras los haya; si no, espera `poll_seconds`."""
        while True:
            if self.run_once() is None:
                time.sleep(poll_seconds)
