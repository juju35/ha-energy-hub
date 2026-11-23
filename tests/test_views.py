"""The reshaping of the history for the panel: events' status, data quality, projections, periods, bill."""

from datetime import UTC, date, datetime, timedelta

from custom_components.energy_hub import views
from custom_components.energy_hub.history import History
from custom_components.energy_hub.sources import BatterySource, Installation

TODAY = date(2026, 7, 17)


def _history(days: dict[int, dict]) -> History:
    h = History()
    for ago, values in days.items():
        rec = h.day(TODAY - timedelta(days=ago))
        rec.update(values)
    return h


def test_event_status():
    assert views._status([], TODAY) == "resolved"
    recent = [(TODAY - timedelta(days=i)).isoformat() for i in (0, 1, 3)]
    assert views._status(recent, TODAY) == "recurring"
    assert views._status([TODAY.isoformat()], TODAY) == "watch"
    assert views._status([(TODAY - timedelta(days=5)).isoformat()], TODAY) == "resolved"


def test_events_from_days():
    h = _history({0: {"clipped": 1.0}, 1: {"clipped": 0.8}, 2: {"clipped": 0.5}, 12: {"unavailable": 1.6}})
    ev = views.events(
        h,
        TODAY,
        clipping_kwh=0.3,
        strings=[{"name": "String 2", "lagging_days": 7, "relative": 0.84}],
        shading=None,
        soiling_loss=None,
        soiling_alert=0.03,
        cell_alerts=[],
    )
    kinds = {e["kind"]: e for e in ev}
    assert kinds["clipping"]["status"] == "recurring"
    assert kinds["clipping"]["days"] == 3
    assert kinds["unavailability"]["status"] == "resolved"
    assert kinds["string_lagging"]["status"] == "recurring"
    assert ev[-1]["status"] == "resolved"


def test_quality_finds_the_gap():
    now = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)
    start = now.timestamp() - 86400
    buckets = [{"t": start + i * 300} for i in range(288)]
    for b in buckets[40:43]:
        b["stale"] = ["sensor.meter"]
    inst = Installation(roles={"grid_power": "sensor.meter", "pv_power": "sensor.pv"})
    rows = {r["role"]: r for r in views.quality(buckets, inst, now)}
    assert rows["pv_power"]["share"] == 1.0
    assert rows["grid_power"]["share"] < 1.0
    assert len(rows["grid_power"]["gaps"]) == 1
    assert rows["grid_power"]["gaps"][0][1] - rows["grid_power"]["gaps"][0][0] == 900


def test_soc_projection_stops_at_full_and_reserve():
    now = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)
    up = views.soc_projection(now, 90.0, 2.0, 10.0, 10.0)
    assert up[-1][1] == 100.0
    down = views.soc_projection(now, 20.0, -2.0, 10.0, 10.0)
    assert down[-1][1] == 10.0
    assert views.soc_projection(now, 50.0, 0.0, 10.0, 10.0) == []


def test_periods_and_bill():
    h = _history({i: {"pv": 10.0, "expected": 12.0, "load": 8.0, "import": 2.0, "export": 4.0} for i in range(40)})
    p = views.periods(h, TODAY)
    assert len(p["7d"]) == 7
    assert len(p["30d"]) == 30
    assert p["7d"][-1]["d"] == TODAY.isoformat()
    bill = views.bill(h, TODAY, 0.2, 0.05)
    assert bill["month"]["without"] == round(17 * 8 * 0.2, 2)
    assert bill["month"]["with"] == round(17 * (2 * 0.2 - 4 * 0.05), 2)


def test_bms_suggestion_and_correlation():
    inst = Installation(
        batteries=[
            BatterySource(key="house", name="House", platform="powerwall", soc="sensor.a"),
            BatterySource(key="bms", name="BMS", platform="bms_ble", soc="sensor.b", cells=["sensor.bms_cells"]),
        ]
    )
    from custom_components.energy_hub.sources import _suggest_bms

    _suggest_bms(inst)
    buckets = [{"t": i, "soc:house": 50 + i, "soc:bms": 49 + i * 1.01} for i in range(20)]
    out = views.suggestions(inst, False, [], buckets)
    attach = next(s for s in out if s["kind"] == "attach_bms")
    assert attach["battery"] == "House"
    assert attach["correlation"] == 1.0
    assert "cells: sensor.bms_cells" in attach["yaml"]


def test_bill_uses_the_half_hour_prices_when_known():
    h = _history({1: {"load": 8.0, "import": 2.0, "export": 4.0, "import_eur": 0.5, "load_eur": 1.9}})
    bill = views.bill(h, TODAY, 0.2, 0.05)
    assert bill["month"]["with"] == round(0.5 - 4 * 0.05, 2)
    assert bill["month"]["without"] == 1.9


def _cfg(**tariff):
    from custom_components.energy_hub.config import parse

    return parse({"tariff": tariff} if tariff else {})


def test_comparator_learns_then_ranks_the_offers():
    evening = [0.0] * 48
    evening[38] = 1.0  # 19:00, a peak hour
    inst = Installation(tariff={"contract": "hphc", "kva": 9})
    few = views.comparator(_history({i: {"imp48": evening} for i in range(1, 6)}), _cfg(), inst, TODAY)
    assert few["offers"] == [] and few["days"] == 5 and few["contract_source"] == "tarif_edf"
    h = _history({i: {"imp48": evening} for i in range(1, 31)})
    h.days[(TODAY - timedelta(days=1)).isoformat()]["color"] = "rouge"
    c = views.comparator(h, _cfg(), inst, TODAY)
    assert c["kva"] == 9 and not c["kva_assumed"] and c["offpeak_assumed"]
    assert c["current"] == "hphc" and c["colors"] == 1
    assert c["best"] == "tempo"  # summer peak hours: blue Tempo days are the cheapest
    assert c["saving"] > 0
    assert c["offers"][0]["delta"] < 0
    assert next(o for o in c["offers"] if o["key"] == "hphc")["delta"] == 0


def test_yaml_contract_wins_and_cache_holds_a_day():
    inst = Installation(tariff={"contract": "tempo", "kva": 9})
    cfg = _cfg(contract="base", kva=6, offpeak="23:00-07:00")
    c = views.contract(cfg, inst)
    assert (c["contract"], c["kva"], c["contract_source"], c["offpeak"]) == ("base", 6, "yaml", "23:00-07:00")
    h = _history({i: {"imp48": [0.1] * 48} for i in range(1, 20)})
    first = views.cached_comparator(h, cfg, inst, TODAY)
    assert views.cached_comparator(h, cfg, inst, TODAY) is first
    assert views.contract_offer(cfg, inst).key == "base"
    assert views.contract_offer(_cfg(), Installation()) is None


def test_history_values_energy_at_the_reading_price():
    from custom_components.energy_hub.history import Reading

    h = History()
    start = datetime(2026, 7, 17, 19, 0, tzinfo=UTC)
    for minute in range(0, 61, 1):
        t = start + timedelta(minutes=minute)
        h.add(Reading(t=t.timestamp(), pv_kw=1.0, load_kw=3.0, grid_kw=2.0, import_price=0.25, day_color="blue"), t)
    rec = h.days["2026-07-17"]
    assert abs(sum(rec["imp48"]) - rec["import"]) < 1e-9
    assert abs(rec["imp48"][38] - 1.0) < 1e-6 and abs(rec["imp48"][39] - 1.0) < 1e-6
    assert abs(rec["import_eur"] - 0.5) < 1e-6
    assert abs(rec["self_eur"] - 0.25) < 1e-6
    assert rec["color"] == "blue"
