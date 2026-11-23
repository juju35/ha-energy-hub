"""Degradation rate of the array, year-on-year (Jordan et al., "Robust PV Degradation Methodology and Application",
IEEE JPV 2018; RdTools ``degradation.degradation_year_on_year``).

Each daily performance index is compared with the one 365 days later: comparing the same time of year cancels most
seasonal effects (soiling, shading, temperature). The rate is the median of those slopes; its confidence interval
comes from a bootstrap of them.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import median

from . import quantile

MIN_DAYS = 730


@dataclass(frozen=True, slots=True)
class DegradationResult:
    rate_pct_per_year: float
    confidence: tuple[float, float]
    pairs: int


def degradation_yoy(pi: dict[int, float], reps: int = 300, seed: int = 0) -> DegradationResult | None:
    """Rate (%/year, negative = losing) from a daily performance index keyed by day number. None under two years."""
    if not pi or max(pi) - min(pi) + 1 < MIN_DAYS:
        return None
    baseline = median(pi.values())
    slopes = [(pi[d + 365] - v) / baseline * 100 for d, v in pi.items() if d + 365 in pi and baseline > 0]
    if len(slopes) < 180:
        return None
    rate = median(slopes)
    rng = random.Random(seed)
    boot = sorted(median(rng.choices(slopes, k=len(slopes))) for _ in range(reps))
    return DegradationResult(rate, (quantile(boot, 0.16), quantile(boot, 0.84)), len(slopes))
