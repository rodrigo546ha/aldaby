"""Descarga de la página que pega el usuario: una sola, a petición suya (ADR-0015).

No es un rastreador: un `GET` a esa URL, sin seguir enlaces, sin ejecutar JavaScript ni descargar
imágenes y sin reintentos. Se respeta `robots.txt`, y si el sitio bloquea o pide demostrar que no
somos un robot, se para y se pide al usuario que pegue el texto. La URL viene de fuera: antes de
cada petición se comprueba que no apunta a la red interna (SSRF).
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.robotparser import RobotFileParser

import httpx

from housefinder.offers.html_text import page_text

USER_AGENT = "HouseFinder/0.1 (enlace aportado por un usuario)"
ROBOTS_AGENT = "HouseFinder"
MAX_BYTES = 3_000_000
TIMEOUT_S = 15.0
MAX_REDIRECTS = 3
MIN_TEXT_CHARS = 500  # menos texto que esto y con marcas de comprobación: página de bloqueo
CHALLENGE_MARKERS = (
    "captcha",
    "datadome",
    "challenge-platform",
    "cf-chl",
    "are you a robot",
    "eres un robot",
    "pardon our interruption",
    "access denied",
)
BLOCKED_STATUS = {401, 403, 429}
REDIRECTS = {301, 302, 303, 307, 308}
PASTE_HINT = "Copia el texto del anuncio y pégalo en su lugar."

# Nombre y puerto → direcciones IP. Inyectable en los tests.
Resolver = Callable[[str, int], list[str]]


class LinkRefused(Exception):
    """No se descarga: el motivo es para el usuario, que puede pegar el texto."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class FetchedPage:
    url: str  # la que pegó el usuario
    final_url: str
    fetched_at: datetime
    title: str | None
    text: str
    images: list[str]

    def raw(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "final_url": self.final_url,
            "fetched_at": self.fetched_at.isoformat(),
            "title": self.title,
            "text": self.text,
            "images": self.images,
        }


def link_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S, follow_redirects=False
    )


def system_resolve(host: str, port: int) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise LinkRefused("No se encuentra el sitio de ese enlace.") from exc
    return sorted({str(info[4][0]) for info in infos})


def check_url(url: str, resolve: Resolver) -> httpx.URL:
    """La URL es pública: http(s), puerto 80 o 443 y todas sus IP globales."""
    try:
        parsed = httpx.URL(url.strip())
    except httpx.InvalidURL as exc:
        raise LinkRefused("El enlace no es una dirección web válida.") from exc
    if parsed.scheme not in ("http", "https") or not parsed.host:
        raise LinkRefused("El enlace tiene que empezar por http:// o https://.")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in (80, 443) or parsed.userinfo:
        raise LinkRefused("Ese enlace no apunta a una página web pública.")
    addresses = resolve(parsed.host, port)
    if not addresses:
        raise LinkRefused("No se encuentra el sitio de ese enlace.")
    for address in addresses:
        ip = ipaddress.ip_address(address.split("%")[0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast:
            raise LinkRefused("Ese enlace no apunta a una página web pública.")
    return parsed


def fetch_listing(
    client: httpx.Client,
    url: str,
    resolve: Resolver = system_resolve,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> FetchedPage:
    """Descarga la página del anuncio o explica por qué no (`LinkRefused`)."""
    target = check_url(url, resolve)
    if target.host == "subastas.boe.es":
        from housefinder.offers import boe_portal

        try:
            auction = boe_portal.scrape_auction(client, str(target))
            docs = boe_portal.download_documents(client, auction, max_docs=2)
            docs_text = "\n\n".join(f"[{d.title}]\n{d.text}" for d in docs)
            full_text = f"{auction.summary_text()}\n\n{docs_text}".strip()
            title = f"Subasta {auction.notice.tipo_subasta or 'judicial'} · {auction.portal_id}"
            return FetchedPage(
                url=url.strip(),
                final_url=auction.portal_url,
                fetched_at=now(),
                title=title,
                text=full_text,
                images=[],
            )
        except Exception as exc:
            raise LinkRefused(
                f"No se pudo descargar la subasta del BOE: {exc}. {PASTE_HINT}"
            ) from exc

    robots: dict[str, bool] = {}  # por origen: cada sitio al que se redirige, el suyo
    for _ in range(MAX_REDIRECTS + 1):
        origin = f"{target.scheme}://{target.host}:{target.port or ''}"
        if origin not in robots:
            robots[origin] = _robots_allow(client, target, resolve)
        if not robots[origin]:
            raise LinkRefused(f"Ese sitio no permite descargas automáticas. {PASTE_HINT}")
        status, location, content_type, body = _get(client, target)
        if status in REDIRECTS and location:
            target = check_url(str(target.join(location)), resolve)
            continue
        break
    else:
        raise LinkRefused("El enlace redirige demasiadas veces.")
    if status in BLOCKED_STATUS:
        raise LinkRefused(f"El sitio no deja descargar la página ({status}). {PASTE_HINT}")
    if status != 200:
        raise LinkRefused(f"El sitio respondió con un error ({status}).")
    if "html" not in content_type:
        raise LinkRefused("El enlace no es una página web.")
    html = body.decode(_charset(content_type), errors="replace")
    page = page_text(html)
    if len(page.text) < MIN_TEXT_CHARS and any(m in html.lower() for m in CHALLENGE_MARKERS):
        raise LinkRefused(f"El sitio pide comprobar que no somos un robot. {PASTE_HINT}")
    return FetchedPage(
        url=url.strip(),
        final_url=str(target),
        fetched_at=now(),
        title=page.title,
        text=page.text,
        images=page.images,
    )


def _get(client: httpx.Client, url: httpx.URL) -> tuple[int, str | None, str, bytes]:
    try:
        with client.stream("GET", url) as response:
            chunks: list[bytes] = []
            size = 0
            if response.status_code == 200:
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise LinkRefused("La página es demasiado grande.")
                    chunks.append(chunk)
            return (
                response.status_code,
                response.headers.get("location"),
                response.headers.get("content-type", "").lower(),
                b"".join(chunks),
            )
    except httpx.TimeoutException as exc:
        raise LinkRefused("El sitio tarda demasiado en responder.") from exc
    except httpx.HTTPError as exc:
        raise LinkRefused("No se pudo conectar con el sitio.") from exc


def _robots_allow(client: httpx.Client, url: httpx.URL, resolve: Resolver) -> bool:
    """`robots.txt` del sitio para nuestro agente (RFC 9309), siguiendo sus redirecciones."""
    target = check_url(str(url.copy_with(path="/robots.txt", query=None, fragment=None)), resolve)
    for _ in range(MAX_REDIRECTS + 1):
        status, location, _, body = _get(client, target)
        if status in REDIRECTS and location:
            target = check_url(str(target.join(location)), resolve)
            continue
        break
    else:
        return False
    if status in (401, 403) or status >= 500:
        return False  # acceso restringido o sitio caído: no se sabe, no se descarga
    if status != 200:
        return True  # sin robots.txt
    parser = RobotFileParser()
    parser.parse(body.decode("utf-8", errors="replace").splitlines())
    return parser.can_fetch(ROBOTS_AGENT, str(url))


def _charset(content_type: str) -> str:
    for part in content_type.split(";"):
        key, _, value = part.strip().partition("=")
        if key == "charset" and value:
            try:
                "".encode(value.strip('"'))
                return value.strip('"')
            except LookupError:
                break
    return "utf-8"
