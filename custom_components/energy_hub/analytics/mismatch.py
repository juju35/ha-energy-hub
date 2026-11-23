"""Strings, MPPT inputs or micro-inverters compared with their peers, with no weather sensor.

After Guerriero et al., "Mismatch Based Diagnosis of PV Fields Relying on Monitored String Currents" (Int. J.
Photoenergy, 2017): units that see the same sky should produce the same energy per kWp; the median of the peers is
the reference, so weather and irradiance cancel out.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

# A unit under this share of its peers' median is lagging...
LAGGING = 0.9
# ...for at least this many consecutive days to be reported.
MIN_DAYS = 3


@dataclass(frozen=True, slots=True)
class UnitScore:
    """A unit's energy per kWp relative to the median of the other units (1 = typical), and its days lagging."""

    name: str
    relative: float
    lagging_days: int

    @property
    def lagging(self) -> bool:
        return self.lagging_days >= MIN_DAYS


def relative_yields(day: dict[str, tuple[float, float]]) -> dict[str, float]:
    """Each unit's specific yield over the median of the *other* units, from ``{name: (kWh, kWp)}`` of one day.
    Leaving the unit out keeps a lagging unit from pulling its own reference down (with two strings, the median of
    both would halve the gap)."""
    yields = {n: e / k for n, (e, k) in day.items() if k > 0}
    if len(yields) < 2:
        return {}
    out = {}
    for name, value in yields.items():
        ref = median(v for n, v in yields.items() if n != name)
        if ref > 0:
            out[name] = value / ref
    return out


def score_units(days: list[dict[str, tuple[float, float]]]) -> list[UnitScore]:
    """Scores of the units over consecutive days (oldest first): today's relative yield and the lagging streak."""
    streak: dict[str, int] = {}
    latest: dict[str, float] = {}
    for day in days:
        rel = relative_yields(day)
        for name, value in rel.items():
            streak[name] = streak.get(name, 0) + 1 if value < LAGGING else 0
            latest[name] = value
    return [UnitScore(n, latest[n], streak.get(n, 0)) for n in sorted(latest)]
