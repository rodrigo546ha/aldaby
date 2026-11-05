"""Conversaciones con el asesor, cifradas (ADR-0064).

Una por cliente y oferta, en el plan de la oferta, y una por cliente sin oferta (`offer_id` None),
en «Mi plan» (ADR-0066). Se guardan la pregunta, la respuesta ya comprobada tal como se enseñó, el
texto con marcadores (para el historial) y la fecha. Caducan a los días de `data/conservacion.yaml`
desde la última pregunta. El historial que ve el modelo sale de aquí, no de la web.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from housefinder.agent.llm import Message
from housefinder.core.retention import conversation_days
from housefinder.crypto.envelope import KeyProvider, Sealed, open_sealed, seal
from housefinder.db.connection import Connection
from housefinder.db.conversations import delete_conversation, get_conversation, save_conversation
from housefinder.db.profiles import SealedRow

TABLE = "advisor_conversations"
MAX_TURNS = 20  # las más recientes; las anteriores se descartan
HISTORY_MESSAGES = 6  # lo que ve el modelo: tres vueltas con respuesta comprobada


@dataclass(frozen=True)
class Turn:
    question: str
    answer: dict[str, Any]  # la respuesta como la devolvió la API, ya comprobada
    text: str | None  # con marcadores; None si no pasó la comprobación
    at: str  # ISO 8601


GENERAL = "general"  # en el dato asociado, donde iría la oferta


def associated_data(org_id: UUID, client_id: UUID, offer_id: UUID | None) -> bytes:
    return f"{TABLE}:{org_id}:{client_id}:{offer_id or GENERAL}".encode()


def load(conn: Connection, keys: KeyProvider, org_id: UUID, client_id: UUID,
         offer_id: UUID | None) -> list[Turn]:
    """Las vueltas guardadas, de la más antigua a la más reciente; [] si no hay o ha caducado."""
    row = get_conversation(conn, org_id, client_id, offer_id, conversation_days())
    if row is None:
        return []
    sealed = Sealed(row.data_enc, row.dek_enc, row.key_id, row.version)
    data = json.loads(open_sealed(sealed, associated_data(org_id, client_id, offer_id), keys))
    return [Turn(t["question"], t["answer"], t.get("text"), t["at"]) for t in data["turns"]]


def append(conn: Connection, keys: KeyProvider, org_id: UUID, client_id: UUID,
           offer_id: UUID | None,
           question: str, answer: dict[str, Any], text: str | None) -> list[Turn]:
    """Añade una vuelta y guarda la conversación, con el plazo contado desde ahora."""
    turns = [*load(conn, keys, org_id, client_id, offer_id),
             Turn(question, answer, text, datetime.now(UTC).isoformat())][-MAX_TURNS:]
    plain = json.dumps({"turns": [t.__dict__ for t in turns]}, ensure_ascii=False).encode()
    sealed = seal(plain, associated_data(org_id, client_id, offer_id), keys)
    save_conversation(conn, org_id, client_id, offer_id,
                      SealedRow(sealed.data_enc, sealed.dek_enc, sealed.key_id, sealed.version))
    return turns


def forget(conn: Connection, org_id: UUID, client_id: UUID, offer_id: UUID | None) -> bool:
    return delete_conversation(conn, org_id, client_id, offer_id)


def history(turns: list[Turn]) -> list[Message]:
    """Las últimas vueltas con respuesta comprobada, como mensajes para el modelo."""
    messages: list[Message] = []
    for turn in turns:
        if turn.text:
            messages += [{"role": "user", "content": turn.question},
                         {"role": "assistant", "content": turn.text}]
    return messages[-HISTORY_MESSAGES:]
