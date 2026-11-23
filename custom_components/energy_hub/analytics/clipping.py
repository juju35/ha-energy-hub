"""Inverter clipping and export limitation, from the shape of the AC power curve.

Geometric method (PVAnalytics ``features.clipping.geometric``): each day, the periods where the slope of the power is
small near the day's maximum are a plateau; their power gives the clipping level. A plateau only counts as clipping
when the expected production (clear-sky or forecast) is above it, which tells a clipped peak from a cloudy noon.
The threshold method (``features.clipping.threshold``) confirms the level over several days: the high quantile of the
power at each time of day flattens at the inverter's limit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median

from . import quantile

# Relative change between two 5-minute samples under which the curve is flat (share of the day's maximum).
SLOPE_MAX = 0.01
# A plateau is this close to the day's maximum.
NEAR_MAX = 0.95
# Shortest plateau counted, in samples (15 minutes at 5-minute sampling).
MIN_RUN = 3
# The expected production must exceed the plateau by this share for it to be clipping, not a flat cloudy sky.
EXPECTED_MARGIN = 0.03
# With a known limit, a clipping plateau sits at it: within 3 %.
LIMIT_SHARE = 0.97


@dataclass(slots=True)
class ClippingResult:
    """Clipped periods of a day: level (kW), lost energy (kWh) and the (start, end) timestamps of each plateau."""

    level: float | None = None
    lost_kwh: float = 0.0
    periods: list[tuple[float, float]] = field(default_factory=list)


def detect_plateaus(samples: list[tuple[float, float]]) -> list[tuple[int, int]]:
    """Index ranges ``[start, end]`` of the flat runs near the maximum of a day's ``(timestamp, kW)`` samples."""
    if len(samples) < MIN_RUN:
        return []
    peak = max(p for _, p in samples)
    if peak <= 0:
        return []
    runs: list[tuple[int, int]] = []
    start = None
    for i, (_, p) in enumerate(samples):
        flat = p >= NEAR_MAX * peak and (i == 0 or abs(p - samples[i - 1][1]) <= SLOPE_MAX * peak)
        if flat and start is None:
            start = i
        elif not flat and start is not None:
            if i - start >= MIN_RUN:
                runs.append((start, i - 1))
            start = None
    if start is not None and len(samples) - start >= MIN_RUN:
        runs.append((start, len(samples) - 1))
    return runs


def clipping_day(
    samples: list[tuple[float, float]], expected: list[float] | None = None, limit_kw: float | None = None
) -> ClippingResult:
    """Clipping of one day. ``expected`` (kW, aligned with ``samples``) gives the lost energy; ``limit_kw`` (the
    inverter's maximum, or the export limit) is used as the level when known, else the plateaus' median."""
    result = ClippingResult()
    runs = detect_plateaus(samples)
    if not runs:
        return result
    plateau_values = [samples[i][1] for a, b in runs for i in range(a, b + 1)]
    level = limit_kw or median(plateau_values)
    if limit_kw and median(plateau_values) < LIMIT_SHARE * limit_kw:
        # Flat, but below the inverter's limit: the round top of a sunny day or a uniform sky, not clipping.
        return result
    kept: list[tuple[int, int]] = []
    for a, b in runs:
        if expected is not None:
            above = [expected[i] for i in range(a, b + 1) if expected[i] > level * (1 + EXPECTED_MARGIN)]
            if len(above) < (b - a + 1) / 2:
                continue
        kept.append((a, b))
    if not kept:
        return result
    result.level = level
    for a, b in kept:
        result.periods.append((samples[a][0], samples[b][0]))
        if expected is None:
            continue
        for i in range(a, b + 1):
            dt = (samples[i + 1][0] - samples[i][0]) if i + 1 < len(samples) else (samples[i][0] - samples[i - 1][0])
            result.lost_kwh += max(expected[i] - samples[i][1], 0.0) * dt / 3600
    return result


def clipping_threshold(days: list[list[tuple[float, float]]], power_quantile: float = 0.995) -> float | None:
    """Clipping level confirmed over several days: the high quantile of each day's maximum, when at least half of the
    days reach it within 2 % (a flattened top of the daily power curve). None when no common ceiling shows."""
    peaks = [max(p for _, p in day) for day in days if day]
    if len(peaks) < 5:
        return None
    ceiling = quantile(peaks, power_quantile)
    if ceiling <= 0:
        return None
    reaching = sum(1 for p in peaks if p >= 0.98 * ceiling)
    return ceiling if reaching >= len(peaks) / 2 else None
