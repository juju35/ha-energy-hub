"""Energy balance indicators, computed from energies (kWh) over a period, never from instantaneous powers.

Definitions follow IEC 61724-1:2021: the energy performance index (EPI) is the measured specific yield over the
expected (modelled) one; the performance ratio (PR) needs plane-of-array irradiance, which a home installation rarely
measures, so the EPI against the clear-sky or forecast model stands in for it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Balance:
    """Energies of a period, kWh. ``battery_in``/``battery_out`` are the battery fleet's charge and discharge."""

    pv: float = 0.0
    grid_import: float = 0.0
    grid_export: float = 0.0
    battery_in: float = 0.0
    battery_out: float = 0.0

    @property
    def load(self) -> float:
        """Home consumption: everything that came in minus what left to the grid and into the batteries."""
        return max(self.pv + self.grid_import + self.battery_out - self.grid_export - self.battery_in, 0.0)

    @property
    def self_consumed(self) -> float:
        """Production used on site (home and batteries), kWh."""
        return max(self.pv - self.grid_export, 0.0)


def ratio(part: float, whole: float) -> float | None:
    """``part / whole`` clamped to [0, 1], or None when there is nothing to divide."""
    if whole <= 1e-9:
        return None
    return max(0.0, min(1.0, part / whole))


def self_consumption(balance: Balance) -> float | None:
    """Share of the production used on site (home + batteries)."""
    return ratio(balance.self_consumed, balance.pv)


def self_sufficiency(balance: Balance) -> float | None:
    """Share of the home consumption covered by the panels or the batteries."""
    load = balance.load
    return ratio(load - balance.grid_import, load)


def specific_yield(pv_kwh: float, kwp: float) -> float | None:
    """kWh produced per kWp installed."""
    if kwp <= 0:
        return None
    return pv_kwh / kwp


def energy_performance_index(actual_kwh: float, expected_kwh: float) -> float | None:
    """Measured over expected production (IEC 61724-1 EPI); not clamped, a value above 1 is possible."""
    if expected_kwh <= 1e-6:
        return None
    return actual_kwh / expected_kwh
