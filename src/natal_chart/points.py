"""Mean lunar node and mean Black Moon Lilith (mean lunar apogee).

Both come from the ELP-2000/82 mean-element polynomials as given by
J. Meeus, *Astronomical Algorithms* (2nd ed.), ch. 47:

* mean ascending node  Ω = 125.0445479 − 1934.1362891 T + 0.0020754 T²
  + T³/467441 − T⁴/60616000
* mean perigee         ϖ = 83.3532465 + 4069.0137287 T − 0.0103200 T²
  − T³/80053 + T⁴/18999000

with T in Julian centuries of TT from J2000.0. The values refer to the mean
equinox of date; we add the nutation in longitude so they are on the same
true-equinox-of-date frame as the planets.

The mean apogee (ϖ + 180°) lies on the inclined lunar orbit. Its ecliptic
longitude is obtained by projecting it from the orbit plane (inclination
5.1453964°) onto the ecliptic, which is what most astrology software does.
"""

from __future__ import annotations

import math

from ._angles import atan2d, cosd, norm360, sind

LUNAR_INCLINATION = 5.1453964  # degrees, mean inclination of the lunar orbit


def mean_node(T: float) -> float:
    """Mean ascending lunar node, mean equinox of date (degrees)."""
    return norm360(
        125.0445479
        - 1934.1362891 * T
        + 0.0020754 * T**2
        + T**3 / 467441.0
        - T**4 / 60616000.0
    )


def mean_node_speed(T: float) -> float:
    """Speed of the mean node in degrees per day."""
    dT = -1934.1362891 + 2 * 0.0020754 * T + 3 * T**2 / 467441.0 - 4 * T**3 / 60616000.0
    return dT / 36525.0


def mean_perigee(T: float) -> float:
    """Mean longitude of the lunar perigee (Ω + ω, along ecliptic then orbit)."""
    return norm360(
        83.3532465
        + 4069.0137287 * T
        - 0.0103200 * T**2
        - T**3 / 80053.0
        + T**4 / 18999000.0
    )


def mean_apogee(T: float) -> tuple[float, float]:
    """Mean lunar apogee (Black Moon Lilith): (ecliptic longitude, latitude).

    Mean equinox of date, degrees.
    """
    node = mean_node(T)
    # argument of the apogee measured in the orbit plane from the node
    u = norm360(mean_perigee(T) + 180.0 - node)
    i = LUNAR_INCLINATION
    lon = norm360(node + atan2d(sind(u) * cosd(i), cosd(u)))
    lat = math.degrees(math.asin(sind(u) * sind(i)))
    return lon, lat


def mean_apogee_speed(T: float, h: float = 0.5) -> float:
    """Speed of the mean apogee in degrees per day (central difference)."""
    dT = h / 36525.0
    a = mean_apogee(T - dT)[0]
    b = mean_apogee(T + dT)[0]
    return ((b - a + 540.0) % 360.0 - 180.0) / (2 * h)
