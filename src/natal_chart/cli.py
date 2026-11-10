"""Command line interface: ``natal-chart 1990-05-17T14:30 --tz Europe/Moscow --lat 55.75 --lon 37.62``."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Sequence

from . import __version__
from ._angles import format_dms
from .aspects import aspects, transits
from .chart import Chart, chart
from .houses import HOUSE_SYSTEMS, PolarHousesError

_GLYPH_ASPECT = {
    "conjunction": "conj",
    "sextile": "sext",
    "square": "sqr",
    "trine": "tri",
    "opposition": "opp",
}


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="natal-chart",
        description="Tropical natal chart (planets, houses, aspects) from JPL ephemerides.",
    )
    p.add_argument("datetime", help="birth time, ISO format, e.g. 1990-05-17T14:30")
    p.add_argument("--tz", help="IANA time zone of the given time (default: UTC)", default=None)
    p.add_argument("--lat", type=float, required=True, help="latitude, north positive")
    p.add_argument("--lon", type=float, required=True, help="longitude, east positive")
    p.add_argument("--houses", choices=HOUSE_SYSTEMS, default="placidus")
    p.add_argument(
        "--polar-fallback",
        choices=("porphyry", "equal", "whole_sign"),
        default=None,
        help="house system to use where Placidus/Koch are undefined (|lat| > ~66.56)",
    )
    p.add_argument("--aspects", action="store_true", help="also list major aspects")
    p.add_argument("--transits", metavar="DATETIME", help="list transits for this time (UTC unless it has an offset)")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _chart_dict(c: Chart) -> dict:
    return {
        "datetime_utc": c.datetime_utc.isoformat(),
        "latitude": c.latitude,
        "longitude": c.longitude,
        "house_system": c.house_system,
        "polar_fallback_used": c.polar_fallback_used,
        "points": [
            {
                "name": p.name,
                "longitude": p.longitude,
                "latitude": p.latitude,
                "sign": p.sign,
                "degree": p.degree,
                "speed": p.speed,
                "retrograde": p.retrograde,
                "house": p.house,
            }
            for p in c
        ],
        "cusps": list(c.cusps),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    when = datetime.fromisoformat(args.datetime)
    tz = args.tz
    if when.tzinfo is None and tz is None:
        tz = "UTC"
    try:
        c = chart(when, args.lat, args.lon, tz=tz, house_system=args.houses,
                  polar_fallback=args.polar_fallback)
    except (PolarHousesError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    asp = aspects(c) if args.aspects else []
    tr = []
    if args.transits:
        tw = datetime.fromisoformat(args.transits)
        if tw.tzinfo is None:
            tw = tw.replace(tzinfo=timezone.utc)
        tr = transits(c, tw)

    if args.json:
        out = _chart_dict(c)
        if args.aspects:
            out["aspects"] = [a.__dict__ for a in asp]
        if args.transits:
            out["transits"] = [a.__dict__ for a in tr]
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    note = " (polar fallback)" if c.polar_fallback_used else ""
    print(f"{c.datetime_utc:%Y-%m-%d %H:%M:%S} UTC  lat {c.latitude:.4f}  lon {c.longitude:.4f}"
          f"  houses: {c.house_system}{note}")
    print()
    print(f"{'Point':<10} {'Sign':<12} {'Degree':>10}  {'Longitude':>10}  {'Speed':>8}  R  House")
    for p in c:
        r = "R" if p.retrograde else " "
        print(f"{p.name:<10} {p.sign:<12} {format_dms(p.degree):>10}  {p.longitude:10.4f}"
              f"  {p.speed:8.4f}  {r}  {p.house or '':>5}")
    print()
    print("Cusps: " + "  ".join(f"{i + 1}:{x:.2f}" for i, x in enumerate(c.cusps)))
    if args.aspects:
        print()
        print("Aspects (orb, A=applying S=separating):")
        for a in asp:
            print(f"  {a.first:<10} {_GLYPH_ASPECT[a.aspect]:<4} {a.second:<10} "
                  f"{a.orb:5.2f}  {'A' if a.applying else 'S'}")
    if args.transits:
        print()
        print(f"Transits at {args.transits} (transiting -> natal):")
        for a in tr:
            print(f"  {a.first:<10} {_GLYPH_ASPECT[a.aspect]:<4} natal {a.second:<10} "
                  f"{a.orb:5.2f}  {'A' if a.applying else 'S'}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
