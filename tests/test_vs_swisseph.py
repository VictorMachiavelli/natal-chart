"""Cross-check against the Swiss Ephemeris (optional, dev-only).

pyswisseph is AGPL-licensed and is *not* a dependency of natal-chart: it is
only imported here, and the whole module is skipped when it is missing.

Set ``SE_EPHE_PATH`` to a directory with the Swiss Ephemeris data files
(sepl_18.se1, semo_18.se1) to compare against the full Swiss Ephemeris;
without them pyswisseph falls back to its built-in Moshier ephemeris, which is
itself only good to ~1" (planets) / a few " (Moon), so wider tolerances apply.

Comparisons are made at identical instants (TT for bodies, UT1 for houses) so
that the different Delta T models of the two libraries do not enter: what is
measured is ephemeris + reduction + house math.

Note on sidereal time: from 2050-01-01 on (and before 1850) the Swiss
Ephemeris switches to its own long-term sidereal-time formula, which differs
from the IERS expression Skyfield uses by ~1.9" (0.13 s). After 2050 we
therefore compare the house math through ``swe.houses_armc`` with our own
RAMC and obliquity, and the full ``houses_ex`` path only before 2050.

All dates/places are random and fictional (seeded).
"""

from __future__ import annotations

import os
import random
from datetime import datetime, timedelta, timezone

SWISS_LTERM_SIDTIME = datetime(2050, 1, 1, tzinfo=timezone.utc)

import pytest

swe = pytest.importorskip("swisseph")

from natal_chart import PLANETS, chart  # noqa: E402
from natal_chart._angles import norm180  # noqa: E402

EPHE_PATH = os.environ.get("SE_EPHE_PATH")
FULL_SWISS = bool(EPHE_PATH) and os.path.exists(os.path.join(EPHE_PATH, "semo_18.se1"))
if FULL_SWISS:
    swe.set_ephe_path(EPHE_PATH)
FLAG = (swe.FLG_SWIEPH if FULL_SWISS else swe.FLG_MOSEPH) | swe.FLG_SPEED

# Tolerances in arcseconds (bodies) / degrees (houses).
# Full Swiss Ephemeris files are a compressed fit of JPL DE431; vs DE440 the
# measured differences are < 0.01" for all ten bodies (1900-2100),
# so 0.05" leaves margin for model details (precession/nutation, Delta T).
TOL_PLANET = 0.05 if FULL_SWISS else 3.0
TOL_MOON = 0.05 if FULL_SWISS else 10.0
TOL_SPEED = 1e-4 if FULL_SWISS else 1e-3  # deg/day (central difference)
TOL_HOUSES = 0.001  # degrees (3.6")
TOL_NODE = 1.0  # arcsec, Meeus polynomial vs Swiss's own lunar theory
TOL_LILITH = 1.0  # arcsec

IDS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}
HOUSE_CODES = {"placidus": b"P", "koch": b"K", "porphyry": b"O", "equal": b"E", "whole_sign": b"W"}


def _cases(n: int = 300) -> list[tuple[datetime, float, float]]:
    rnd = random.Random(20261110)
    start = datetime(1900, 1, 1, tzinfo=timezone.utc)
    span = (datetime(2100, 1, 1, tzinfo=timezone.utc) - start).total_seconds()
    out = []
    for _ in range(n):
        when = start + timedelta(seconds=rnd.uniform(0, span))
        out.append((when.replace(microsecond=0), rnd.uniform(-66.0, 66.0), rnd.uniform(-180, 180)))
    return out


CASES = _cases()
MAX: dict[str, float] = {}


def _track(key: str, value: float) -> None:
    MAX[key] = max(MAX.get(key, 0.0), abs(value))


@pytest.mark.parametrize("when,lat,lon", CASES)
def test_bodies_and_houses(ephemeris, when, lat, lon):
    c = chart(when, lat, lon)
    for name, body in IDS.items():
        x = swe.calc(c.jd_tt, body, FLAG)[0]
        p = c[name]
        dlon = norm180(p.longitude - x[0]) * 3600
        dlat = (p.latitude - x[1]) * 3600
        _track(f"{name} lon \"", dlon)
        _track(f"{name} lat \"", dlat)
        _track("speed deg/day", p.speed - x[3])
        tol = TOL_MOON if name == "Moon" else TOL_PLANET
        assert abs(dlon) < tol and abs(dlat) < tol, (name, dlon, dlat)
        assert abs(p.speed - x[3]) < TOL_SPEED, (name, p.speed, x[3])
        assert p.retrograde == (x[3] < 0)

    node = swe.calc(c.jd_tt, swe.MEAN_NODE, FLAG)[0]
    d = norm180(c["Mean Node"].longitude - node[0]) * 3600
    _track("Mean Node lon \"", d)
    assert abs(d) < TOL_NODE
    lil = swe.calc(c.jd_tt, swe.MEAN_APOG, FLAG)[0]
    d = norm180(c["Lilith"].longitude - lil[0]) * 3600
    _track("Lilith lon \"", d)
    _track("Lilith lat \"", (c["Lilith"].latitude - lil[1]) * 3600)
    assert abs(d) < TOL_LILITH

    for system, code in HOUSE_CODES.items():
        hc = chart(when, lat, lon, house_system=system)
        if when < SWISS_LTERM_SIDTIME:
            cusps, ascmc = swe.houses_ex(hc.jd_ut, lat, lon, code)
        else:
            cusps, ascmc = swe.houses_armc(hc.ramc, lat, hc.obliquity, code)
        dc = max(abs(norm180(a - b)) for a, b in zip(hc.cusps, cusps))
        _track(f"{system} cusps deg", dc)
        assert dc < TOL_HOUSES, (system, hc.cusps, cusps)
        _track("ASC deg", norm180(hc.ascendant.longitude - ascmc[0]))
        _track("MC deg", norm180(hc.mc.longitude - ascmc[1]))
        assert abs(norm180(hc.ascendant.longitude - ascmc[0])) < TOL_HOUSES
        assert abs(norm180(hc.mc.longitude - ascmc[1])) < TOL_HOUSES


def test_report_max_deviation():
    """Print the measured maxima (run with ``pytest -s``)."""
    if not MAX:
        pytest.skip("no comparisons ran")
    print(f"\nSwiss Ephemeris mode: {'files' if FULL_SWISS else 'Moshier'}; {len(CASES)} cases")
    for key in sorted(MAX):
        print(f"  max |diff| {key:<22} {MAX[key]:.6f}")
