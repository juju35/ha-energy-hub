"""The analytics core against synthetic series whose answer is known."""

import math
from datetime import datetime, timedelta, timezone

import pytest

from custom_components.energy_hub.analytics import quantile, theil_sen
from custom_components.energy_hub.analytics.battery import (
    BatteryState,
    autonomy_hours,
    cycles,
    fleet,
    hours_to_full,
    round_trip_efficiency,
    soh_from_charge,
)
from custom_components.energy_hub.analytics.cells import days_to_threshold, summarize
from custom_components.energy_hub.analytics.clearsky import Plane, clearsky_power, solar_position
from custom_components.energy_hub.analytics.clipping import clipping_day, clipping_threshold
from custom_components.energy_hub.analytics.degradation import degradation_yoy
from custom_components.energy_hub.analytics.finance import payback, savings
from custom_components.energy_hub.analytics.kpis import (
    Balance,
    energy_performance_index,
    self_consumption,
    self_sufficiency,
    specific_yield,
)
from custom_components.energy_hub.analytics.mismatch import score_units
from custom_components.energy_hub.analytics.shading import recurring_shading
from custom_components.energy_hub.analytics.soiling import soiling_srr

PARIS = timezone(timedelta(hours=1))


def test_theil_sen_ignores_an_outlier():
    xs = [0.0, 1, 2, 3, 4, 5]
    ys = [0.0, 1, 2, 30, 4, 5]
    slope, intercept = theil_sen(xs, ys)
    assert slope == pytest.approx(1.0)
    assert intercept == pytest.approx(0.0)


def test_quantile_matches_linear_interpolation():
    assert quantile([1, 2, 3, 4], 0.5) == 2.5
    assert quantile([5], 0.9) == 5


def test_solar_position_noon_in_june_is_high_and_south():
    zenith, azimuth = solar_position(datetime(2026, 6, 21, 13, 50, tzinfo=timezone(timedelta(hours=2))), 48.1, -1.7)
    assert 23 < zenith < 28
    assert 170 < azimuth < 190


def test_clearsky_power_is_zero_at_night_and_bounded_at_noon():
    planes = [Plane(6.0, 30, 180)]
    assert clearsky_power(datetime(2026, 6, 21, 2, 0, tzinfo=PARIS), 48.1, -1.7, planes) == 0
    noon = clearsky_power(datetime(2026, 6, 21, 13, 0, tzinfo=PARIS), 48.1, -1.7, planes)
    assert 4.0 < noon < 6.0


def test_balance_ratios():
    day = Balance(pv=20, grid_import=4, grid_export=5, battery_in=6, battery_out=5)
    assert day.load == pytest.approx(18)
    assert self_consumption(day) == pytest.approx(0.75)
    assert self_sufficiency(day) == pytest.approx(14 / 18)
    assert self_consumption(Balance()) is None
    assert specific_yield(18.4, 6) == pytest.approx(3.0667, rel=1e-3)
    assert energy_performance_index(18.4, 20) == pytest.approx(0.92)
    assert energy_performance_index(1, 0) is None


def _day_curve(peak, limit=None, step=300):
    samples, expected = [], []
    for i in range(6 * 12, 21 * 12):
        t = i * step
        p = max(peak * math.sin(math.pi * (i - 72) / 180), 0.0)
        expected.append(p)
        samples.append((t, min(p, limit) if limit else p))
    return samples, expected


def test_clipping_detected_and_lost_energy_counted():
    samples, expected = _day_curve(5.4, limit=4.6)
    result = clipping_day(samples, expected, limit_kw=4.6)
    assert result.level == 4.6
    assert result.periods
    lost = sum(max(e - 4.6, 0) for e in expected) * 300 / 3600
    assert result.lost_kwh == pytest.approx(lost, rel=0.15)


def test_no_clipping_on_a_round_curve():
    samples, expected = _day_curve(4.0)
    assert clipping_day(samples, expected, limit_kw=4.6).periods == []


def test_flat_cloudy_day_is_not_clipping():
    samples = [(i * 300, 1.2) for i in range(60)]
    assert clipping_day(samples, [3.0] * 60, limit_kw=4.6).periods == []


def test_clipping_threshold_over_days():
    days = [_day_curve(5.4, limit=4.6)[0] for _ in range(8)] + [_day_curve(3.0)[0] for _ in range(2)]
    assert clipping_threshold(days) == pytest.approx(4.6)
    assert clipping_threshold(days[:3]) is None


def _sawtooth(days, rate=0.002, period=30):
    return [1.0 - rate * (d % period) for d in range(days)]


def test_soiling_srr_recovers_the_sawtooth_loss():
    result = soiling_srr(_sawtooth(180))
    assert result is not None
    expected_loss = 0.002 * sum(range(30)) / 30
    assert result.loss == pytest.approx(expected_loss, abs=0.01)
    assert result.confidence[0] <= result.ratio <= result.confidence[1] + 1e-9
    assert len(result.intervals) >= 4


def test_soiling_needs_three_months():
    assert soiling_srr(_sawtooth(60)) is None


def test_degradation_yoy():
    series = {d: 1.0 * (1 - 0.006 * d / 365) for d in range(800)}
    result = degradation_yoy(series)
    assert result is not None
    assert result.rate_pct_per_year == pytest.approx(-0.6, abs=0.05)
    assert degradation_yoy(dict.fromkeys(range(400), 1.0)) is None


def test_recurring_shading_found_at_the_same_time():
    days = []
    for d in range(14):
        day = {}
        for minute in range(8 * 60, 18 * 60, 15):
            expected = 0.5
            actual = 0.15 if 15 * 60 + 30 <= minute < 16 * 60 + 15 else 0.47
            if d == 3 and minute == 10 * 60:
                actual = 0.1
            day[minute] = (actual, expected)
        days.append(day)
    windows = recurring_shading(days)
    assert windows is not None
    assert len(windows) == 1
    assert windows[0].start_minute == 15 * 60 + 30
    assert windows[0].end_minute == 16 * 60 + 15
    assert windows[0].kwh_per_day > 0
    assert recurring_shading(days[:5]) is None


def test_mismatch_flags_a_lagging_string():
    days = [{"S1": (9.6, 3.0), "S2": (8.4, 3.0), "S3": (9.5, 3.0)} for _ in range(4)]
    scores = {s.name: s for s in score_units(days)}
    assert scores["S2"].lagging
    assert not scores["S1"].lagging
    assert scores["S2"].relative == pytest.approx(8.4 / 9.55)


def test_battery_fleet_is_weighted_and_sees_exchanges():
    batteries = [
        BatteryState("Maison", 15, 72, 1.2),
        BatteryState("Garage", 2.88, 45, -0.3),
        BatteryState("Balcon", 5.12, 100, 0),
    ]
    f = fleet(batteries)
    assert f.soc == pytest.approx((10.8 + 1.296 + 5.12) / 23 * 100)
    assert f.capacity_kwh == pytest.approx(23)
    assert f.charging == 1
    assert f.discharging == 1
    assert f.exchange_kw == pytest.approx(0.3)
    assert autonomy_hours(batteries, 0.6) == pytest.approx(
        ((72 - 10) / 100 * 15 + (45 - 10) / 100 * 2.88 + 0.9 * 5.12) / 0.6
    )
    assert hours_to_full(batteries[0]) == pytest.approx(0.28 * 15 / 1.2)
    assert hours_to_full(batteries[2]) is None


def test_battery_health_and_efficiency():
    assert cycles(4120, 10) == pytest.approx(412)
    assert round_trip_efficiency(6.4, 6.0) == pytest.approx(0.9375)
    assert round_trip_efficiency(0.1, 0.1) is None
    soh = soh_from_charge(20, 90, 7.0, 10)
    assert soh == pytest.approx(7.0 * 0.97 / 0.7 / 10 * 100)
    assert soh_from_charge(60, 80, 2, 10) is None


def test_cells_summary_and_drift():
    voltages = [3.331, 3.334, 3.332, 3.336, 3.312, 3.333]
    s = summarize(voltages)
    assert s.min_index == 4
    assert s.spread_mv == pytest.approx(24)
    drift = [18 + 0.8 * d for d in range(30)]
    assert days_to_threshold(drift, 50) == pytest.approx((50 - drift[-1]) / 0.8, rel=0.01)
    assert days_to_threshold([20.0] * 30) is None
    assert days_to_threshold([*drift[:-1], 60.0]) == 0


def test_finance():
    s = savings(10, 2, 0.2, 0.04)
    assert s.total == pytest.approx(2.08)
    p = payback(net_cost=8660, gained_so_far=5470, yearly_gain=1042, age_years=3.6, inverter_cost=1400)
    assert p.years_to_break_even is not None
    assert 2 < p.years_to_break_even < 4
    assert p.share_paid == pytest.approx(5470 / 8660)
    never = payback(net_cost=100000, gained_so_far=0, yearly_gain=100, horizon_years=20)
    assert never.years_to_break_even is None
