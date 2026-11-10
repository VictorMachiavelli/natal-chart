"""Pure house-math tests (no ephemeris needed)."""

from __future__ import annotations

import pytest

from natal_chart._angles import norm180, norm360
from natal_chart.houses import (
    PolarHousesError,
    ascendant,
    house_cusps,
    house_of,
    midheaven,
)

EPS = 23.4392911


def test_mc_at_ramc_zero_is_aries_point():
    assert midheaven(0.0, EPS) == pytest.approx(0.0, abs=1e-12)
    assert midheaven(90.0, EPS) == pytest.approx(90.0, abs=1e-12)
    assert midheaven(180.0, EPS) == pytest.approx(180.0, abs=1e-12)


def test_ascendant_at_equator_ramc_zero():
    # At the equator with RAMC 0 the rising ecliptic point is 0° Cancer.
    assert ascendant(0.0, EPS, 0.0) == pytest.approx(90.0, abs=1e-12)


@pytest.mark.parametrize("system", ["placidus", "koch", "porphyry"])
@pytest.mark.parametrize("lat", [-60.0, -33.9, 0.0, 12.5, 48.2, 64.0])
@pytest.mark.parametrize("ramc", [0.0, 37.3, 133.0, 222.2, 301.9])
def test_quadrant_systems_share_angles_and_are_ordered(system, lat, ramc):
    cusps, used = house_cusps(ramc, EPS, lat, system)
    assert used == system
    assert cusps[0] == pytest.approx(ascendant(ramc, EPS, lat), abs=1e-9)
    assert cusps[9] == pytest.approx(midheaven(ramc, EPS), abs=1e-9)
    # cusps advance counter-clockwise, total 360
    steps = [norm360(cusps[(i + 1) % 12] - cusps[i]) for i in range(12)]
    assert all(0 < s < 180 for s in steps)
    assert sum(steps) == pytest.approx(360.0)
    # opposite cusps are 180° apart
    for i in range(6):
        assert abs(norm180(cusps[i + 6] - cusps[i])) == pytest.approx(180.0, abs=1e-9)


def test_equal_and_whole_sign():
    cusps, _ = house_cusps(123.0, EPS, 45.0, "equal")
    asc = ascendant(123.0, EPS, 45.0)
    assert [round(norm360(c - asc), 9) for c in cusps] == [30.0 * i for i in range(12)]
    ws, _ = house_cusps(123.0, EPS, 45.0, "whole_sign")
    assert ws[0] == 30.0 * int(asc // 30)
    assert all(c % 30 == 0 for c in ws)


def test_house_of_wraps_through_aries():
    cusps, _ = house_cusps(0.0, EPS, 0.0, "equal")  # asc 90 -> cusps 90,120,...
    assert house_of(90.0, cusps) == 1
    assert house_of(119.999, cusps) == 1
    assert house_of(120.0, cusps) == 2
    assert house_of(45.0, cusps) == 11
    assert house_of(359.0, cusps) == 9
    assert house_of(0.0, cusps) == 10


@pytest.mark.parametrize("system", ["placidus", "koch"])
@pytest.mark.parametrize("lat", [66.6, 70.0, -78.0])
def test_polar_latitudes_raise(system, lat):
    with pytest.raises(PolarHousesError, match="undefined"):
        house_cusps(10.0, EPS, lat, system)


def test_polar_fallback():
    cusps, used = house_cusps(10.0, EPS, 70.0, "placidus", polar_fallback="porphyry")
    assert used == "porphyry"
    assert len(cusps) == 12
    with pytest.raises(ValueError):
        house_cusps(10.0, EPS, 70.0, "placidus", polar_fallback="koch")


def test_unknown_system():
    with pytest.raises(ValueError, match="unknown house system"):
        house_cusps(0.0, EPS, 0.0, "regiomontanus")
