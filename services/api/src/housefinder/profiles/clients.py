"""Clientes de un profesional con su nombre cifrado (F7.2, ADR-0029, ADR-0011).

El nombre lo pone el profesional y se cifra con sobre, atado a su fila y su organización: un nombre
cifrado copiado a otra fila u organización no se puede descifrar. Borrar un cliente borra sus
perfiles y su entrevista.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from housefinder.crypto.envelope import KeyProvider, Sealed, open_sealed, seal
from housefinder.db import clients as sql
from housefinder.db.connection import Connection
from housefinder.db.profiles import SealedRow

TABLE = "clients"
MAX_NAME = 80


class ClientError(ValueError):
    """Error que se puede enseñar al usuario; no repite el nombre."""


@dataclass(frozen=True)
class Client:
    id: UUID
    name: str
    has_profile: bool

    def __repr__(self) -> str:  # el nombre es un dato personal: nunca en logs
        return f"Client({self.id}, <nombre redactado>)"


def associated_data(client_id: UUID, org_id: UUID) -> bytes:
    return f"{TABLE}:{client_id}:{org_id}".encode()


def create(conn: Connection, keys: KeyProvider, org_id: UUID, name: str,
           informed: bool = False) -> UUID:
    name = " ".join(name.split())
    if not name:
        raise ClientError("Escribe un nombre para el cliente")
    if len(name) > MAX_NAME:
        raise ClientError(f"El nombre puede tener {MAX_NAME} caracteres como mucho")
    client_id = uuid4()
    sealed = seal(name.encode(), associated_data(client_id, org_id), keys)
    sql.insert_client(conn, client_id, org_id,
                      SealedRow(sealed.data_enc, sealed.dek_enc, sealed.key_id, sealed.version),
                      informed)
    return client_id


def list_all(conn: Connection, keys: KeyProvider, org_id: UUID) -> list[Client]:
    result = []
    for row in sql.list_clients(conn, org_id):
        sealed = Sealed(row.sealed.data_enc, row.sealed.dek_enc, row.sealed.key_id,
                        row.sealed.version)
        name = open_sealed(sealed, associated_data(row.id, org_id), keys).decode()
        result.append(Client(row.id, name, row.has_profile))
    return result


def belongs(conn: Connection, client_id: UUID, org_id: UUID) -> bool:
    return sql.client_in_org(conn, client_id, org_id)


def delete(conn: Connection, client_id: UUID, org_id: UUID) -> None:
    """Borrado definitivo: nombre, perfiles y entrevista (derecho de supresión)."""
    if not sql.delete_client(conn, client_id, org_id):
        raise ClientError("No existe ese cliente")
