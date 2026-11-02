"""Altas de cuentas de la beta (F7.1, ADR-0028). Las da el administrador; no hay registro abierto.

    python -m housefinder.accounts alta ana@ejemplo.es --organizacion "Asesoría Ana"
    python -m housefinder.accounts alta tu@correo.es --organizacion Aldaby --rol admin
    python -m housefinder.accounts espera                    # lista de espera (ADR-0041)
    python -m housefinder.accounts alta luis@ejemplo.es --rol particular
    python -m housefinder.accounts restablecer ana@ejemplo.es

Cada orden imprime un enlace de un solo uso, válido siete días, para elegir la contraseña. Envíalo
tú a la persona: el enlace no se guarda en ningún sitio.
"""

from __future__ import annotations

import argparse
import os
import sys
from urllib.parse import quote

from housefinder.accounts.service import LINK_DAYS, AccountError, create_account, reset_link
from housefinder.db.connection import connect
from housefinder.db.waitlist import list_waitlist


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m housefinder.accounts")
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("alta", help="crea una cuenta y su enlace para elegir contraseña")
    new.add_argument("correo")
    new.add_argument("--organizacion",
                     help="nombre de la organización (un particular, si no se da, su correo)")
    new.add_argument("--rol", default="profesional", choices=("profesional", "admin",
                                                               "particular"))
    sub.add_parser("espera", help="lista de espera de la página de presentación")
    reset = sub.add_parser("restablecer", help="nuevo enlace para elegir contraseña")
    reset.add_argument("correo")
    parser.add_argument("--web", default=os.environ.get("HOUSEFINDER_WEB_URL",
                                                        "http://localhost:3000"),
                        help="dirección de la web (HOUSEFINDER_WEB_URL)")
    args = parser.parse_args()
    with connect() as conn:
        try:
            if args.command == "espera":
                for row in list_waitlist(conn):
                    state = (f"alta el {row.invited_at:%Y-%m-%d}" if row.invited_at
                             else "pendiente")
                    print(f"{row.created_at:%Y-%m-%d}  {row.kind:<11}  {row.email}  ({state})")
                return 0
            if args.command == "alta":
                organization = args.organizacion or (args.correo if args.rol == "particular"
                                                     else None)
                if organization is None:
                    print("Falta --organizacion", file=sys.stderr)
                    return 1
                _, token = create_account(conn, args.correo, organization, args.rol)
            else:
                token = reset_link(conn, args.correo)
        except AccountError as exc:
            print(exc, file=sys.stderr)
            return 1
        conn.commit()
    print(f"Enlace para elegir la contraseña (un solo uso, {LINK_DAYS} días):")
    print(f"{args.web.rstrip('/')}/acceso/contrasena?token={quote(token)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
