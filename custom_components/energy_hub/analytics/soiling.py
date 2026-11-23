"""Soiling loss from the daily performance index: stochastic rate and recovery (SRR), simplified.

Deceglie, Micheli and Muller, "Quantifying Soiling Loss Directly From PV Yield", IEEE JPV 8(2) p. 547, 2018
(implemented in NREL's RdTools as ``soiling.soiling_srr``):
1. cleaning events split the series into soiling intervals — a jump of the rolling median (``shift``) and/or rain;
2. the slope of each interval is fitted with Theil-Sen, robust to outliers;
3. the loss is the insolation-weighted mean of the soiling profile, with a Monte Carlo spread of the slopes for its
   confidence interval.
The pattern it expects is a sawtooth: a slow decline, then a sharp recovery at a natural or manual cleaning.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, field
from statistics import median

from . import quantile, theil_sen

MIN_DAYS = 90
MIN_INTERVAL = 7
DAY_SCALE = 7


@dataclass(slots=True)
class SoilingInterval:
    start: int
    end: int
    rate_per_day: float


@dataclass(slots=True)
class SoilingResult:
    """Soiling ratio (1 = clean), the loss ``1 - ratio``, its confidence interval and the intervals found."""

    ratio: float
    loss: float
    confidence: tuple[float, float]
    intervals: list[SoilingInterval] = field(default_factory=list)
    days_used: int = 0


def _rolling_median(values: list[float], window: int) -> list[float]:
    half = window // 2
    return [median(values[max(0, i - half) : i + half + 1]) for i in range(len(values))]


def cleaning_events(pi: list[float], rain: list[float] | None = None, rain_threshold: float = 1.0) -> list[int]:
    """Days where the panels were cleaned: a positive step of the rolling median larger than three quartile ranges
    of the day-to-day changes (the "shift" criterion), or a rainy day followed by a rise."""
    smooth = _rolling_median(pi, DAY_SCALE)
    steps = [smooth[i] - smooth[i - 1] for i in range(1, len(smooth))]
    if not steps:
        return []
    iqr = quantile(steps, 0.75) - quantile(steps, 0.25)
    threshold = max(3 * iqr, 0.01)
    events = []
    for i in range(1, len(smooth)):
        jump = smooth[min(i + DAY_SCALE // 2, len(smooth) - 1)] - smooth[max(i - DAY_SCALE // 2 - 1, 0)]
        rained = rain is not None and rain[i] >= rain_threshold
        if (smooth[i] - smooth[i - 1] > threshold or (rained and jump > threshold / 2)) and (
            not events or i - events[-1] >= MIN_INTERVAL
        ):
            events.append(i)
    return events


def soiling_srr(
    pi: list[float],
    insolation: list[float] | None = None,
    rain: list[float] | None = None,
    reps: int = 200,
    seed: int = 0,
) -> SoilingResult | None:
    """Soiling loss of a daily performance index (EPI) series. None under ``MIN_DAYS`` days or without an interval."""
    if len(pi) < MIN_DAYS:
        return None
    weights = insolation or [1.0] * len(pi)
    bounds = [0, *cleaning_events(pi, rain), len(pi)]
    intervals: list[SoilingInterval] = []
    slopes_spread: list[tuple[SoilingInterval, float]] = []
    for a, b in itertools.pairwise(bounds):
        if b - a < MIN_INTERVAL:
            continue
        xs = list(range(a, b))
        ys = pi[a:b]
        slope, _ = theil_sen([float(x) for x in xs], ys)
        slope = min(slope, 0.0)
        residuals = [y - (slope * x) for x, y in zip(xs, ys, strict=True)]
        spread = (quantile(residuals, 0.84) - quantile(residuals, 0.16)) / 2 / max(b - a, 1)
        interval = SoilingInterval(a, b - 1, slope)
        intervals.append(interval)
        slopes_spread.append((interval, spread))
    if not intervals:
        return None

    def profile_loss(slopes: list[float]) -> float:
        lost = total = 0.0
        for (interval, _), slope in zip(slopes_spread, slopes, strict=True):
            for day in range(interval.start, interval.end + 1):
                factor = max(0.0, min(1.0, 1 + slope * (day - interval.start)))
                lost += (1 - factor) * weights[day]
                total += weights[day]
        return lost / total if total else 0.0

    p50 = profile_loss([i.rate_per_day for i in intervals])
    rng = random.Random(seed)
    samples = sorted(
        profile_loss([min(i.rate_per_day + rng.gauss(0, s), 0.0) for i, s in slopes_spread]) for _ in range(reps)
    )
    low, high = min(quantile(samples, 0.16), p50), max(quantile(samples, 0.84), p50)
    return SoilingResult(
        ratio=1 - p50,
        loss=p50,
        confidence=(1 - high, 1 - low),
        intervals=intervals,
        days_used=len(pi),
    )
