"""Mean lunar points against Meeus, and aspect logic on synthetic charts."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from natal_chart import Aspect, Chart, Point, aspects
from natal_chart.points import mean_node


def test_mean_node_meeus_example_47a():
    # Meeus, Astronomical Algorithms 2nd ed., example 47.a: 1992 Apr 12, 0h TD
    T = (2448724.5 - 2451545.0) / 36525.0
    assert mean_node(T) == pytest.approx(274.400656, abs=1e-6)


def _chart(points: dict[str, tuple[float, float]]) -> Chart:
    pts = {n: Point(n, lon, 0.0, spd) for n, (lon, spd) in points.items()}
    return Chart(
        datetime_utc=datetime(2000, 1, 1, tzinfo=timezone.utc),
        latitude=0.0,
        longitude=0.0,
        house_system="equal",
        polar_fallback_used=False,
        cusps=tuple(float(30 * i) for i in range(12)),  # type: ignore[arg-type]
        ramc=0.0,
        obliquity=23.44,
        jd_ut=2451544.5,
        jd_tt=2451544.5,
        points=pts,
    )


def _one(c: Chart, **kw) -> Aspect:
    found = aspects(c, **kw)
    assert len(found) == 1, found
    return found[0]


def test_trine_applying_and_separating():
    # fast A at 10°, slow B at 132°: separation 122°, A closes the gap -> applying
    a = _one(_chart({"A": (10.0, 1.0), "B": (132.0, 0.0)}))
    assert (a.aspect, a.applying) == ("trine", True)
    assert a.orb == pytest.approx(2.0)
    # A at 14°: separation 118° and shrinking, i.e. moving away from 120°
    a = _one(_chart({"A": (14.0, 1.0), "B": (132.0, 0.0)}))
    assert (a.aspect, a.orb, a.separating) == ("trine", pytest.approx(2.0), True)
    # same position but A retrograde: back towards 120° -> applying
    assert _one(_chart({"A": (14.0, -1.0), "B": (132.0, 0.0)})).applying
    # both moving: only the relative speed matters
    assert _one(_chart({"A": (10.0, 1.2), "B": (132.0, 1.0)})).applying


def test_aspect_across_aries_point():
    a = _one(_chart({"A": (355.0, 1.0), "B": (3.0, 0.0)}))
    assert a.aspect == "conjunction"
    assert a.separation == pytest.approx(8.0)
    assert a.applying


def test_opposition_and_custom_orbs():
    c = _chart({"A": (0.0, 0.0), "B": (176.0, 1.0)})
    assert _one(c).aspect == "opposition"
    assert aspects(c, orbs={"opposition": 3.0}) == []
    with pytest.raises(ValueError, match="unknown aspect"):
        aspects(c, orbs={"quincunx": 2.0})


def test_tightest_first():
    c = _chart({"A": (0.0, 0.0), "B": (91.0, 0.0), "C": (180.5, 0.0)})
    names = [(x.first, x.second, x.aspect) for x in aspects(c)]
    assert names[0] == ("A", "C", "opposition")
    assert ("A", "B", "square") in names and ("B", "C", "square") in names
