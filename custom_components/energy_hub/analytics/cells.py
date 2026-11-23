"""Cell voltages of a battery pack: spread, weakest cell, drift over time and the days left to the alert threshold."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from . import theil_sen

DEFAULT_THRESHOLD_MV = 50.0


@dataclass(frozen=True, slots=True)
class CellSummary:
    """Spread (mV), the lowest and highest cell (index from 0, volts) and each cell's deviation from the mean (mV)."""

    spread_mv: float
    min_index: int
    min_v: float
    max_index: int
    max_v: float
    deviations_mv: list[float]


def summarize(voltages: list[float]) -> CellSummary | None:
    if len(voltages) < 2:
        return None
    avg = mean(voltages)
    lo = min(range(len(voltages)), key=voltages.__getitem__)
    hi = max(range(len(voltages)), key=voltages.__getitem__)
    return CellSummary(
        spread_mv=(voltages[hi] - voltages[lo]) * 1000,
        min_index=lo,
        min_v=voltages[lo],
        max_index=hi,
        max_v=voltages[hi],
        deviations_mv=[(v - avg) * 1000 for v in voltages],
    )


def days_to_threshold(daily_spread_mv: list[float], threshold_mv: float = DEFAULT_THRESHOLD_MV) -> float | None:
    """Days until the spread reaches the threshold at its current trend (Theil-Sen over the daily maxima); None when
    the spread is stable or shrinking, or with under 7 days of data. 0 when already over."""
    if len(daily_spread_mv) < 7:
        return None
    if daily_spread_mv[-1] >= threshold_mv:
        return 0.0
    slope, intercept = theil_sen([float(i) for i in range(len(daily_spread_mv))], daily_spread_mv)
    if slope <= 0.05:
        return None
    today = intercept + slope * (len(daily_spread_mv) - 1)
    return max((threshold_mv - today) / slope, 0.0)
