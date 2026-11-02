"""Feeds de agencias de la beta (ADR-0038). Los da de alta el administrador con el consentimiento
firmado de la agencia; la URL se pide sin mostrarla y se guarda cifrada.

    python -m housefinder.feeds alta --organizacion "Agencia Sol" --agencia "Agencia Sol" \\
        --alcance organizacion --consentimiento 2026-11-10 --documento "Contrato de alta"
    python -m housefinder.feeds lista
    python -m housefinder.feeds baja 6f1c…
"""

from __future__ import annotations

import argparse
import getpass
import sys
from datetime import date
from uuid import UUID

from housefinder.crypto.envelope import provider_from_env
from housefinder.db.agency_feeds import deactivate_feed, find_organization, list_feeds
from housefinder.db.connection import connect
from housefinder.db.offers import retire_missing
from housefinder.feeds.registry import SCOPES, FeedError, register
from housefinder.offers.channels.agency_feed import NAME


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m housefinder.feeds")
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("alta", help="da de alta el feed de una agencia (pide la URL)")
    new.add_argument("--organizacion", required=True, help="organización cliente (ya creada)")
    new.add_argument("--agencia", required=True, help="nombre de la agencia que cede la cartera")
    new.add_argument("--alcance", required=True, choices=SCOPES,
                     help="quién ve sus inmuebles: la organización o todos los usuarios")
    new.add_argument("--consentimiento", required=True, type=date.fromisoformat,
                     help="fecha del consentimiento firmado (AAAA-MM-DD)")
    new.add_argument("--documento", required=True, help="referencia del documento firmado")
    sub.add_parser("lista", help="feeds activos")
    off = sub.add_parser("baja", help="deja de leer un feed y retira sus ofertas")
    off.add_argument("id", type=UUID)
    args = parser.parse_args()
    with connect() as conn:
        if args.command == "alta":
            org_id = find_organization(conn, args.organizacion)
            if org_id is None:
                print(f"No hay ninguna organización llamada {args.organizacion!r}",
                      file=sys.stderr)
                return 1
            url = getpass.getpass("URL del feed (no se muestra): ")
            try:
                feed_id = register(conn, provider_from_env(), org_id, args.agencia, url,
                                   args.alcance, args.consentimiento, args.documento)
            except FeedError as exc:
                print(exc, file=sys.stderr)
                return 1
            conn.commit()
            print(f"Feed {feed_id} dado de alta: se leerá en el próximo trabajo diario.")
        elif args.command == "lista":
            for row in list_feeds(conn):
                print(f"{row.id}  {row.agency_name}  alcance={row.scope}  "
                      f"consentimiento={row.consent_on} ({row.consent_ref})")
        else:
            if not deactivate_feed(conn, args.id):
                print("No hay ningún feed con ese identificador", file=sys.stderr)
                return 1
            retired = retire_missing(conn, NAME, f"feed-agencia-{args.id}", [])
            conn.commit()
            print(f"Feed dado de baja; {retired} ofertas retiradas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
