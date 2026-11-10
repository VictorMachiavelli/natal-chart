"""Major aspects within a chart and transits to a natal chart."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from typing import Iterable, Mapping

from ._angles import norm180
from .chart import ASCENDANT, MC, PLANETS, Chart, Point, positions

_ANGLES = {ASCENDANT, MC}

ASPECT_ANGLES: dict[str, float] = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "opposition": 180.0,
}

DEFAULT_ORBS: dict[str, float] = {
    "conjunction": 8.0,
    "opposition": 8.0,
    "trine": 7.0,
    "square": 7.0,
    "sextile": 5.0,
}

DEFAULT_TRANSIT_ORBS: dict[str, float] = {name: 1.0 for name in ASPECT_ANGLES}


@dataclass(frozen=True)
class Aspect:
    """An aspect between two points.

    ``orb`` is the absolute distance from exactness in degrees. ``applying``
    is True when the orb is shrinking given the current speeds of both
    points (for transits the natal point is fixed).
    """

    first: str
    second: str
    aspect: str
    angle: float
    separation: float
    """Shortest angular distance between the two points, 0..180."""
    orb: float
    applying: bool

    @property
    def separating(self) -> bool:
        return not self.applying


def _aspect_between(
    p1: Point, p2: Point, orbs: Mapping[str, float], speed1: float, speed2: float
) -> Aspect | None:
    sep = norm180(p2.longitude - p1.longitude)  # signed, p1 -> p2
    dist = abs(sep)
    best: Aspect | None = None
    for name, max_orb in orbs.items():
        angle = ASPECT_ANGLES[name]
        dev = dist - angle
        if abs(dev) > max_orb:
            continue
        # d(dist)/dt; at sep == 0 the sign is irrelevant for a conjunction
        rate = (speed2 - speed1) * (1.0 if sep >= 0 else -1.0)
        applying = bool(dev * rate < 0)
        cand = Aspect(p1.name, p2.name, name, angle, dist, abs(dev), applying)
        if best is None or cand.orb < best.orb:
            best = cand
    return best


def _check_orbs(orbs: Mapping[str, float]) -> None:
    unknown = set(orbs) - set(ASPECT_ANGLES)
    if unknown:
        raise ValueError(f"unknown aspect(s) {sorted(unknown)}; known: {list(ASPECT_ANGLES)}")


def aspects(
    chart: Chart,
    orbs: Mapping[str, float] | None = None,
    points: Iterable[str] | None = None,
) -> list[Aspect]:
    """Major aspects between the points of a chart, tightest first.

    Args:
        chart: a :class:`~natal_chart.chart.Chart`.
        orbs: maximum orb per aspect name in degrees; aspects not in the
            mapping are not searched. Defaults to :data:`DEFAULT_ORBS`.
        points: names of points to consider (default: all chart points,
            including the Ascendant and MC; the ASC-MC pair itself is skipped).
    """
    orbs = DEFAULT_ORBS if orbs is None else orbs
    _check_orbs(orbs)
    names = list(chart.points) if points is None else list(points)
    found: list[Aspect] = []
    for a, b in combinations(names, 2):
        if a in _ANGLES and b in _ANGLES:
            continue  # ASC-MC geometry is not an aspect
        p1, p2 = chart[a], chart[b]
        asp = _aspect_between(p1, p2, orbs, p1.speed, p2.speed)
        if asp is not None:
            found.append(asp)
    return sorted(found, key=lambda x: x.orb)


def transits(
    natal: Chart,
    when: datetime | str,
    tz: str | None = None,
    orbs: Mapping[str, float] | None = None,
    transiting: Iterable[str] = PLANETS,
    natal_points: Iterable[str] | None = None,
) -> list[Aspect]:
    """Aspects from transiting planets at ``when`` to natal points.

    In each returned :class:`Aspect`, ``first`` is the transiting body and
    ``second`` the natal point. Natal points are treated as fixed when
    deciding applying/separating. Default orbs: 1° (:data:`DEFAULT_TRANSIT_ORBS`).
    """
    orbs = DEFAULT_TRANSIT_ORBS if orbs is None else orbs
    _check_orbs(orbs)
    sky = positions(when, tz)
    targets = list(natal.points) if natal_points is None else list(natal_points)
    found: list[Aspect] = []
    for t_name in transiting:
        tp = sky[t_name]
        for n_name in targets:
            asp = _aspect_between(tp, natal[n_name], orbs, tp.speed, 0.0)
            if asp is not None:
                found.append(asp)
    return sorted(found, key=lambda x: x.orb)
