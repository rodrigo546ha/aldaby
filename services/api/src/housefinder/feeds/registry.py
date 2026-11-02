"""Alta de feeds de agencias con su consentimiento (ADR-0038).

La URL se cifra con sobre (ADR-0011), atada a su fila y a su organización: puede llevar usuario,
contraseña o un token. Nunca se imprime ni se guarda en claro.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from housefinder.crypto.envelope import DecryptionError, KeyProvider, Sealed, open_sealed, seal
from housefinder.db import agency_feeds as sql
from housefinder.db.connection import Connection
from housefinder.db.profiles import SealedRow

TABLE = "agency_feeds"
SCOPES = ("organizacion", "todos")
MAX_NAME = 120


class FeedError(ValueError):
    """Error que se puede enseñar; no repite la URL."""


@dataclass(frozen=True)
class Feed:
    id: UUID
    org_id: UUID
    agency_name: str
    scope: str
    consent_on: date
    consent_ref: str
    url: str

    def __repr__(self) -> str:  # la URL puede llevar credenciales: nunca en logs
        return f"Feed({self.id}, {self.agency_name!r}, {self.scope}, <url redactada>)"

    @property
    def offers_org(self) -> UUID | None:
        """De quién son sus ofertas: de la organización, o de todos (nulo)."""
        return self.org_id if self.scope == "organizacion" else None


def associated_data(feed_id: UUID, org_id: UUID) -> bytes:
    return f"{TABLE}:{feed_id}:{org_id}".encode()


def register(conn: Connection, keys: KeyProvider, org_id: UUID, agency_name: str, url: str,
             scope: str, consent_on: date, consent_ref: str, today: date | None = None) -> UUID:
    agency_name = " ".join(agency_name.split())
    consent_ref = " ".join(consent_ref.split())
    url = url.strip()
    if not agency_name or len(agency_name) > MAX_NAME:
        raise FeedError(f"El nombre de la agencia debe tener entre 1 y {MAX_NAME} caracteres")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise FeedError("La URL del feed debe empezar por http:// o https://")
    if scope not in SCOPES:
        raise FeedError(f"El alcance debe ser uno de: {', '.join(SCOPES)}")
    if not consent_ref:
        raise FeedError("Falta la referencia del documento de consentimiento de la agencia")
    if consent_on > (today or date.today()):
        raise FeedError("La fecha del consentimiento no puede ser futura")
    feed_id = uuid4()
    sealed = seal(url.encode(), associated_data(feed_id, org_id), keys)
    sql.insert_feed(conn, feed_id, org_id, agency_name, scope, consent_on, consent_ref,
                    SealedRow(sealed.data_enc, sealed.dek_enc, sealed.key_id, sealed.version))
    return feed_id


def active_feeds(conn: Connection, keys: KeyProvider) -> tuple[list[Feed], list[UUID]]:
    """Los feeds activos con su URL y, aparte, los que no se pueden descifrar (falta su clave):
    uno así no impide leer los demás."""
    feeds: list[Feed] = []
    locked: list[UUID] = []
    for row in sql.list_feeds(conn):
        sealed = Sealed(row.sealed.data_enc, row.sealed.dek_enc, row.sealed.key_id,
                        row.sealed.version)
        try:
            url = open_sealed(sealed, associated_data(row.id, row.org_id), keys).decode()
        except DecryptionError:
            locked.append(row.id)
            continue
        feeds.append(Feed(row.id, row.org_id, row.agency_name, row.scope, row.consent_on,
                          row.consent_ref, url))
    return feeds, locked
