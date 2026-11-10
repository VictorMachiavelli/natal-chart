"""Small angle helpers (degrees)."""

from __future__ import annotations

import math

SIGNS: tuple[str, ...] = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)


def norm360(x: float) -> float:
    """Normalise an angle to [0, 360)."""
    x = math.fmod(x, 360.0)
    if x < 0:
        x += 360.0
    # fmod can return 360.0 for tiny negative inputs after the addition
    return 0.0 if x >= 360.0 else x


def norm180(x: float) -> float:
    """Normalise an angle to [-180, 180)."""
    return norm360(x + 180.0) - 180.0


def sind(x: float) -> float:
    return math.sin(math.radians(x))


def cosd(x: float) -> float:
    return math.cos(math.radians(x))


def tand(x: float) -> float:
    return math.tan(math.radians(x))


def asind(x: float) -> float:
    return math.degrees(math.asin(max(-1.0, min(1.0, x))))


def atan2d(y: float, x: float) -> float:
    return math.degrees(math.atan2(y, x))


def sign_of(longitude: float) -> tuple[str, float]:
    """Return (sign name, degree within sign) for an ecliptic longitude."""
    lon = norm360(longitude)
    idx = int(lon // 30.0)
    return SIGNS[idx], lon - 30.0 * idx


def format_dms(degree_in_sign: float) -> str:
    """Format a degree within a sign as ``DD°MM'SS"``."""
    total = int(round(degree_in_sign * 3600.0))
    d, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{d:2d}°{m:02d}'{s:02d}\""
