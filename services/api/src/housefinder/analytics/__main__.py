"""Embudo de alta y orígenes de las visitas (F8.6, ADR-0042).

    python -m housefinder.analytics embudo                  # los últimos 30 días
    python -m housefinder.analytics embudo --desde 2026-11-01 --hasta 2026-11-30
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from housefinder.analytics.funnel import funnel
from housefinder.db.analytics import funnel_counts, top_referrers, views
from housefinder.db.connection import connect

MADRID = ZoneInfo("Europe/Madrid")


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m housefinder.analytics")
    sub = parser.add_subparsers(dest="command", required=True)
    report = sub.add_parser("embudo", help="embudo de alta de particulares y orígenes")
    report.add_argument("--desde", type=date.fromisoformat)
    report.add_argument("--hasta", type=date.fromisoformat)
    args = parser.parse_args()
    end = args.hasta or datetime.now(MADRID).date()
    start = args.desde or end - timedelta(days=29)
    with connect() as conn:
        counts = {**funnel_counts(conn, start, end), "visits": views(conn, start, end, "/")}
        counts["waitlist"] = counts.pop("waitlist_particulares")
        professionals = funnel_counts(conn, start, end)["waitlist"] - counts["waitlist"]
        origins = top_referrers(conn, start, end)
    print(f"Embudo de particulares del {start} al {end} (visitas: páginas vistas, no personas)")
    for step in funnel(counts):
        share = (f"  ({step.of_previous * 100:.1f} % del paso anterior)"
                 if step.of_previous is not None else "")
        print(f"  {step.count:>7}  {step.name}{share}")
    print(f"  {professionals:>7}  Profesionales apuntados a la lista de espera (aparte)")
    if origins:
        print("Orígenes de las visitas a la página de presentación:")
        for origin, count in origins:
            print(f"  {count:>7}  {origin}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
