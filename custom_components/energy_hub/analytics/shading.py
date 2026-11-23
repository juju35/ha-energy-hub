"""Recurring shading: dips that come back at the same time of day on clear days.

A density-based reading of the residential case (Utrecht University, Progress in Photovoltaics, 2023): on clear days
the actual/expected ratio of each time bin is near 1; a tree, a chimney or a neighbour's roof shows as bins whose
ratio drops on most clear days while the rest of the day stays at its usual level. A one-off cloud does not repeat.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

# A clear day: its whole-day actual/expected ratio is at least this.
CLEAR_DAY = 0.85
# A bin is shaded when its ratio is this far below the day's median ratio...
DIP = 0.2
# ...on at least this share of the clear days.
RECURRENCE = 0.6
MIN_CLEAR_DAYS = 10


@dataclass(frozen=True, slots=True)
class ShadingWindow:
    """A recurring shading period: first and last bin (minutes after midnight), mean loss in the window, kWh/day."""

    start_minute: int
    end_minute: int
    depth: float
    kwh_per_day: float


def recurring_shading(
    days: list[dict[int, tuple[float, float]]], bin_minutes: int = 15, clear_day: float = CLEAR_DAY
) -> list[ShadingWindow] | None:
    """Shading windows from days of ``{minute: (actual kWh, expected kWh)}`` bins. None under ``MIN_CLEAR_DAYS``.

    ``clear_day`` picks the clear days by their whole-day ratio; 0 when the caller already kept only clear days
    (a panel compared with its peers has a ratio of its own that says nothing about the sky)."""
    clear = []
    for day in days:
        actual = sum(a for a, _ in day.values())
        expected = sum(e for _, e in day.values())
        if expected > 0 and actual / expected >= clear_day:
            clear.append(day)
    if len(clear) < MIN_CLEAR_DAYS:
        return None
    shaded: dict[int, list[float]] = {}
    lost: dict[int, list[float]] = {}
    for day in clear:
        ratios = {m: a / e for m, (a, e) in day.items() if e > 0.02}
        if not ratios:
            continue
        typical = median(ratios.values())
        for minute, r in ratios.items():
            hit = r < typical - DIP
            shaded.setdefault(minute, []).append(1.0 if hit else 0.0)
            if hit:
                a, e = day[minute]
                lost.setdefault(minute, []).append(max(e * typical - a, 0.0))
    flagged = sorted(m for m, hits in shaded.items() if sum(hits) / len(hits) >= RECURRENCE)
    windows: list[ShadingWindow] = []
    run: list[int] = []
    for minute in [*flagged, None]:
        if minute is not None and (not run or minute - run[-1] == bin_minutes):
            run.append(minute)
            continue
        if run:
            losses = [sum(lost.get(m, [0.0])) / len(clear) for m in run]
            depths = [1 - sum(shaded[m]) / len(shaded[m]) * DIP for m in run]
            windows.append(ShadingWindow(run[0], run[-1] + bin_minutes, 1 - min(depths), sum(losses)))
        run = [minute] if minute is not None else []
    return windows
