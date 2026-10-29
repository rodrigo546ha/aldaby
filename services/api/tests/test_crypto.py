"""Cifrado de sobre (ADR-0011): ida y vuelta, manipulación, datos asociados, rotación y claves."""

import os
import stat
from pathlib import Path

import pytest

from housefinder.crypto.envelope import (
    DecryptionError,
    LocalKeyProvider,
    Sealed,
    add_key,
    open_sealed,
    rewrap,
    seal,
)

AAD = b"user_profiles:1:org-a"


def provider(*ids: str) -> LocalKeyProvider:
    return LocalKeyProvider({i: os.urandom(32) for i in ids}, ids[-1])


def test_ida_y_vuelta():
    keys = provider("k1")
    sealed = seal(b"ingresos 4321.98", AAD, keys)
    assert sealed.key_id == "k1"
    assert b"4321" not in sealed.data_enc + sealed.dek_enc
    assert open_sealed(sealed, AAD, keys) == b"ingresos 4321.98"


def test_cada_cifrado_es_distinto():
    keys = provider("k1")
    a, b = seal(b"igual", AAD, keys), seal(b"igual", AAD, keys)
    assert a.data_enc != b.data_enc and a.dek_enc != b.dek_enc


def test_otros_datos_asociados_no_descifran():
    keys = provider("k1")
    sealed = seal(b"x", AAD, keys)
    with pytest.raises(DecryptionError):
        open_sealed(sealed, b"user_profiles:2:org-a", keys)  # otra fila


def test_contenido_manipulado():
    keys = provider("k1")
    sealed = seal(b"x" * 40, AAD, keys)
    flipped = bytearray(sealed.data_enc)
    flipped[-1] ^= 1
    with pytest.raises(DecryptionError):
        open_sealed(Sealed(bytes(flipped), sealed.dek_enc, sealed.key_id), AAD, keys)


def test_clave_desconocida_u_otra_clave():
    sealed = seal(b"x", AAD, provider("k1"))
    with pytest.raises(DecryptionError, match="desconocida"):
        open_sealed(sealed, AAD, provider("k2"))
    with pytest.raises(DecryptionError):
        open_sealed(sealed, AAD, provider("k1"))  # mismo identificador, otra clave


def test_rotacion_sin_volver_a_cifrar_el_contenido():
    old = os.urandom(32)
    before = LocalKeyProvider({"k1": old}, "k1")
    sealed = seal(b"perfil", AAD, before)
    both = LocalKeyProvider({"k1": old, "k2": os.urandom(32)}, "k2")
    rotated = rewrap(sealed, AAD, both)
    assert rotated.key_id == "k2" and rotated.data_enc == sealed.data_enc
    only_new = LocalKeyProvider({"k2": both._keys["k2"]}, "k2")
    assert open_sealed(rotated, AAD, only_new) == b"perfil"


def test_fichero_de_claves(tmp_path: Path):
    path = tmp_path / "claves" / "master.keys"
    add_key(path, "k1")
    add_key(path, "k2")
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    keys = LocalKeyProvider.from_file(path)
    assert keys.key_ids == ("k1", "k2") and keys.current_key_id == "k2"
    with pytest.raises(ValueError, match="Ya existe"):
        add_key(path, "k2")


def test_la_representacion_no_muestra_claves():
    secret = os.urandom(32)
    keys = LocalKeyProvider({"k1": secret}, "k1")
    assert secret.hex() not in repr(keys) and str(list(secret)) not in repr(keys)
    assert "k1" in repr(keys)
    assert "B)" in repr(seal(b"x", AAD, keys))  # el sobre solo muestra el tamaño


def test_claves_no_validas():
    with pytest.raises(ValueError):
        LocalKeyProvider({"k1": b"corta"}, "k1")
    with pytest.raises(ValueError):
        LocalKeyProvider({"k1": os.urandom(32)}, "k2")
