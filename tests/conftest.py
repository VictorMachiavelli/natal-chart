"""Shared fixtures. All birth data in this test suite is fictional."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def ephemeris():
    """Load (and on first run download) the JPL ephemeris, or skip."""
    from natal_chart import _ephemeris

    try:
        return _ephemeris.ephemeris()
    except Exception as exc:  # pragma: no cover - offline environments
        pytest.skip(f"JPL ephemeris unavailable: {exc}")
