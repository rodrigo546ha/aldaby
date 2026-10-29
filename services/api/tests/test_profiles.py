"""Perfiles cifrados (ADR-0011): redacción, almacenamiento y ausencia de datos en los logs.

Importes inventados y fáciles de buscar: 4321.98 de ingresos, 876.54 de deudas, 98765.43 de ahorro.
"""

import logging
import os

import pytest

from housefinder.crypto.envelope import DecryptionError, LocalKeyProvider
from housefinder.profiles.model import ProfileError, UserProfile

SECRETS = ("4321.98", "4321,98", "876.54", "98765.43", "1984")
DATA = {
    "net_monthly_income": "4321.98",
    "existing_monthly_debt": "876.54",
    "available_savings": "98765.43",
    "birth_year": 1984,
    "residence": "ES-13",
    "taxable_base": "51234.00",
}


def leaks(text: str) -> list[str]:
    return [s for s in SECRETS if s in text]


def test_el_perfil_nunca_se_muestra():
    profile = UserProfile.parse(DATA)
    percent = "%s" % profile  # noqa: UP031 — es la forma que usa logging
    shown = [repr(profile), str(profile), f"{profile}", f"{profile!r}", percent,
             repr({"perfil": profile}), repr([profile])]
    assert all(s == "UserProfile(<redactado>)" or "redactado" in s for s in shown)
    assert not leaks(" ".join(shown))


def test_los_errores_de_validacion_no_repiten_los_valores():
    with pytest.raises(ProfileError) as exc:
        UserProfile.parse({**DATA, "net_monthly_income": "-4321.98", "residence": "Madrid 1984"})
    message = str(exc.value)
    assert "net_monthly_income" in message and "residence" in message
    assert not leaks(message)
    assert exc.value.__cause__ is None  # sin el ValidationError original encadenado


# --- Contra la base de datos -------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")


def keys(*ids):
    return LocalKeyProvider({i: os.urandom(32) for i in ids}, ids[-1])


@pytest.fixture
def conn(migrated_database: str):
    with psycopg.connect(migrated_database, autocommit=True) as connection:
        yield connection


@pytest.fixture
def org(conn):
    from housefinder.db.profiles import create_organization

    return create_organization(conn, "Prueba", "particular")


@pytest.mark.db
def test_guardar_y_leer(conn, org):
    from housefinder.profiles.store import load, save, save_new

    k = keys("k1")
    profile_id = save_new(conn, k, org, "usuario-1", UserProfile.parse(DATA))
    assert load(conn, k, profile_id, org).net_monthly_income == UserProfile.parse(
        DATA).net_monthly_income
    raw = conn.execute("SELECT data_enc, dek_enc FROM user_profiles WHERE id = %s",
                       (profile_id,)).fetchone()
    blob = bytes(raw[0]) + bytes(raw[1])
    assert b"4321" not in blob and b"net_monthly_income" not in blob
    changed = UserProfile.parse({**DATA, "available_savings": "1000"})
    save(conn, k, profile_id, org, changed)
    assert str(load(conn, k, profile_id, org).available_savings) == "1000"


@pytest.mark.db
def test_otra_organizacion_no_lo_ve(conn, org):
    from housefinder.db.profiles import create_organization
    from housefinder.profiles.store import ProfileNotFound, load, save_new

    k = keys("k1")
    profile_id = save_new(conn, k, org, "usuario-1", UserProfile.parse(DATA))
    other = create_organization(conn, "Otra", "profesional")
    with pytest.raises(ProfileNotFound):
        load(conn, k, profile_id, other)


@pytest.mark.db
def test_copiar_el_cifrado_a_otra_fila_no_sirve(conn, org):
    from housefinder.profiles.store import load, save_new

    k = keys("k1")
    victim = save_new(conn, k, org, "usuario-1", UserProfile.parse(DATA))
    attacker = save_new(conn, k, org, "usuario-2",
                        UserProfile.parse({**DATA, "net_monthly_income": "1"}))
    conn.execute(
        "UPDATE user_profiles SET data_enc = v.data_enc, dek_enc = v.dek_enc "
        "FROM user_profiles v WHERE v.id = %s AND user_profiles.id = %s", (victim, attacker))
    with pytest.raises(DecryptionError):
        load(conn, k, attacker, org)


@pytest.mark.db
def test_rotacion_de_la_clave_maestra(conn, org):
    from housefinder.profiles.store import load, rotate, save_new

    old = os.urandom(32)
    k1 = LocalKeyProvider({"rot-1": old}, "rot-1")
    profile_id = save_new(conn, k1, org, "usuario-1", UserProfile.parse(DATA))
    new = os.urandom(32)
    both = LocalKeyProvider({"rot-1": old, "rot-2": new}, "rot-2")
    report = rotate(conn, both)
    assert report.rotated >= 1 and profile_id not in report.failed
    only_new = LocalKeyProvider({"rot-2": new}, "rot-2")
    assert load(conn, only_new, profile_id, org).birth_year == 1984


@pytest.mark.db
def test_un_flujo_completo_no_deja_datos_en_los_logs(conn, org, caplog):
    from housefinder.profiles.store import load, rotate, save, save_new

    caplog.set_level(logging.DEBUG)  # todos los loggers, psycopg incluido
    logging.getLogger("psycopg").setLevel(logging.DEBUG)
    log = logging.getLogger("housefinder.prueba")
    k = keys("k1")
    profile = UserProfile.parse(DATA)
    profile_id = save_new(conn, k, org, "usuario-1", profile)
    log.info("guardado %s %r", profile, profile)
    loaded = load(conn, k, profile_id, org)
    log.debug("leído %s", loaded)
    save(conn, k, profile_id, org, loaded)
    report = rotate(conn, keys("k1", "k2"))  # sin la k1 antigua: no puede rotar este perfil
    assert profile_id in report.failed
    log.warning("perfiles sin rotar: %s", report.failed)
    # El valor erróneo va en una variable: el traceback muestra líneas de código, y el test
    # comprueba los valores en ejecución, no el texto del propio test.
    invalid = dict(DATA, net_monthly_income="-" + DATA["net_monthly_income"])
    try:
        UserProfile.parse(invalid)
    except ProfileError:
        log.exception("perfil no válido")
    assert caplog.records, "el test tiene que capturar registros"
    assert not leaks(caplog.text)
