# natal-chart

[![PyPI](https://img.shields.io/pypi/v/natal-chart)](https://pypi.org/project/natal-chart/) [![Python](https://img.shields.io/pypi/pyversions/natal-chart)](https://pypi.org/project/natal-chart/) [![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Tropical natal chart math for Python: planet positions, houses
(Placidus, Koch, Porphyry, Equal, Whole Sign), Ascendant/MC, mean lunar node,
mean Black Moon Lilith, major aspects and transits.

Positions come from NASA JPL ephemerides through
[Skyfield](https://rhodesmill.org/skyfield/). The package does **not** use or
contain the Swiss Ephemeris, so it can be released under the MIT license.

## Install

```bash
pip install natal-chart
```

Requires Python 3.10+. The only dependency is Skyfield (which brings NumPy).

The first call downloads the JPL DE440s ephemeris (~32 MB, covers
1849-2150) into `~/.cache/natal-chart` (override with the `NATAL_CHART_DATA`
environment variable). It is never bundled with the package. To use a
different file, e.g. the smaller DE421 (1900-2050) or DE440 (1550-2650):

```python
import natal_chart
natal_chart.set_ephemeris("de421.bsp")   # or NATAL_CHART_EPHEMERIS=de421.bsp
```

## Quickstart

```python
from natal_chart import chart, aspects, transits

# Fictional birth data: local time + IANA time zone
c = chart("1990-05-17T14:30", lat=55.75, lon=37.62, tz="Europe/Moscow")

c["Sun"].sign, round(c["Sun"].degree, 2)   # ('Taurus', 26.26)
c["Saturn"].retrograde                      # True
c["Moon"].house                             # 5
c.ascendant.longitude, c.mc.longitude       # 166.69..., 71.52...
c.cusps                                     # 12 cusp longitudes, cusp 1 first

for a in aspects(c)[:3]:
    print(a.first, a.aspect, a.second, round(a.orb, 2),
          "applying" if a.applying else "separating")

for a in transits(c, "2026-11-10T12:00:00+00:00"):
    print("transiting", a.first, a.aspect, "natal", a.second, round(a.orb, 2))
```

`chart()` accepts a timezone-aware `datetime`, or a naive one plus `tz=`.
A naive time without `tz` is rejected rather than silently treated as UTC.

Points: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune,
Pluto, `"Mean Node"`, `"Lilith"`, `"Ascendant"`, `"MC"`. Each `Point` has
`longitude`, `latitude`, `speed` (°/day), `sign`, `degree` (within sign),
`retrograde` and `house`.

### Aspects

`aspects(chart, orbs=None, points=None)` finds conjunction, sextile, square,
trine and opposition, tightest first. Default orbs:
conjunction/opposition 8°, trine/square 7°, sextile 5°. Pass your own
mapping, e.g. `orbs={"conjunction": 10, "square": 6}` (aspects left out are
not searched). `applying` is decided from the current speeds of both points.

`transits(natal, when, orbs=None)` compares the transiting planets with every
natal point (default orb 1°). The natal point is treated as fixed.

### Command line

```text
$ natal-chart 1990-05-17T14:30 --tz Europe/Moscow --lat 55.75 --lon 37.62 --aspects
1990-05-17 10:30:00 UTC  lat 55.7500  lon 37.6200  houses: placidus

Point      Sign             Degree   Longitude     Speed  R  House
Sun        Taurus        26°15'49"     56.2636    0.9636         9
Moon       Aquarius      21°37'13"    321.6204   12.9387         5
...
```

Options: `--houses {placidus,koch,porphyry,equal,whole_sign}`,
`--polar-fallback {porphyry,equal,whole_sign}`, `--aspects`,
`--transits DATETIME`, `--json`. Without `--tz` the time is taken as UTC.

## What exactly is computed

* **Planets**: geocentric *apparent* positions (light-time, aberration,
  gravitational deflection), ecliptic longitude and latitude referred to the
  **true equinox and ecliptic of date** (IAU 2006 precession + IAU 2000A
  nutation), tropical zodiac. This is the same convention as the default
  output of most astrology software. Mars-Pluto use the planetary-system
  barycenter segments of the JPL file; the offset from the planet's centre
  is below 0.1" as seen from Earth.
* **Speed**: central difference over ±0.01 day, degrees per day.
* **Mean node / mean Lilith**: ELP-2000/82 mean-element polynomials
  (Meeus, *Astronomical Algorithms*, ch. 47), plus nutation in longitude.
  Lilith (mean lunar apogee) is projected from the inclined lunar orbit onto
  the ecliptic, so it also has a small ecliptic latitude.
* **Houses**: RAMC from Skyfield's Greenwich apparent sidereal time plus the
  east longitude; true obliquity of date. Placidus is computed by iterating
  each cusp on its own diurnal/nocturnal semi-arc; Koch from Ascendants at
  the times that trisect the MC degree's semi-arc.
* **Time**: from 1972 the input is UTC with leap seconds. Before 1972 the
  given UTC is treated as UT1 (civil time followed UT then); Delta T comes
  from Skyfield's built-in model. Ambiguous or non-existent local times at
  DST changes follow Python's `datetime.fold` rule (`fold=0` by default).

### High latitudes

Placidus and Koch are undefined when part of the ecliptic never rises or sets,
i.e. for |latitude| ≥ 90° − obliquity (about 66.56°). There `chart()` raises
`PolarHousesError` with an explanation. Pass
`polar_fallback="porphyry"` (or `"equal"`, `"whole_sign"`) to get a chart
anyway; then `chart.house_system` names the system actually used and
`chart.polar_fallback_used` is `True`. Equal, Whole Sign and Porphyry work at
any latitude short of the poles.

## Accuracy

Measured against the Swiss Ephemeris 2.10 (pyswisseph, with its
`sepl_18`/`semo_18` data files) on 300 random fictional dates 1900-2100 and
latitudes within ±66°. The comparison is run at identical instants (same TT
for bodies, same UT1 for houses) so that what is measured is ephemeris,
reduction and house math, not the two libraries' Delta T models.

| Quantity | Max difference |
| --- | --- |
| Sun ... Pluto, longitude | 0.007" |
| Sun ... Pluto, latitude | 0.003" |
| Speeds | 0.00008 °/day |
| Mean Node | 0.11" |
| Mean Lilith (longitude / latitude) | 0.54" / 0.04" |
| Ascendant, MC | 0.000003° |
| Placidus, Koch, Porphyry, Equal cusps | 0.000006° |

Things that differ between libraries and are *not* in the table:

* **Delta T for future dates.** Neither library can know future Earth
  rotation; their predictions differ by a few seconds after 2026, which moves
  the Moon (0.5"/s) by up to ~13" at the same civil time (we measured 0.003"
  for 1972-2025 and 0.4" for 1900-1971).
* **Sidereal time after 2050.** From 2050-01-01 the Swiss Ephemeris switches
  to its own long-term sidereal-time formula, which differs from the IERS
  expression used here by ~1.9" (0.13 s of time).

The comparison test (`tests/test_vs_swisseph.py`) runs only when the
optional `pyswisseph` dev dependency is installed; point `SE_EPHE_PATH` at the
Swiss data files to compare against the full Swiss Ephemeris instead of its
built-in Moshier fallback.

## Ephemeris data

NASA JPL DE440 (public domain) via Skyfield. Default file DE440s; the
file is downloaded on first use and is not part of this package.

## Development

```bash
python -m venv .venv && .venv/bin/pip install -e ".[test]"
.venv/bin/pytest -s
```

All birth data in the tests is fictional. `pyswisseph` (AGPL) appears only in
the optional test extra and is never imported by the package.

## License

MIT. See [LICENSE](LICENSE).

---

Built by the team behind [AstralRead](https://astralread.com) — free natal
chart & AI astrologer.
