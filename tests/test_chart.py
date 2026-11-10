"""Chart-level tests. Need the JPL ephemeris (downloaded on first run).

All birth data is fictional.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from natal_chart import PolarHousesError, aspects, chart, positions, transits
from natal_chart._angles import norm180
from natal_chart.cli import main

# Fictional person: 17 May 1990, 14:30 local, Moscow
BIRTH = datetime(1990, 5, 17, 14, 30)
TZ = "Europe/Moscow"
LAT, LON = 55.75, 37.62


def test_meeus_example_47a_moon(ephemeris):
    # 1992 Apr 12, 0h TD; TT-UTC = 58.184 s. Meeus: apparent λ = 133.162655°,
    # computed from a *truncated* ELP-2000 series (~10-20" accurate), so this
    # is only a sanity check. We get 133.16672° (Swiss Ephemeris agrees with
    # us to < 0.1"); the difference is the truncation of Meeus' series.
    p = positions(datetime(1992, 4, 11, 23, 59, 1, 816000, tzinfo=timezone.utc))
    assert abs(norm180(p["Moon"].longitude - 133.162655)) * 3600 < 20


def test_meeus_example_25b_sun(ephemeris):
    # 1992 Oct 13.0 TD; TT-UTC = 59.184 s. Meeus (full VSOP87): λ = 199°54'21.818"
    p = positions(datetime(1992, 10, 12, 23, 59, 0, 816000, tzinfo=timezone.utc))
    expected = 199 + 54 / 60 + 21.818 / 3600
    assert abs(norm180(p["Sun"].longitude - expected)) * 3600 < 0.5


def test_local_time_and_aware_datetime_agree(ephemeris):
    a = chart(BIRTH, LAT, LON, tz=TZ)
    b = chart(BIRTH.replace(tzinfo=ZoneInfo(TZ)), LAT, LON)
    c = chart("1990-05-17T10:30:00+00:00", LAT, LON)
    assert a.datetime_utc == b.datetime_utc == c.datetime_utc
    assert a.datetime_utc == datetime(1990, 5, 17, 10, 30, tzinfo=timezone.utc)
    assert a["Moon"].longitude == pytest.approx(c["Moon"].longitude, abs=1e-9)


def test_naive_without_tz_rejected():
    with pytest.raises(ValueError, match="naive"):
        chart(BIRTH, LAT, LON)
    with pytest.raises(ValueError, match="either"):
        chart(BIRTH.replace(tzinfo=timezone.utc), LAT, LON, tz=TZ)


def test_chart_contents(ephemeris):
    c = chart(BIRTH, LAT, LON, tz=TZ)
    assert c["Sun"].sign == "Taurus"
    assert 0 <= c["Sun"].degree < 30
    assert len(c.points) == 14
    assert c["Saturn"].retrograde and not c["Sun"].retrograde
    assert all(1 <= p.house <= 12 for p in c)
    assert c.ascendant.house == 1 and c.mc.house == 10
    assert c.ascendant.longitude == pytest.approx(c.cusps[0])
    assert c.obliquity == pytest.approx(23.44, abs=0.01)
    # whole-sign house numbers follow directly from the signs
    ws = chart(BIRTH, LAT, LON, tz=TZ, house_system="whole_sign")
    asc_sign = int(ws.ascendant.longitude // 30)
    for p in ws:
        assert p.house == (int(p.longitude // 30) - asc_sign) % 12 + 1


def test_polar_chart(ephemeris):
    with pytest.raises(PolarHousesError):
        chart("2001-01-01T12:00:00+00:00", 69.65, 18.96)  # fictional, Tromsø area
    c = chart("2001-01-01T12:00:00+00:00", 69.65, 18.96, polar_fallback="porphyry")
    assert c.house_system == "porphyry" and c.polar_fallback_used
    c = chart("2001-01-01T12:00:00+00:00", 69.65, 18.96, house_system="equal")
    assert not c.polar_fallback_used


def test_speed_matches_motion(ephemeris):
    t0 = datetime(2004, 3, 3, tzinfo=timezone.utc)
    a, b = positions(t0), positions(t0 + timedelta(hours=1))
    for name in ("Sun", "Moon", "Mars", "Mean Node"):
        moved = norm180(b[name].longitude - a[name].longitude) * 24
        assert moved == pytest.approx(a[name].speed, rel=0.01, abs=1e-4)


def test_aspects_on_real_chart(ephemeris):
    c = chart(BIRTH, LAT, LON, tz=TZ)
    found = aspects(c)
    assert found == sorted(found, key=lambda a: a.orb)
    for a in found:
        assert abs(a.separation - a.angle) == pytest.approx(a.orb)
        assert not ({a.first, a.second} <= {"Ascendant", "MC"})


def test_transits(ephemeris):
    natal = chart(BIRTH, LAT, LON, tz=TZ)
    # transiting Sun exactly opposite the natal Sun half a year later
    found = transits(natal, "1990-11-17T00:00:00+00:00", orbs={"opposition": 2.0})
    sun = [a for a in found if a.first == "Sun" and a.second == "Sun"]
    assert len(sun) == 1 and sun[0].aspect == "opposition"
    for a in transits(natal, "2026-11-10T12:00:00+00:00"):
        assert a.orb <= 1.0


def test_cli_table_and_json(ephemeris, capsys):
    assert main(["1990-05-17T14:30", "--tz", TZ, "--lat", "55.75", "--lon", "37.62", "--aspects"]) == 0
    out = capsys.readouterr().out
    assert "Sun" in out and "Taurus" in out and "Aspects" in out
    assert main(["1990-05-17T14:30", "--tz", TZ, "--lat", "55.75", "--lon", "37.62", "--json",
                 "--transits", "2026-11-10T12:00"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["house_system"] == "placidus" and len(data["cusps"]) == 12
    assert "transits" in data
    assert main(["2001-01-01T12:00", "--lat", "70", "--lon", "19"]) == 2
