"""Qué se cuenta de una visita (ADR-0042): la ruta normalizada, el dominio de origen y la fuente.

Solo rutas conocidas de la web; los segmentos variables se cambian por su nombre para que nunca
quede un identificador. Nada de lo que llega se guarda tal cual.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

# Rutas de la web (apps/web/app). Las de segmento variable, con su patrón y su nombre.
PATHS = frozenset({
    "/", "/simulador", "/clientes", "/perfil", "/busqueda", "/ofertas", "/anuncios",
    "/agencias", "/marca", "/acceso", "/acceso/contrasena", "/acceso/condiciones",
})
PATTERNS = (
    (re.compile(r"^/plan/[^/]+$"), "/plan/[offer]"),
    (re.compile(r"^/legal/[a-z-]{1,40}$"), None),  # el id del texto legal no es personal: se queda
)
HOST = re.compile(r"^[a-z0-9.-]{1,253}$")
SOURCE = re.compile(r"^[a-z0-9_.-]{1,40}$")
ROBOTS = re.compile(r"bot|crawl|spider|slurp|preview|headless|lighthouse|monitor|curl|wget|python",
                    re.I)


@dataclass(frozen=True)
class Visit:
    path: str
    referrer: str  # dominio, o ''
    source: str  # utm_source, o ''


def normalize_path(path: str) -> str | None:
    path = path.split("?", 1)[0].split("#", 1)[0]
    if len(path) > 1:
        path = path.rstrip("/")
    if path in PATHS:
        return path
    for pattern, name in PATTERNS:
        if pattern.match(path):
            return name or path
    return None


def referrer_host(referrer: str | None, own_host: str | None) -> str:
    """El dominio de origen, sin ruta ni parámetros; vacío si es el propio o no vale."""
    if not referrer:
        return ""
    parts = urlsplit(referrer)
    if parts.scheme not in ("http", "https"):
        return ""
    host = (parts.hostname or "").lower()
    host = host.removeprefix("www.")
    if not HOST.match(host) or host == (own_host or "").lower().removeprefix("www."):
        return ""
    return host


def visit(path: str, referrer: str | None, source: str | None,
          own_host: str | None) -> Visit | None:
    normalized = normalize_path(path)
    if normalized is None:
        return None
    clean_source = (source or "").strip().lower()
    return Visit(normalized, referrer_host(referrer, own_host),
                 clean_source if SOURCE.match(clean_source) else "")


def counts(headers: dict[str, str]) -> bool:
    """Si la petición se cuenta: no si pide no ser contada (GPC, DNT) ni si es un robot."""
    if headers.get("sec-gpc") == "1" or headers.get("dnt") == "1":
        return False
    return not ROBOTS.search(headers.get("user-agent", ""))
