"""Loading of the JPL ephemeris through Skyfield.

The ephemeris file is never shipped with the package. On first use Skyfield
downloads it into a cache directory:

* ``$NATAL_CHART_DATA`` if set, otherwise
* ``~/.cache/natal-chart``.

The default file is NASA JPL DE440s (1849-2150, ~32 MB). Any other
Skyfield-readable SPK file (for example ``de421.bsp``, 1900-2050, ~17 MB, or
``de440.bsp``, 1550-2650, ~114 MB) can be selected with
:func:`set_ephemeris` or the ``NATAL_CHART_EPHEMERIS`` environment variable.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from skyfield.api import Loader

DEFAULT_EPHEMERIS = "de440s.bsp"

_ephemeris_name: str = os.environ.get("NATAL_CHART_EPHEMERIS", DEFAULT_EPHEMERIS)


def data_dir() -> Path:
    """Directory where the ephemeris file is cached."""
    env = os.environ.get("NATAL_CHART_DATA")
    return Path(env).expanduser() if env else Path.home() / ".cache" / "natal-chart"


@lru_cache(maxsize=1)
def _loader() -> Loader:
    path = data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return Loader(str(path), verbose=False)


@lru_cache(maxsize=1)
def timescale() -> Any:
    """Skyfield timescale (uses Skyfield's built-in Delta T / leap-second data)."""
    return _loader().timescale()


@lru_cache(maxsize=4)
def _load(name: str) -> Any:
    return _loader()(name)


def ephemeris() -> Any:
    """The currently selected JPL ephemeris, downloading it on first use."""
    return _load(_ephemeris_name)


def set_ephemeris(name_or_path: str) -> None:
    """Select the SPK file to use, e.g. ``"de421.bsp"`` or a local path."""
    global _ephemeris_name
    _ephemeris_name = name_or_path
