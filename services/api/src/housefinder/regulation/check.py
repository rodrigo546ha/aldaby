"""Comprueba las reglas de una carpeta: `python -m housefinder.regulation.check [carpeta]`."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from housefinder.regulation.rules import RuleBook, default_rules_dir


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    path = Path(args[0]) if args else default_rules_dir()
    try:
        book = RuleBook.from_dir(path)
    except ValueError as exc:
        print(exc)
        return 1
    print(f"{len(book.rules)} reglas válidas en {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
