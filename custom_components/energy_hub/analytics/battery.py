"""Battery fleet, health and efficiency.

The fleet's state of charge is weighted by capacity (stored kWh over total kWh), not the mean of the percentages.
Cycles are the discharged energy over the nominal capacity; the round-trip efficiency is discharged over charged
energy across whole days; the state of health, when the battery does not report it, is the capacity measured on a
charge spanning a large part of the range over the nominal capacity.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BatteryState:
    """One battery now: capacity (kWh), SoC (%), power (kW, positive = charging), reserve (%)."""

    name: str
    capacity_kwh: float
    soc: float
    power_kw: float = 0.0
    reserve: float = 10.0


@dataclass(frozen=True, slots=True)
class Fleet:
    soc: float | None
    stored_kwh: float
    capacity_kwh: float
    power_kw: float
    charging: int
    discharging: int
    exchange_kw: float


def fleet(batteries: list[BatteryState], idle_kw: float = 0.05) -> Fleet:
    """The fleet of batteries: weighted SoC, net power, and the power one battery sends into another (both at once
    charging and discharging: a loss of round-trip efficiency, reported as such)."""
    capacity = sum(b.capacity_kwh for b in batteries)
    stored = sum(b.capacity_kwh * b.soc / 100 for b in batteries)
    charging = sum(b.power_kw for b in batteries if b.power_kw > idle_kw)
    discharging = -sum(b.power_kw for b in batteries if b.power_kw < -idle_kw)
    return Fleet(
        soc=stored / capacity * 100 if capacity > 0 else None,
        stored_kwh=stored,
        capacity_kwh=capacity,
        power_kw=charging - discharging,
        charging=sum(1 for b in batteries if b.power_kw > idle_kw),
        discharging=sum(1 for b in batteries if b.power_kw < -idle_kw),
        exchange_kw=min(charging, discharging),
    )


def autonomy_hours(batteries: list[BatteryState], load_kw: float) -> float | None:
    """Hours the batteries can carry the home at ``load_kw``, each down to its reserve."""
    if load_kw <= 0.01:
        return None
    usable = sum(max(b.soc - b.reserve, 0) / 100 * b.capacity_kwh for b in batteries)
    return usable / load_kw


def hours_to_full(battery: BatteryState) -> float | None:
    """Hours until the battery is full at its current charging power."""
    if battery.power_kw <= 0.01:
        return None
    return (100 - battery.soc) / 100 * battery.capacity_kwh / battery.power_kw


def cycles(discharged_kwh: float, capacity_kwh: float) -> float | None:
    """Equivalent full cycles."""
    if capacity_kwh <= 0:
        return None
    return discharged_kwh / capacity_kwh


def round_trip_efficiency(charged_kwh: float, discharged_kwh: float) -> float | None:
    """Discharged over charged energy, over a period long enough for the SoC to come back (whole days)."""
    if charged_kwh < 0.5:
        return None
    return min(discharged_kwh / charged_kwh, 1.0)


def soh_from_charge(soc_start: float, soc_end: float, charged_kwh: float, capacity_kwh: float) -> float | None:
    """State of health (%) from one charge: energy taken over the SoC gained, against the nominal capacity. Only a
    charge over at least 40 points of SoC is trusted (the SoC estimate drifts on short ones)."""
    gained = soc_end - soc_start
    if gained < 40 or capacity_kwh <= 0:
        return None
    measured = charged_kwh * 0.97 / (gained / 100)
    return max(0.0, min(100.0, measured / capacity_kwh * 100))
