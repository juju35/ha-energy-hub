"""Declared strings and panels: PV total, per-string losses, and the finance figures they move.

The declarations come from YAML (``strings:`` / ``panels:``, each with its own kWp, tilt, azimuth and
``count_in_total``); the installation holds the units the readings actually carry. These tests build both by hand,
then check what the snapshot makes of them. The day's ``pv`` is what the coordinator integrated: it already holds
the declared units added to a meter (or the units' sum without one), so the engine reads it as it is.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from custom_components.energy_hub import engine
from custom_components.energy_hub.config import UnitConfig, parse
from custom_components.energy_hub.history import History, Reading
from custom_components.energy_hub.sources import Installation, UnitSource

TODAY = date(2026, 7, 17)
NOW = datetime(2026, 7, 17, 12, 0, tzinfo=timezone(timedelta(hours=1)))
LAT, LON = 48.1, -1.7


class DeclaredUnit(UnitConfig):
    """UnitConfig once the strings contract lands: a unit carries its own orientation and whether it counts."""

    __slots__ = ("azimuth", "count_in_total", "tilt")

    def __init__(
        self,
        name: str,
        *,
        power: str | None = None,
        kwp: float | None = None,
        tilt: float | None = None,
        azimuth: float | None = None,
        count_in_total: bool | None = None,
    ) -> None:
        super().__init__(name=name, power=power, kwp=kwp)
        self.tilt = tilt
        self.azimuth = azimuth
        self.count_in_total = count_in_total


def _hub(
    *, planes: list[float] | None = None, strings: list[DeclaredUnit] | None = None, cost: float | None = None
) -> Any:
    """A HubConfig shaped like the real one: ``kwp`` is the planes', else the strings' counted in the total."""
    from custom_components.energy_hub.analytics.clearsky import Plane

    base = parse({})
    cfg = SimpleNamespace(**{name: getattr(base, name) for name in base.__slots__})
    cfg.planes = [Plane(kwp) for kwp in (planes or [])] or list(base.planes)
    cfg.strings = list(strings or [])
    cfg.panels = []
    cfg.cost = cost
    cfg.kwp = (
        sum(p.kwp for p in cfg.planes)
        if cfg.planes
        else sum(u.kwp or 0.0 for u in cfg.strings if u.count_in_total is not False)
    )
    return cfg


def _history(days: dict[int, dict], *, strings: dict[str, float] | None = None) -> History:
    """A history whose days hold what the engine reads: energies, clear-sky reference, per-string energy."""
    h = History()
    for ago, values in days.items():
        rec = h.day(TODAY - timedelta(days=ago))
        rec.update(values)
        rec["strings"] = dict(strings or {})
    return h


def test_a_declared_string_is_the_pv_total_without_a_pv_power_role() -> None:
    """No ``pv_power`` role: the coordinator's total is the units' sum, and the string carries the capacity."""
    cfg = _hub(strings=[DeclaredUnit("South", power="sensor.south_power", kwp=3.0, tilt=30.0, azimuth=180.0)])
    inst = Installation(strings=[UnitSource("South", power="sensor.south_power", kwp=3.0)])
    history = _history({0: {"pv": 6.0, "clearsky": 20.0, "expected": 18.0}}, strings={"South": 6.0})

    snap = engine.build_snapshot(history, inst, cfg, Reading(t=NOW.timestamp()), NOW)

    assert snap["today"]["pv_kwh"] == 6.0
    assert snap["losses"]["today"]["produced"] == 6.0
    assert snap["kwp"] == 3.0 and snap["kwp_estimated"] is False
    south = snap["production"]["strings"][0]
    assert (south["kwp"], south["tilt"], south["azimuth"], south["count_in_total"]) == (3.0, 30.0, 180.0, True)


def test_a_declared_string_shows_its_capacity_before_it_produces_anything() -> None:
    """No history yet: the declaration alone fills the per-string fields, the losses stay empty."""
    cfg = _hub(strings=[DeclaredUnit("South", power="sensor.south_power", kwp=3.0, tilt=25.0, azimuth=200.0)])
    inst = Installation(strings=[UnitSource("South", power="sensor.south_power", kwp=3.0)])

    snap = engine.build_snapshot(History(), inst, cfg, Reading(t=NOW.timestamp()), NOW)

    south = snap["production"]["strings"][0]
    assert (south["kwp"], south["tilt"], south["azimuth"], south["count_in_total"]) == (3.0, 25.0, 200.0, True)
    assert south["soiling"] is None and south["expected_kwh"] is None


def test_a_pv_power_role_already_metering_the_string_is_not_counted_twice() -> None:
    """The string's own sensor is the ``pv_power`` role: its energy is already in the total."""
    cfg = _hub(planes=[6.0], strings=[DeclaredUnit("South", power="sensor.pv_total", kwp=3.0)])
    inst = Installation(
        roles={"pv_power": "sensor.pv_total"},
        strings=[UnitSource("South", power="sensor.pv_total", kwp=3.0)],
    )
    history = _history({0: {"pv": 6.0, "clearsky": 40.0, "expected": 36.0}}, strings={"South": 6.0})

    snap = engine.build_snapshot(history, inst, cfg, Reading(t=NOW.timestamp(), pv_kw=3.0), NOW)

    assert snap["today"]["pv_kwh"] == 6.0
    # The string sits on the plane: the capacity is the plane's 6 kWp, not 6 + 3.
    assert snap["kwp"] == 6.0


def test_a_string_added_to_the_meter_is_not_added_a_second_time() -> None:
    """The coordinator already added the garage string to the meter: the engine must not add its kWh again."""
    cfg = _hub(
        planes=[6.0],
        strings=[
            DeclaredUnit("South", power="sensor.pv_total", kwp=3.0),
            DeclaredUnit("Garage", power="sensor.garage_power", kwp=2.0, count_in_total=True),
        ],
    )
    inst = Installation(
        roles={"pv_power": "sensor.pv_total"},
        strings=[
            UnitSource("South", power="sensor.pv_total", kwp=3.0),
            UnitSource("Garage", power="sensor.garage_power", kwp=2.0),
        ],
    )
    # 10 kWh metered + 4 kWh from the garage string, as the coordinator integrated them.
    history = _history({0: {"pv": 14.0, "clearsky": 40.0, "expected": 36.0}}, strings={"South": 6.0, "Garage": 4.0})

    snap = engine.build_snapshot(history, inst, cfg, Reading(t=NOW.timestamp()), NOW)

    assert snap["today"]["pv_kwh"] == 14.0
    assert snap["losses"]["today"]["produced"] == 14.0
    assert snap["kwp"] == 6.0


def test_a_string_left_out_of_the_total_is_ignored_even_though_it_produces() -> None:
    """``count_in_total: false``: still shown and still on the roof, but its energy is left out of the total."""
    cfg = _hub(
        planes=[6.0],
        strings=[DeclaredUnit("Shelter", power="sensor.shelter_power", kwp=2.0, count_in_total=False)],
    )
    inst = Installation(strings=[UnitSource("Shelter", power="sensor.shelter_power", kwp=2.0)])
    history = _history({0: {"pv": 5.0, "clearsky": 40.0, "expected": 36.0}}, strings={"Shelter": 4.0})

    snap = engine.build_snapshot(history, inst, cfg, Reading(t=NOW.timestamp()), NOW)

    assert snap["today"]["pv_kwh"] == 5.0
    assert snap["kwp"] == 6.0
    assert snap["today"]["specific_yield"] == pytest.approx(5 / 6, abs=0.01)
    assert snap["production"]["strings"][0]["count_in_total"] is False
    assert snap["production"]["strings"][0]["kwh"] == 4.0


def test_the_strings_kwp_lowers_the_specific_yield_and_shortens_the_payback() -> None:
    """Capacity and gains both follow the declarations: kWh/kWc drops, the installation is paid back sooner."""
    counted = _hub(strings=[DeclaredUnit("South", power="sensor.south_power", kwp=3.0)], cost=6000.0)
    bigger = _hub(strings=[DeclaredUnit("South", power="sensor.south_power", kwp=6.0)], cost=6000.0)
    left_out = _hub(
        planes=[3.0],
        strings=[DeclaredUnit("South", power="sensor.south_power", kwp=3.0, count_in_total=False)],
        cost=6000.0,
    )
    inst = Installation(strings=[UnitSource("South", power="sensor.south_power", kwp=3.0)])
    history = _history({0: {"pv": 6.0, "clearsky": 20.0, "expected": 18.0}}, strings={"South": 6.0})
    # Left out of the total, the string's energy never reached the coordinator's total.
    nothing = _history({0: {"pv": 0.0, "clearsky": 20.0, "expected": 18.0}}, strings={"South": 6.0})

    on = engine.build_snapshot(history, inst, counted, Reading(t=NOW.timestamp()), NOW)
    wide = engine.build_snapshot(history, inst, bigger, Reading(t=NOW.timestamp()), NOW)
    off = engine.build_snapshot(nothing, inst, left_out, Reading(t=NOW.timestamp()), NOW)

    # Without a plane the declared kWp is the denominator: the same 6 kWh gives 6/3 kWh/kWc with a 3 kWc string
    # declared, 6/6 with a 6 kWc one.
    assert on["kwp"] == 3.0 and wide["kwp"] == 6.0
    assert on["today"]["specific_yield"] == pytest.approx(6 / 3, abs=0.01)
    assert wide["today"]["specific_yield"] == pytest.approx(6 / 6, abs=0.01)
    # Only the counted string earns its savings, so it alone reaches break-even and a positive ROI.
    assert on["finances"]["yearly"] > 0
    assert on["finances"]["years_to_break_even"] is not None
    assert off["today"]["specific_yield"] == 0.0
    assert off["finances"]["yearly"] == 0
    assert off["finances"]["years_to_break_even"] is None
    assert on["finances"]["gain_at_horizon"] > off["finances"]["gain_at_horizon"]


def test_each_string_is_weighed_on_its_own_orientation() -> None:
    """A steep and a flat string, same production: the steep one misses its own clear-sky expectation more."""
    cfg = _hub(
        planes=[6.0],
        strings=[
            DeclaredUnit("Flat", power="sensor.flat_power", kwp=3.0, tilt=10.0, azimuth=180.0),
            DeclaredUnit("Steep", power="sensor.steep_power", kwp=3.0, tilt=70.0, azimuth=180.0),
        ],
    )
    inst = Installation(
        strings=[
            UnitSource("Flat", power="sensor.flat_power", kwp=3.0),
            UnitSource("Steep", power="sensor.steep_power", kwp=3.0),
        ]
    )
    days = {ago: {"pv": 20.0, "clearsky": 25.0, "expected": 22.0} for ago in range(8)}
    history = _history(days, strings={"Flat": 8.0, "Steep": 8.0})

    snap = engine.build_snapshot(history, inst, cfg, Reading(t=NOW.timestamp()), NOW, latitude=LAT, longitude=LON)

    rows = {s["name"]: s for s in snap["production"]["strings"]}
    assert rows["Flat"]["tilt"] == 10.0 and rows["Steep"]["tilt"] == 70.0
    # Same production, but July's sun favours the flat string: its expectation is the higher one, so the same
    # 8 kWh leaves a lower performance ratio — the steep string is not flagged for its pitch.
    assert rows["Flat"]["expected_kwh"] > rows["Steep"]["expected_kwh"] > 0
    assert rows["Steep"]["performance"] > rows["Flat"]["performance"]
    assert rows["Flat"]["yield"] == rows["Steep"]["yield"] == pytest.approx(8 / 3, abs=0.01)
    # The per-string losses are published next to the installation-wide ones, with their own orientation.
    losses = {s["name"]: s for s in snap["losses"]["strings"]}
    assert set(losses) == {"Flat", "Steep"}
    assert (losses["Steep"]["tilt"], losses["Steep"]["azimuth"]) == (70.0, 180.0)
    assert losses["Flat"]["expected_kwh"] == rows["Flat"]["expected_kwh"]


def test_per_string_losses_stay_learning_without_enough_history() -> None:
    """Soiling and degradation need months of clear days: below that the per-string fields stay empty."""
    cfg = _hub(planes=[6.0], strings=[DeclaredUnit("South", power="sensor.south_power", kwp=3.0)])
    inst = Installation(strings=[UnitSource("South", power="sensor.south_power", kwp=3.0)])
    history = _history({0: {"pv": 20.0, "clearsky": 25.0, "expected": 22.0}}, strings={"South": 8.0})

    snap = engine.build_snapshot(history, inst, cfg, Reading(t=NOW.timestamp()), NOW)

    south = snap["production"]["strings"][0]
    assert south["soiling"] is None and south["degradation_pct"] is None
    assert south["expected_kwh"] is not None  # the day itself is enough to compare today's production
    assert snap["losses"]["strings"][0]["soiling"] is None


def test_the_per_unit_fields_do_not_break_the_existing_payload_keys() -> None:
    """The keys the panel and the docs already read are still there, unchanged in shape."""
    cfg = _hub(planes=[6.0], strings=[DeclaredUnit("South", power="sensor.south_power", kwp=3.0)])
    inst = Installation(strings=[UnitSource("South", power="sensor.south_power", kwp=3.0)])
    history = _history({0: {"pv": 12.0, "clearsky": 25.0, "expected": 22.0}}, strings={"South": 6.0})

    snap = engine.build_snapshot(history, inst, cfg, Reading(t=NOW.timestamp(), strings={"South": 3.0}), NOW)

    string = snap["production"]["strings"][0]
    for key in ("name", "kw", "kwh", "relative", "lagging_days", "kwp", "tilt", "azimuth", "count_in_total"):
        assert key in string
    for key in ("potential", "clipping", "shading", "soiling", "limitation", "unavailability", "produced"):
        assert key in snap["losses"]["today"]
    for key in ("today", "month", "year", "since", "yearly", "years_to_break_even", "gain_at_horizon"):
        assert key in snap["finances"]
