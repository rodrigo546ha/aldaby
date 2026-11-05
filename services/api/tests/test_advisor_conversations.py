"""Conversaciones con el asesor cifradas 30 días (ADR-0064)."""

import os
from uuid import uuid4

import pytest

from housefinder.advisor import conversations
from housefinder.advisor.conversations import Turn, history
from housefinder.core.retention import conversation_days
from housefinder.crypto.envelope import DecryptionError, LocalKeyProvider
from housefinder.legal.documents import load as legal_documents


def turn(question, text):
    return Turn(question, {"answer": None, "text": text, "failure": None, "notes": []}, text,
                "2026-11-05T10:00:00+00:00")


def test_el_plazo_es_un_dato_y_lo_citan_los_textos_legales():
    days = conversation_days()
    assert days == 30
    docs = legal_documents()
    assert f"{days} días desde la última pregunta" in docs["privacidad"].text
    assert f"{days} días de la última pregunta" in docs["encargo"].text


def test_el_historial_solo_lleva_respuestas_comprobadas_y_las_ultimas():
    turns = [turn(f"p{i}", None if i == 1 else f"r{i}") for i in range(6)]
    messages = history(turns)
    assert len(messages) == 6  # tres vueltas
    assert [m["content"] for m in messages] == ["p3", "r3", "p4", "r4", "p5", "r5"]
    assert all(m["content"] != "p1" for m in history(turns[:3]))  # la rechazada no entra


psycopg = pytest.importorskip("psycopg")


@pytest.fixture
def setting(migrated_database: str):
    from conftest import add_client

    from housefinder.db.profiles import get_or_create_organization

    with psycopg.connect(migrated_database) as conn:
        org = get_or_create_organization(conn, f"conversaciones-{uuid4().hex[:6]}", "particular")
        client = add_client(conn, org)
        offer = conn.execute(
            "INSERT INTO offers (channel, external_id, kind, raw, raw_sha256) "
            "VALUES ('prueba', %s, 'lote', '{}', '') RETURNING id", (str(uuid4()),)).fetchone()[0]
        conn.commit()
    keys = LocalKeyProvider({"prueba": os.urandom(32)}, "prueba")
    return migrated_database, keys, org, client, offer


@pytest.mark.db
def test_se_guarda_cifrada_y_se_lee_con_su_clave(setting):
    database, keys, org, client, offer = setting
    with psycopg.connect(database) as conn:
        conversations.append(conn, keys, org, client, offer, "¿Me queda dinero?",
                             {"text": "Sí"}, "Sí")
        conn.commit()
        assert [t.question for t in conversations.load(conn, keys, org, client, offer)] == [
            "¿Me queda dinero?"]
        stored = bytes(conn.execute("SELECT data_enc FROM advisor_conversations "
                                    "WHERE offer_id = %s", (offer,)).fetchone()[0])
        assert b"dinero" not in stored
        # Otro cliente de la misma organización no la ve
        assert conversations.load(conn, keys, org, uuid4(), offer) == []
        # Con otra clave maestra no se abre
        other = LocalKeyProvider({"prueba": os.urandom(32)}, "prueba")
        with pytest.raises(DecryptionError):
            conversations.load(conn, other, org, client, offer)


@pytest.mark.db
def test_se_guardan_las_ultimas_y_caduca(setting):
    from housefinder.db.conversations import purge_expired

    database, keys, org, client, offer = setting
    with psycopg.connect(database) as conn:
        for i in range(conversations.MAX_TURNS + 3):
            conversations.append(conn, keys, org, client, offer, f"p{i}", {}, f"r{i}")
        turns = conversations.load(conn, keys, org, client, offer)
        assert len(turns) == conversations.MAX_TURNS and turns[0].question == "p3"
        # A los 30 días de la última pregunta ya no se devuelve, y el borrado nocturno la quita
        conn.execute("UPDATE advisor_conversations SET updated_at = now() - interval '30 days' "
                     "WHERE offer_id = %s", (offer,))
        assert conversations.load(conn, keys, org, client, offer) == []
        assert purge_expired(conn, conversation_days()) >= 1
        assert conn.execute("SELECT count(*) FROM advisor_conversations WHERE offer_id = %s",
                            (offer,)).fetchone()[0] == 0
        conversations.append(conn, keys, org, client, offer, "otra", {}, "r")
        assert conversations.forget(conn, org, client, offer) is True
        assert conversations.load(conn, keys, org, client, offer) == []


@pytest.mark.db
def test_la_conversacion_general_va_aparte_y_caduca_igual(setting):
    # «Mi plan», sin oferta (ADR-0066): otra fila, otro dato asociado, el mismo plazo
    from housefinder.db.conversations import purge_expired

    database, keys, org, client, offer = setting
    assert conversations.associated_data(org, client, None).endswith(b":general")
    with psycopg.connect(database) as conn:
        conversations.append(conn, keys, org, client, None, "¿Cuál me encaja?", {}, "Esta")
        conversations.append(conn, keys, org, client, offer, "¿Y esta?", {}, "Sí")
        assert [t.question for t in conversations.load(conn, keys, org, client, None)] == [
            "¿Cuál me encaja?"]
        assert [t.question for t in conversations.load(conn, keys, org, client, offer)] == [
            "¿Y esta?"]
        stored = bytes(conn.execute("SELECT data_enc FROM advisor_general_conversations "
                                    "WHERE client_id = %s", (client,)).fetchone()[0])
        assert b"encaja" not in stored
        conn.execute("UPDATE advisor_general_conversations "
                     "SET updated_at = now() - interval '30 days' WHERE client_id = %s", (client,))
        assert conversations.load(conn, keys, org, client, None) == []
        assert purge_expired(conn, conversation_days()) >= 1
        assert conversations.load(conn, keys, org, client, offer) != []  # la de la oferta sigue
        conversations.append(conn, keys, org, client, None, "otra", {}, "r")
        assert conversations.forget(conn, org, client, None) is True
        assert conversations.load(conn, keys, org, client, None) == []
