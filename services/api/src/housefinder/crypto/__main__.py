"""Claves maestras locales (ADR-0011).

    python -m housefinder.crypto nueva-clave [ID]   añade una clave vigente al fichero de claves
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from housefinder.crypto.envelope import add_key, default_keys_path


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m housefinder.crypto")
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("nueva-clave", help="añade una clave maestra vigente")
    new.add_argument("id", nargs="?", default=f"k{datetime.now(UTC):%Y%m%d%H%M%S}")
    args = parser.parse_args()
    path = default_keys_path()
    add_key(path, args.id)
    print(f"Clave {args.id} añadida en {path} (permisos 0600). Guárdala fuera del repositorio.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
