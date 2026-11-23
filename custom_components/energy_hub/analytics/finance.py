"""Savings and payback of the installation.

Self-consumed energy is valued at the import price it avoided (the price of that hour and Tempo colour when known);
exported energy at the feed-in price. The payback projection grows the yearly gain with the electricity price, takes
off the panels' degradation and an inverter replacement, and finds the date the cumulated gain covers the net cost.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Savings:
    self_consumed_eur: float
    export_eur: float

    @property
    def total(self) -> float:
        return self.self_consumed_eur + self.export_eur


def savings(self_consumed_kwh: float, export_kwh: float, import_price: float, export_price: float) -> Savings:
    return Savings(self_consumed_kwh * import_price, export_kwh * export_price)


@dataclass(frozen=True, slots=True)
class Payback:
    """Years from now to the break-even (None if not within the horizon) and the net gain at the horizon (EUR)."""

    years_to_break_even: float | None
    net_gain_at_horizon: float
    share_paid: float


def payback(
    net_cost: float,
    gained_so_far: float,
    yearly_gain: float,
    price_growth: float = 0.03,
    degradation: float = 0.005,
    age_years: float = 0.0,
    inverter_cost: float = 0.0,
    inverter_at_year: float = 12.0,
    horizon_years: float = 20.0,
) -> Payback:
    """Monthly projection of the cumulated gain from today to ``horizon_years`` after commissioning."""
    total = gained_so_far
    break_even = 0.0 if total >= net_cost > 0 else None
    months = max(round((horizon_years - age_years) * 12), 0)
    inverter_paid = age_years >= inverter_at_year
    for m in range(1, months + 1):
        years = m / 12
        total += yearly_gain / 12 * (1 + price_growth) ** years * (1 - degradation * (age_years + years))
        if not inverter_paid and age_years + years >= inverter_at_year:
            total -= inverter_cost
            inverter_paid = True
        if break_even is None and total >= net_cost:
            break_even = years
    share = min(gained_so_far / net_cost, 1.0) if net_cost > 0 else 1.0
    return Payback(break_even, total - net_cost, share)
