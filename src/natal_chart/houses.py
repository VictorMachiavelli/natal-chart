"""House systems, Ascendant and Midheaven.

All functions here are pure math and take:

* ``ramc`` - right ascension of the meridian (local apparent sidereal time
  in degrees),
* ``eps`` - true obliquity of the ecliptic, degrees,
* ``lat`` - geographic latitude, degrees (north positive).

Cusps are returned as a 12-tuple of ecliptic longitudes, index 0 = cusp 1.

Placidus and Koch are undefined when part of the ecliptic never rises or
sets, i.e. for ``|lat| > 90° - eps`` (about 66.56°). In that case
:class:`PolarHousesError` is raised; :func:`house_cusps` can instead fall
back to another system when asked to.
"""

from __future__ import annotations

from typing import Literal

from ._angles import asind, atan2d, cosd, norm180, norm360, sind, tand

HouseSystem = Literal["placidus", "koch", "porphyry", "equal", "whole_sign"]
HOUSE_SYSTEMS: tuple[str, ...] = ("placidus", "koch", "porphyry", "equal", "whole_sign")
_QUADRANT_SYSTEMS = ("placidus", "koch")

Cusps = tuple[float, float, float, float, float, float, float, float, float, float, float, float]


class PolarHousesError(ValueError):
    """Placidus/Koch cusps do not exist at this latitude."""


def midheaven(ramc: float, eps: float) -> float:
    """Ecliptic longitude of the MC."""
    return norm360(atan2d(sind(ramc), cosd(ramc) * cosd(eps)))


def ascendant(ramc: float, eps: float, lat: float) -> float:
    """Ecliptic longitude of the ecliptic point rising in the east."""
    return norm360(
        atan2d(cosd(ramc), -(sind(ramc) * cosd(eps) + tand(lat) * sind(eps)))
    )


def _lon_from_ra(ra: float, eps: float) -> float:
    """Ecliptic longitude of the ecliptic point with right ascension ``ra``."""
    return norm360(atan2d(sind(ra), cosd(ra) * cosd(eps)))


def _check_polar(lat: float, eps: float, system: str) -> None:
    if abs(lat) >= 90.0 - eps:
        raise PolarHousesError(
            f"{system.capitalize()} houses are undefined at latitude {lat:.4f}° "
            f"(|latitude| >= 90° - obliquity = {90.0 - eps:.4f}°): part of the "
            "ecliptic never rises or sets. Use house_system='porphyry', 'equal' or "
            "'whole_sign', or pass polar_fallback=..."
        )


def placidus(ramc: float, eps: float, lat: float) -> Cusps:
    """Placidus cusps by iterating on the diurnal semi-arc of each cusp.

    Cusp 11/12 is the ecliptic point whose right ascension exceeds RAMC by
    1/3 resp. 2/3 of its own diurnal semi-arc; cusps 2/3 likewise trisect
    the nocturnal semi-arc between the Ascendant and the IC.
    """
    _check_polar(lat, eps, "placidus")
    tan_lat = tand(lat)

    def cusp(offset: float, factor: float) -> float:
        # RA(cusp) = RAMC + offset + factor * DSA(dec(cusp)), DSA = 90 + AD
        lon = _lon_from_ra(ramc + offset + factor * 90.0, eps)  # start: equator
        for _ in range(100):
            dec = asind(sind(eps) * sind(lon))
            ad = asind(tan_lat * tand(dec))
            new = _lon_from_ra(ramc + offset + factor * (90.0 + ad), eps)
            if abs(norm180(new - lon)) < 1e-10:
                return new
            lon = new
        return lon

    mc = midheaven(ramc, eps)
    asc = ascendant(ramc, eps, lat)
    c11 = cusp(0.0, 1.0 / 3.0)
    c12 = cusp(0.0, 2.0 / 3.0)
    # RA(c2) = RAMC + 180 - 2/3 NSA = RAMC + 60 + 2/3 DSA ; RA(c3) = RAMC + 120 + 1/3 DSA
    c2 = cusp(60.0, 2.0 / 3.0)
    c3 = cusp(120.0, 1.0 / 3.0)
    return _from_quadrant(asc, c2, c3, mc, c11, c12)


def koch(ramc: float, eps: float, lat: float) -> Cusps:
    """Koch (birthplace) cusps.

    Intermediate cusps are Ascendants computed for sidereal times that
    trisect the diurnal semi-arc of the MC degree.
    """
    _check_polar(lat, eps, "koch")
    mc = midheaven(ramc, eps)
    dec_mc = asind(sind(eps) * sind(mc))
    ad = asind(tand(lat) * tand(dec_mc))
    dsa = 90.0 + ad
    asc = ascendant(ramc, eps, lat)
    c11 = ascendant(ramc - 2.0 * dsa / 3.0, eps, lat)
    c12 = ascendant(ramc - dsa / 3.0, eps, lat)
    c2 = ascendant(ramc + dsa / 3.0, eps, lat)
    c3 = ascendant(ramc + 2.0 * dsa / 3.0, eps, lat)
    return _from_quadrant(asc, c2, c3, mc, c11, c12)


def porphyry(ramc: float, eps: float, lat: float) -> Cusps:
    """Porphyry: each quadrant between the angles is trisected in longitude."""
    mc = midheaven(ramc, eps)
    asc = ascendant(ramc, eps, lat)
    q1 = norm360(asc - mc)  # MC -> ASC (houses 10-12)
    q2 = 180.0 - q1  # ASC -> IC (houses 1-3)
    c11 = norm360(mc + q1 / 3.0)
    c12 = norm360(mc + 2.0 * q1 / 3.0)
    c2 = norm360(asc + q2 / 3.0)
    c3 = norm360(asc + 2.0 * q2 / 3.0)
    return _from_quadrant(asc, c2, c3, mc, c11, c12)


def equal(ramc: float, eps: float, lat: float) -> Cusps:
    """Equal houses: 30° steps from the Ascendant."""
    asc = ascendant(ramc, eps, lat)
    return tuple(norm360(asc + 30.0 * i) for i in range(12))  # type: ignore[return-value]


def whole_sign(ramc: float, eps: float, lat: float) -> Cusps:
    """Whole-sign houses: house 1 is the whole sign containing the Ascendant."""
    asc = ascendant(ramc, eps, lat)
    start = 30.0 * int(asc // 30.0)
    return tuple(norm360(start + 30.0 * i) for i in range(12))  # type: ignore[return-value]


def _from_quadrant(
    asc: float, c2: float, c3: float, mc: float, c11: float, c12: float
) -> Cusps:
    ic, dsc = norm360(mc + 180.0), norm360(asc + 180.0)
    return (
        asc,
        c2,
        c3,
        ic,
        norm360(c11 + 180.0),
        norm360(c12 + 180.0),
        dsc,
        norm360(c2 + 180.0),
        norm360(c3 + 180.0),
        mc,
        c11,
        c12,
    )


_SYSTEMS = {
    "placidus": placidus,
    "koch": koch,
    "porphyry": porphyry,
    "equal": equal,
    "whole_sign": whole_sign,
}


def house_cusps(
    ramc: float,
    eps: float,
    lat: float,
    system: str = "placidus",
    polar_fallback: str | None = None,
) -> tuple[Cusps, str]:
    """Compute cusps and return ``(cusps, system_actually_used)``.

    If ``system`` is Placidus or Koch and the latitude is beyond the polar
    circle, :class:`PolarHousesError` is raised unless ``polar_fallback``
    names another system, which is then used instead.
    """
    if system not in _SYSTEMS:
        raise ValueError(f"unknown house system {system!r}; choose from {HOUSE_SYSTEMS}")
    try:
        return _SYSTEMS[system](ramc, eps, lat), system
    except PolarHousesError:
        if polar_fallback is None:
            raise
        if polar_fallback not in _SYSTEMS or polar_fallback in _QUADRANT_SYSTEMS:
            raise ValueError(
                "polar_fallback must be one of 'porphyry', 'equal', 'whole_sign'"
            ) from None
        return _SYSTEMS[polar_fallback](ramc, eps, lat), polar_fallback


def house_of(longitude: float, cusps: Cusps) -> int:
    """House number (1-12) containing an ecliptic longitude."""
    lon = norm360(longitude)
    for i in range(12):
        start, end = cusps[i], cusps[(i + 1) % 12]
        if norm360(lon - start) < norm360(end - start):
            return i + 1
    return 12  # pragma: no cover - only reachable with degenerate cusps
