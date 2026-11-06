"""Fixed readers for stable Vietnamese price pages. See services.py."""
from __future__ import annotations

from .base import Reading
from .services import READERS, UNREADABLE


def run_all():
    """Run every reader; never raises. Returns (readings, errors) — errors are 'reader: message' strings."""
    readings: list[Reading] = []
    errors: list[str] = []
    for fn in READERS:
        try:
            for item in fn():
                if isinstance(item, Reading):
                    readings.append(item)
                else:
                    errors.append(f"{fn.__name__}: {item}")
        except Exception as e:  # noqa: BLE001 — a broken page must not stop the run
            errors.append(f"{fn.__name__}: {type(e).__name__}: {e}")
    return readings, errors


__all__ = ["Reading", "READERS", "UNREADABLE", "run_all"]
