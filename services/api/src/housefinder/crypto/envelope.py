"""Cifrado de sobre con AES-256-GCM (ADR-0011).

Cada registro lleva su clave de datos (DEK); la DEK va envuelta con una clave maestra (KEK)
que identifica `key_id`. Los datos asociados (AAD) atan el contenido a su tabla, su fila y su
organización: descifrarlo en otra fila falla.
"""

from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FORMAT_VERSION = 1
KEY_BYTES = 32
NONCE_BYTES = 12
KEY_ID = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


class DecryptionError(Exception):
    """No se puede descifrar: clave, datos asociados o contenido no válidos."""


@dataclass(frozen=True)
class Sealed:
    data_enc: bytes  # nonce + contenido cifrado con la DEK
    dek_enc: bytes  # nonce + DEK cifrada con la KEK
    key_id: str  # KEK con la que se envolvió la DEK
    version: int = FORMAT_VERSION

    def __repr__(self) -> str:
        return f"Sealed(key_id={self.key_id!r}, version={self.version}, {len(self.data_enc)} B)"


class KeyProvider(Protocol):
    @property
    def current_key_id(self) -> str: ...

    def wrap(self, dek: bytes, aad: bytes) -> tuple[str, bytes]: ...

    def unwrap(self, key_id: str, wrapped: bytes, aad: bytes) -> bytes: ...


class LocalKeyProvider:
    """Claves maestras de un fichero local (desarrollo). En producción, KMS (F7)."""

    def __init__(self, keys: dict[str, bytes], current: str) -> None:
        if current not in keys:
            raise ValueError("La clave vigente no está entre las claves")
        for key_id, key in keys.items():
            if not KEY_ID.match(key_id) or len(key) != KEY_BYTES:
                raise ValueError(f"Clave maestra no válida: {key_id!r}")
        self._keys = dict(keys)
        self._current = current

    @classmethod
    def from_file(cls, path: Path) -> LocalKeyProvider:
        """Una clave por línea: `identificador base64`. La última es la vigente."""
        keys: dict[str, bytes] = {}
        current = None
        for line in path.read_text("utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key_id, _, encoded = line.partition(" ")
            keys[key_id] = base64.b64decode(encoded.strip(), validate=True)
            current = key_id
        if current is None:
            raise ValueError(f"Sin claves en {path}")
        return cls(keys, current)

    @property
    def current_key_id(self) -> str:
        return self._current

    @property
    def key_ids(self) -> tuple[str, ...]:
        return tuple(self._keys)

    def wrap(self, dek: bytes, aad: bytes) -> tuple[str, bytes]:
        nonce = os.urandom(NONCE_BYTES)
        return self._current, nonce + AESGCM(self._keys[self._current]).encrypt(nonce, dek, aad)

    def unwrap(self, key_id: str, wrapped: bytes, aad: bytes) -> bytes:
        key = self._keys.get(key_id)
        if key is None:
            raise DecryptionError(f"Clave maestra desconocida: {key_id}")
        return _decrypt(key, wrapped, aad)

    def __repr__(self) -> str:  # nunca las claves
        return f"LocalKeyProvider(claves={sorted(self._keys)}, vigente={self._current!r})"


def seal(plaintext: bytes, aad: bytes, provider: KeyProvider) -> Sealed:
    dek = AESGCM.generate_key(bit_length=KEY_BYTES * 8)
    nonce = os.urandom(NONCE_BYTES)
    data_enc = nonce + AESGCM(dek).encrypt(nonce, plaintext, aad)
    key_id, dek_enc = provider.wrap(dek, aad)
    return Sealed(data_enc, dek_enc, key_id)


def open_sealed(sealed: Sealed, aad: bytes, provider: KeyProvider) -> bytes:
    if sealed.version != FORMAT_VERSION:
        raise DecryptionError(f"Versión de formato desconocida: {sealed.version}")
    dek = provider.unwrap(sealed.key_id, sealed.dek_enc, aad)
    return _decrypt(dek, sealed.data_enc, aad)


def rewrap(sealed: Sealed, aad: bytes, provider: KeyProvider) -> Sealed:
    """Envuelve la DEK con la clave vigente, sin volver a cifrar el contenido."""
    dek = provider.unwrap(sealed.key_id, sealed.dek_enc, aad)
    key_id, dek_enc = provider.wrap(dek, aad)
    return Sealed(sealed.data_enc, dek_enc, key_id, sealed.version)


def default_keys_path() -> Path:
    configured = os.environ.get("HOUSEFINDER_KEYS_FILE")
    return Path(configured) if configured else Path.home() / ".housefinder" / "master.keys"


def provider_from_env() -> LocalKeyProvider:
    path = default_keys_path()
    if not path.exists():
        raise FileNotFoundError(
            f"No hay fichero de claves en {path}: créalo con `python -m housefinder.crypto "
            "nueva-clave`"
        )
    return LocalKeyProvider.from_file(path)


def add_key(path: Path, key_id: str) -> None:
    """Añade una clave maestra nueva (pasa a ser la vigente). Crea el fichero con permisos 0600."""
    if not KEY_ID.match(key_id):
        raise ValueError(f"Identificador de clave no válido: {key_id!r}")
    if path.exists() and key_id in LocalKeyProvider.from_file(path).key_ids:
        raise ValueError(f"Ya existe la clave {key_id}")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        encoded = base64.b64encode(AESGCM.generate_key(bit_length=KEY_BYTES * 8)).decode()
        handle.write(f"{key_id} {encoded}\n")
    os.chmod(path, 0o600)


def _decrypt(key: bytes, blob: bytes, aad: bytes) -> bytes:
    if len(blob) <= NONCE_BYTES:
        raise DecryptionError("Contenido cifrado demasiado corto")
    try:
        return AESGCM(key).decrypt(blob[:NONCE_BYTES], blob[NONCE_BYTES:], aad)
    except InvalidTag as exc:
        raise DecryptionError("No se puede descifrar: clave o datos asociados no válidos") from exc
