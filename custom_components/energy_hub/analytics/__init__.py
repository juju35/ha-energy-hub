"""Pure-Python analytics of Energy Hub: no Home Assistant import, no third-party dependency.

Each module follows a published method, simplified for a residential installation with no irradiance sensor:
- ``clearsky``: solar position and clear-sky irradiance (expected production when no forecast is configured)
- ``kpis``: self-consumption, self-sufficiency, specific yield, energy performance index (IEC 61724-1:2021)
- ``clipping``: inverter clipping and export limitation (PVAnalytics geometric / threshold methods)
- ``soiling``: stochastic rate and recovery (Deceglie et al., IEEE JPV 2018, RdTools)
- ``degradation``: year-on-year degradation rate (Jordan et al., 2017, RdTools)
- ``shading``: recurring dips at the same sun position on clear days
- ``mismatch``: strings or micro-inverters compared with their peers
- ``battery``, ``cells``: battery fleet, health, cycles, round-trip efficiency, cell spread
- ``finance``: savings and payback

Every estimate that needs history returns ``None`` below its minimum data: the panel then shows "learning".
"""

from __future__ import annotations

from statistics import median


def theil_sen(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Slope and intercept of the Theil-Sen estimator: the median of the pairwise slopes, robust to outliers."""
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("theil_sen needs two points or more")
    slopes = [
        (ys[j] - ys[i]) / (xs[j] - xs[i]) for i in range(len(xs)) for j in range(i + 1, len(xs)) if xs[j] != xs[i]
    ]
    if not slopes:
        raise ValueError("theil_sen needs two distinct x values")
    slope = median(slopes)
    intercept = median(y - slope * x for x, y in zip(xs, ys, strict=True))
    return slope, intercept


def quantile(values: list[float], q: float) -> float:
    """Quantile with linear interpolation (numpy's default), for 0 <= q <= 1."""
    if not values:
        raise ValueError("quantile of an empty list")
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)
