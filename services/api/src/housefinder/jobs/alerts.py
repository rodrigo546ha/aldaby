"""Alertas de trabajos fallidos (ADR-0010).

Al principio, un registro ERROR en el logger `housefinder.alertas`; el correo llega en F7.
Nunca se escribe el `payload`: solo identificador, tipo, intentos y error.
"""

from __future__ import annotations

import logging

from housefinder.db.jobs import Job

logger = logging.getLogger("housefinder.alertas")
MAX_ERROR = 500


def alert_failed(job: Job, error: str) -> None:
    logger.error(
        "Trabajo %s (%s) fallido tras %s intentos: %s",
        job.id, job.kind, job.attempts, error[:MAX_ERROR],
    )
