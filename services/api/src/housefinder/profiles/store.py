"""Guardar y leer perfiles cifrados (ADR-0011).

El contenido se ata a su fila y a su organización con los datos asociados: un perfil cifrado
copiado a otra fila u organización no se puede descifrar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from housefinder.crypto.envelope import (
    DecryptionError,
    KeyProvider,
    Sealed,
    open_sealed,
    rewrap,
    seal,
)
from housefinder.db.connection import Connection
from housefinder.db.profiles import (
    SealedRow,
    get_profile,
    insert_profile,
    profiles_with_old_key,
    replace_wrapped_key,
    update_profile,
)
from housefinder.profiles.model import UserProfile

TABLE = "user_profiles"


class ProfileNotFound(LookupError):
    pass


def associated_data(profile_id: UUID, org_id: UUID) -> bytes:
    return f"{TABLE}:{profile_id}:{org_id}".encode()


def save_new(
    conn: Connection, keys: KeyProvider, org_id: UUID, owner_id: str, profile: UserProfile
) -> UUID:
    profile_id = uuid4()
    insert_profile(conn, profile_id, org_id, owner_id,
                   _row(_seal(profile, profile_id, org_id, keys)))
    return profile_id


def save(
    conn: Connection, keys: KeyProvider, profile_id: UUID, org_id: UUID, profile: UserProfile
) -> None:
    if not update_profile(conn, profile_id, org_id, _row(_seal(profile, profile_id, org_id, keys))):
        raise ProfileNotFound(str(profile_id))


def load(conn: Connection, keys: KeyProvider, profile_id: UUID, org_id: UUID) -> UserProfile:
    row = get_profile(conn, profile_id, org_id)
    if row is None:
        raise ProfileNotFound(str(profile_id))
    sealed = Sealed(row.data_enc, row.dek_enc, row.key_id, row.version)
    return UserProfile.parse(open_sealed(sealed, associated_data(profile_id, org_id), keys))


@dataclass(frozen=True)
class RotationReport:
    rotated: int
    failed: list[UUID] = field(default_factory=list)  # sin la clave antigua: no se tocan


def rotate(conn: Connection, keys: KeyProvider) -> RotationReport:
    """Envuelve con la clave vigente las DEK de los perfiles con una clave anterior.

    Un perfil cuya clave antigua no está en `keys` no para la rotación: se informa por su
    identificador y se deja como estaba.
    """
    rotated = 0
    failed: list[UUID] = []
    for profile_id, org_id, row in profiles_with_old_key(conn, keys.current_key_id):
        sealed = Sealed(row.data_enc, row.dek_enc, row.key_id, row.version)
        try:
            new = rewrap(sealed, associated_data(profile_id, org_id), keys)
        except DecryptionError:
            failed.append(profile_id)
            continue
        replace_wrapped_key(conn, profile_id, row.key_id, new.dek_enc, new.key_id)
        rotated += 1
    return RotationReport(rotated, failed)


def _seal(profile: UserProfile, profile_id: UUID, org_id: UUID, keys: KeyProvider) -> Sealed:
    return seal(profile.model_dump_json().encode(), associated_data(profile_id, org_id), keys)


def _row(sealed: Sealed) -> SealedRow:
    return SealedRow(sealed.data_enc, sealed.dek_enc, sealed.key_id, sealed.version)
