"""Natal chart computation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterator
from zoneinfo import ZoneInfo

from skyfield.framelib import ecliptic_frame
from skyfield.nutationlib import iau2000a_radians, mean_obliquity

from . import _ephemeris
from ._angles import norm180, norm360, sign_of
from .houses import Cusps, ascendant, house_cusps, house_of, midheaven
from .points import mean_apogee, mean_apogee_speed, mean_node, mean_node_speed

PLANETS: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
)
MEAN_NODE = "Mean Node"
LILITH = "Lilith"
ASCENDANT = "Ascendant"
MC = "MC"

# Segments available in every JPL DE file (DE440s has no planet-centre
# segments for Mars..Pluto). The offset between a planet's system
# barycenter and its centre is < 0.1" as seen from Earth.
_TARGETS = {
    "Sun": "sun",
    "Moon": "moon",
    "Mercury": "mercury barycenter",
    "Venus": "venus barycenter",
    "Mars": "mars barycenter",
    "Jupiter": "jupiter barycenter",
    "Saturn": "saturn barycenter",
    "Uranus": "uranus barycenter",
    "Neptune": "neptune barycenter",
    "Pluto": "pluto barycenter",
}

_SPEED_STEP_DAYS = 0.01  # central difference step for speeds (14.4 min)
_ARCSEC = 1.0 / 3600.0


@dataclass(frozen=True)
class Point:
    """A chart point: planet, lunar point or angle.

    ``longitude``/``latitude`` are geocentric apparent ecliptic coordinates
    referred to the true equinox and ecliptic of date (tropical zodiac).
    ``speed`` is in degrees per day of longitude.
    """

    name: str
    longitude: float
    latitude: float
    speed: float
    house: int | None = None

    @property
    def sign(self) -> str:
        return sign_of(self.longitude)[0]

    @property
    def degree(self) -> float:
        """Degree within the sign, 0 <= degree < 30."""
        return sign_of(self.longitude)[1]

    @property
    def retrograde(self) -> bool:
        return bool(self.speed < 0)


@dataclass(frozen=True)
class Chart:
    """A computed chart. Index it by point name: ``chart["Moon"]``."""

    datetime_utc: datetime
    latitude: float
    longitude: float
    house_system: str
    """The house system actually used (may differ from the requested one
    if ``polar_fallback`` kicked in, see :attr:`polar_fallback_used`)."""
    polar_fallback_used: bool
    cusps: Cusps
    ramc: float
    obliquity: float
    """True obliquity of the ecliptic, degrees."""
    jd_ut: float
    jd_tt: float
    points: dict[str, Point] = field(repr=False)

    def __getitem__(self, name: str) -> Point:
        return self.points[name]

    def __iter__(self) -> Iterator[Point]:
        return iter(self.points.values())

    @property
    def ascendant(self) -> Point:
        return self.points[ASCENDANT]

    @property
    def mc(self) -> Point:
        return self.points[MC]

    @property
    def planets(self) -> list[Point]:
        return [self.points[n] for n in PLANETS]


def to_utc(when: datetime | str, tz: str | None = None) -> datetime:
    """Normalise input time to an aware UTC datetime.

    * aware ``datetime``: converted to UTC (``tz`` must be omitted);
    * naive ``datetime`` + ``tz``: interpreted as local time in that IANA
      zone (ambiguous/non-existent DST times follow ``datetime.fold``);
    * naive ``datetime`` without ``tz``: rejected, to avoid silent mistakes.
    """
    if isinstance(when, str):
        when = datetime.fromisoformat(when)
    if when.tzinfo is not None:
        if tz is not None:
            raise ValueError("pass either an aware datetime or tz, not both")
        return when.astimezone(timezone.utc)
    if tz is None:
        raise ValueError(
            "naive datetime: pass tz='Area/City' (IANA) or a timezone-aware datetime"
        )
    return when.replace(tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)


_UTC_EPOCH = datetime(1972, 1, 1, tzinfo=timezone.utc)


def _time(dt_utc: datetime):  # -> skyfield Time
    """Skyfield Time for a UTC instant.

    Modern UTC (leap seconds) starts in 1972. Before that, civil time
    followed UT (the "rubber second" UTC of 1961-1971 stayed within 0.1 s of
    UT1), so earlier instants are taken as UT1 and converted with
    Skyfield's Delta T model, as astrology software conventionally does.
    """
    ts = _ephemeris.timescale()
    sec = dt_utc.second + dt_utc.microsecond / 1e6
    args = (dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour, dt_utc.minute, sec)
    return ts.utc(*args) if dt_utc >= _UTC_EPOCH else ts.ut1(*args)


def _bodies(t) -> dict[str, Point]:
    """Apparent geocentric ecliptic positions of the ten planets + lunar points."""
    ts = _ephemeris.timescale()
    eph = _ephemeris.ephemeris()
    earth = eph["earth"]
    h = _SPEED_STEP_DAYS
    tt = ts.tt_jd([t.tt - h, t.tt, t.tt + h])
    out: dict[str, Point] = {}
    for name in PLANETS:
        apparent = earth.at(tt).observe(eph[_TARGETS[name]]).apparent()
        lat, lon, _ = apparent.frame_latlon(ecliptic_frame)
        lons = lon.degrees
        speed = norm180(lons[2] - lons[0]) / (2 * h)
        out[name] = Point(name, float(norm360(lons[1])), float(lat.degrees[1]), float(speed))

    T = (float(t.tt) - 2451545.0) / 36525.0
    dpsi, _ = iau2000a_radians(t)
    dpsi_deg = float(dpsi) * 180.0 / 3.141592653589793
    out[MEAN_NODE] = Point(
        MEAN_NODE, norm360(mean_node(T) + dpsi_deg), 0.0, mean_node_speed(T)
    )
    a_lon, a_lat = mean_apogee(T)
    out[LILITH] = Point(LILITH, norm360(a_lon + dpsi_deg), a_lat, mean_apogee_speed(T))
    return out


def _true_obliquity(t) -> float:
    _, deps = iau2000a_radians(t)
    return mean_obliquity(t.tdb) * _ARCSEC + float(deps) * 180.0 / 3.141592653589793


def chart(
    when: datetime | str,
    lat: float,
    lon: float,
    tz: str | None = None,
    house_system: str = "placidus",
    polar_fallback: str | None = None,
) -> Chart:
    """Compute a tropical natal chart.

    Args:
        when: birth time; an aware datetime, or a naive one together with ``tz``.
        lat: geographic latitude, degrees, north positive.
        lon: geographic longitude, degrees, east positive.
        tz: IANA time zone name for a naive ``when`` (e.g. ``"Europe/Moscow"``).
        house_system: ``"placidus"`` (default), ``"koch"``, ``"porphyry"``,
            ``"equal"`` or ``"whole_sign"``.
        polar_fallback: system to use when Placidus/Koch are undefined
            (``|lat| > 90° - obliquity``, about 66.56°). ``None`` (default)
            raises :class:`~natal_chart.houses.PolarHousesError` instead.
    """
    if not -90.0 <= lat <= 90.0:
        raise ValueError("latitude must be within [-90, 90]")
    if not -180.0 <= lon <= 360.0:
        raise ValueError("longitude must be within [-180, 360]")
    dt_utc = to_utc(when, tz)
    t = _time(dt_utc)

    eps = _true_obliquity(t)
    ramc = norm360(t.gast * 15.0 + lon)
    cusps, used = house_cusps(ramc, eps, lat, house_system, polar_fallback)

    points = _bodies(t)
    points = {n: _with_house(p, cusps) for n, p in points.items()}

    # Speeds of the angles from the rate of sidereal time (deg/day).
    d_ramc = 360.98564736629 * 0.001  # 0.001 day step
    asc = ascendant(ramc, eps, lat)
    mc = midheaven(ramc, eps)
    asc_speed = norm180(ascendant(ramc + d_ramc, eps, lat) - ascendant(ramc - d_ramc, eps, lat)) / 0.002
    mc_speed = norm180(midheaven(ramc + d_ramc, eps) - midheaven(ramc - d_ramc, eps)) / 0.002
    points[ASCENDANT] = Point(ASCENDANT, asc, 0.0, asc_speed, house_of(asc, cusps))
    points[MC] = Point(MC, mc, 0.0, mc_speed, house_of(mc, cusps))

    return Chart(
        datetime_utc=dt_utc,
        latitude=lat,
        longitude=lon,
        house_system=used,
        polar_fallback_used=used != house_system,
        cusps=cusps,
        ramc=ramc,
        obliquity=eps,
        jd_ut=float(t.ut1),
        jd_tt=float(t.tt),
        points=points,
    )


def _with_house(p: Point, cusps: Cusps) -> Point:
    return Point(p.name, p.longitude, p.latitude, p.speed, house_of(p.longitude, cusps))


def positions(when: datetime | str, tz: str | None = None) -> dict[str, Point]:
    """Planet and lunar-point positions only (no location, no houses)."""
    return _bodies(_time(to_utc(when, tz)))
