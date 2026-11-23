"""The snapshot the panel draws, computed from the history, the installation and the latest reading.

No Home Assistant import: the coordinator calls ``build_snapshot`` in the executor, and the tests call it on the
demo history directly.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timedelta
from statistics import median
from typing import Any

from . import views
from .analytics.battery import (
    BatteryState,
    autonomy_hours,
    cycles,
    fleet,
    hours_to_full,
    round_trip_efficiency,
    soh_from_charge,
)
from .analytics.cells import DEFAULT_THRESHOLD_MV, days_to_threshold, summarize
from .analytics.clipping import clipping_day, clipping_threshold
from .analytics.degradation import MIN_DAYS as DEGRADATION_DAYS
from .analytics.degradation import degradation_yoy
from .analytics.finance import payback, savings
from .analytics.kpis import (
    Balance,
    energy_performance_index,
    self_consumption,
    self_sufficiency,
    specific_yield,
)
from .analytics.mismatch import score_units
from .analytics.shading import MIN_CLEAR_DAYS, recurring_shading
from .analytics.soiling import MIN_DAYS as SOILING_DAYS
from .analytics.soiling import soiling_srr
from .config import HubConfig
from .history import History, Reading
from .sources import DEFAULT_CAPACITY_KWH, Installation

# Thresholds of the alerts.
CLIPPING_ALERT_KWH = 0.3
SOILING_ALERT = 0.03
CELL_ALERT_DAYS = 14


def _balance(record: dict[str, Any] | None) -> Balance:
    if not record:
        return Balance()
    return Balance(
        pv=record["pv"],
        grid_import=record["import"],
        grid_export=record["export"],
        battery_in=sum(record["batt_in"].values()),
        battery_out=sum(record["batt_out"].values()),
    )


def _r(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


def estimate_kwp(cfg: HubConfig, history: History) -> tuple[float, bool]:
    """Installed kWp: from the planes in YAML, else 1.15 × the highest daily peak seen (estimated)."""
    if cfg.kwp:
        return cfg.kwp, False
    peaks = [d["peak"] for d in history.days.values() if d.get("peak")]
    return (round(max(peaks) * 1.15, 2), True) if peaks else (0.0, True)


def _daily_pi(history: History) -> list[tuple[date, float, float]]:
    """(day, performance index, rain) of each past day with enough expected energy, oldest first."""
    rows = []
    for key in sorted(history.days)[:-1]:
        d = history.days[key]
        ref = d.get("clearsky") or 0.0
        if ref < 0.5 or d["pv"] <= 0:
            continue
        rows.append((date.fromisoformat(key), d["pv"] / ref, d.get("rain", 0.0)))
    return rows


def _clear_days(rows: list[tuple[date, float, float]]) -> list[tuple[date, float, float]]:
    """The days near the clear sky: the trend analyses run on them (RdTools' clear-sky filtering)."""
    if not rows:
        return []
    top = sorted(r[1] for r in rows)[int(len(rows) * 0.9)] if len(rows) > 10 else max(r[1] for r in rows)
    return [r for r in rows if r[1] >= 0.8 * top]


def _learning(days: int, needed: int) -> dict[str, Any]:
    return {"learning": True, "days": days, "needed": needed}


def _unit_shading(history: History) -> list[tuple[str | None, Any]] | None:
    """Recurring shading of each string / panel against the median of its peers at the same time (bins of the past
    days): a chimney over one panel shows there, not in the whole installation's curve."""
    ratios = {}
    for key in sorted(history.unit_bins)[:-1]:
        system = history.bins.get(key, {})
        cs = sum(e for _a, e in system.values())
        ratios[key] = sum(a for a, _e in system.values()) / cs if cs > 0 else 0.0
    if not ratios:
        return None
    top = max(ratios.values())
    days = [history.unit_bins[k] for k, r in ratios.items() if top > 0 and r >= 0.85 * top]
    if not days:
        return None
    names = sorted({n for d in days for b in d.values() for n in b})
    if len(names) < 2:
        return None
    found: list[tuple[str | None, Any]] = []
    enough = False
    for name in names:
        unit_days = []
        for d in days:
            bins = {}
            for minute, values in d.items():
                if name in values and len(values) >= 2:
                    peers = sorted(v for n, v in values.items() if n != name)
                    bins[int(minute)] = (values[name], peers[len(peers) // 2])
            unit_days.append(bins)
        windows = recurring_shading(unit_days, clear_day=0.0)
        if windows is not None:
            enough = True
            found += [(name, w) for w in windows]
    return found if enough else None


def build_snapshot(
    history: History,
    inst: Installation,
    cfg: HubConfig,
    reading: Reading | None,
    now: datetime,
    ages: dict[str, float] | None = None,
    demo: bool = False,
) -> dict[str, Any]:
    today = now.date()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    rec = history.day(today)
    yrec = history.days.get((today - timedelta(days=1)).isoformat())
    kwp, kwp_estimated = estimate_kwp(cfg, history)
    bal = _balance(rec)
    ybal = _balance(yrec)

    # ---- today's curve and clipping
    buckets = history.today_buckets(day_start)
    curve = [{k: b.get(k) for k in ("t", "pv", "exp", "cs", "load", "grid", "batt", "soc")} for b in buckets]
    samples = [(b["t"], b.get("pv") or 0.0) for b in buckets]
    expected = [max(b.get("exp") or 0.0, b.get("cs") or 0.0) if b.get("exp") is None else b["exp"] for b in buckets]
    peaks = [d["peak"] for k, d in sorted(history.days.items())[-30:] if d.get("peak")]
    limit = cfg.inverter_max_kw or clipping_threshold([[(0.0, p)] for p in peaks])
    clip = clipping_day(samples, expected, limit_kw=limit)
    if cfg.export_limit_kw and clip.periods:
        # A plateau while exporting at the grid limit is the export limitation, not the inverter's maximum.
        at_limit = [b for b in buckets if -(b.get("grid") or 0) >= 0.98 * cfg.export_limit_kw]
        if at_limit and any(a <= b["t"] <= z for b in at_limit for a, z in clip.periods):
            clip.periods = []
            clip.lost_kwh = 0.0
    if not demo or clip.lost_kwh:
        rec["clipped"] = round(clip.lost_kwh, 4)
        clip_h = [0.0] * 24
        for (t, p), e in zip(samples, expected, strict=True):
            if any(a <= t <= b for a, b in clip.periods):
                clip_h[datetime.fromtimestamp(t, now.tzinfo).hour] += max(e - p, 0) * 300 / 3600
        rec["clip_h"] = [round(x, 4) for x in clip_h]

    # ---- export limitation: exporting at the limit with every battery full
    limited = 0.0
    if cfg.export_limit_kw:
        for b in buckets:
            if -(b.get("grid") or 0) >= 0.98 * cfg.export_limit_kw:
                limited += max((b.get("exp") or 0) - (b.get("pv") or 0), 0) * 300 / 3600
        rec["limited"] = round(limited, 4)

    # ---- trends
    rows = _daily_pi(history)
    clear = _clear_days(rows)
    soiling = soiling_srr([r[1] for r in clear], rain=[r[2] for r in clear]) if len(clear) >= SOILING_DAYS else None
    degr = degradation_yoy({r[0].toordinal(): r[1] for r in clear}) if rows else None
    bin_days = [{int(m): (a, e) for m, (a, e) in history.bins[k].items()} for k in sorted(history.bins)[:-1]]
    shading = _unit_shading(history) if history.unit_bins else None
    if shading is None:
        shading = recurring_shading(bin_days)
        shading = [(None, w) for w in shading] if shading is not None else None
    shading_today = sum(w.kwh_per_day for _u, w in shading or []) if bal.pv else 0.0
    soiling_today = bal.pv * (1 / soiling.ratio - 1) if soiling and soiling.ratio > 0 else 0.0

    # ---- strings, panels
    def unit_days(kind: str, count: int) -> list[dict[str, tuple[float, float]]]:
        days = []
        for key in sorted(history.days)[-8:]:
            values = history.days[key][kind]
            if values:
                share = kwp / max(len(values), 1) if kwp else 1.0
                days.append({n: (e, share) for n, e in values.items()})
        return days[-count:]

    string_scores = {s.name: s for s in score_units(unit_days("strings", 7))}
    unit_scores = {s.name: s for s in score_units(unit_days("units", 7))}
    strings = [
        {
            "name": u.name,
            "kw": _r(reading.strings.get(u.name) if reading else None, 3),
            "kwh": _r(rec["strings"].get(u.name), 2),
            "relative": _r(string_scores[u.name].relative, 3) if u.name in string_scores else None,
            "lagging_days": string_scores[u.name].lagging_days if u.name in string_scores else 0,
        }
        for u in inst.strings
    ]
    best_unit = max((rec["units"].get(u.name, 0) for u in inst.units), default=0)
    units = [
        {
            "name": u.name,
            "kw": _r(reading.units.get(u.name) if reading else None, 3),
            "kwh": _r(rec["units"].get(u.name), 3),
            "pct": round(rec["units"].get(u.name, 0) / best_unit * 100) if best_unit else None,
            "lagging_days": unit_scores[u.name].lagging_days if u.name in unit_scores else 0,
        }
        for u in inst.units
    ]

    # ---- history series
    epi_30 = []
    for key in sorted(history.days)[-31:-1]:
        d = history.days[key]
        if d.get("expected", 0) > 0.3:
            epi_30.append({"d": key, "epi": _r(d["pv"] / d["expected"], 3), "rain": d.get("rain", 0) >= 1})
    months: dict[str, dict[str, float]] = {}
    for key, d in history.days.items():
        m = months.setdefault(key[:7], {"kwh": 0.0, "expected": 0.0, "clearsky": 0.0, "days": 0})
        m["kwh"] += d["pv"]
        m["expected"] += d.get("expected", 0.0)
        m["clearsky"] += d.get("clearsky", 0.0)
        m["days"] += 1
    month_rows = [{"m": k, **{kk: _r(v, 1) for kk, v in m.items()}} for k, m in sorted(months.items())[-12:]]
    month_key = today.isoformat()[:7]
    month_days = [d for k, d in history.days.items() if k.startswith(month_key)]

    # ---- losses
    potential = bal.pv + rec.get("clipped", 0) + limited + shading_today + soiling_today + rec.get("unavailable", 0)
    month_causes = {
        "clipping": sum(d.get("clipped", 0) for d in month_days),
        "shading": (sum(w.kwh_per_day for _u, w in shading) * len(month_days)) if shading else 0.0,
        "soiling": sum(d["pv"] for d in month_days) * (1 / soiling.ratio - 1) if soiling and soiling.ratio else 0.0,
        "limitation": sum(d.get("limited", 0) for d in month_days),
        "unavailability": sum(d.get("unavailable", 0) for d in month_days),
    }
    heatmap = [
        {"d": key, "h": [_r(x, 3) for x in history.days[key].get("clip_h", [0.0] * 24)[10:17]]}
        for key in sorted(history.days)[-30:]
    ]
    month_pv = sum(d["pv"] for d in month_days)
    availability = 1 - month_causes["unavailability"] / max(month_pv + month_causes["unavailability"], 1e-6)

    # ---- batteries
    meta = {b.key: b for b in inst.batteries}
    states: list[BatteryState] = []
    items = []
    days_sorted = sorted(history.days)
    for b in reading.batteries if reading else []:
        src = meta.get(b.key)
        cap = b.capacity_kwh or (src.capacity_kwh if src else None)
        cap_estimated = cap is None
        cap = cap or DEFAULT_CAPACITY_KWH
        reserve = src.reserve if src else 10.0
        states.append(BatteryState(b.key, cap, b.soc or 0.0, b.power_kw or 0.0, reserve))
        out_total = sum(history.days[k]["batt_out"].get(b.key, 0) for k in days_sorted)
        in_30 = sum(history.days[k]["batt_in"].get(b.key, 0) for k in days_sorted[-31:-1])
        out_30 = sum(history.days[k]["batt_out"].get(b.key, 0) for k in days_sorted[-31:-1])
        soh_samples = []
        for k in days_sorted[-31:-1]:
            d = history.days[k]
            lo, hi = d["soc_min"].get(b.key), d["soc_max"].get(b.key)
            if lo is not None and hi is not None and d["batt_in"].get(b.key):
                soh = soh_from_charge(lo, hi, d["batt_in"][b.key], cap)
                if soh is not None:
                    soh_samples.append(soh)
        cell_info = None
        if len(b.cells) > 1:
            summary = summarize(b.cells)
            spreads = [history.days[k]["cells_spread"].get(b.key) for k in days_sorted[-30:]]
            spreads = [s for s in spreads if s is not None]
            cell_info = {
                "voltages": b.cells,
                "summary": asdict(summary) if summary else None,
                "spread_30d": [_r(s, 1) for s in spreads],
                "threshold_mv": DEFAULT_THRESHOLD_MV,
                "days_to_threshold": _r(days_to_threshold(spreads), 1),
            }
        if cell_info is not None:
            cell_info.update(views.cells_detail(history, b, today))
        state = "charging" if (b.power_kw or 0) > 0.05 else "discharging" if (b.power_kw or 0) < -0.05 else "idle"
        if (b.soc or 0) >= 99.5 and state == "idle":
            state = "full"
        items.append(
            {
                "key": b.key,
                "name": src.name if src else b.key,
                "platform": src.platform if src else "",
                "soc": _r(b.soc, 1),
                "power_kw": _r(b.power_kw, 3),
                "state": state,
                "capacity_kwh": cap,
                "capacity_estimated": cap_estimated,
                "reserve": reserve,
                "soh": _r(b.soh, 1) if b.soh is not None else _r(median(soh_samples), 1) if soh_samples else None,
                "soh_estimated": b.soh is None,
                "cycles": _r(b.cycles, 0) if b.cycles is not None else _r(cycles(out_total, cap), 0),
                "cycles_estimated": b.cycles is None,
                "rte": _r(round_trip_efficiency(in_30, out_30), 3),
                "temperature": _r(b.temperature, 1),
                "hours_to_full": _r(hours_to_full(states[-1]), 2),
                "autonomy_h": _r(autonomy_hours([states[-1]], (reading.load_kw or 0.0) if reading else 0.0), 1),
                "coupling": views.coupling(src.platform if src else ""),
                "soc_today": views.soc_today(buckets, b.key),
                "soc_projection": views.soc_projection(now, b.soc, b.power_kw, cap, reserve),
                "soh_trend": views.soh_trend(history, b.key, today),
                "modules": b.modules,
                "cells": cell_info,
            }
        )
    fl = fleet(states) if states else None
    load_now = reading.load_kw if reading and reading.load_kw else None

    # ---- finances
    def gain(d: dict[str, Any]) -> float:
        # Self-consumption valued at the price of its half hour when the contract's prices were known that day.
        if "self_eur" in d:
            return d["self_eur"] + d["export"] * cfg.export_price
        return savings(max(d["pv"] - d["export"], 0), d["export"], cfg.import_price, cfg.export_price).total

    gains_by_day = {k: gain(d) for k, d in history.days.items()}
    year_keys = days_sorted[-365:]
    year_gain = sum(gains_by_day[k] for k in year_keys)
    since = sum(gains_by_day.values())
    commissioned = cfg.commissioned or (date.fromisoformat(days_sorted[0]) if days_sorted else today)
    age_years = max((today - commissioned).days / 365.25, 0.0)
    if cfg.commissioned and days_sorted and (date.fromisoformat(days_sorted[0]) - cfg.commissioned).days > 30:
        # History shorter than the installation's life: the missing years at this year's pace.
        missing = (date.fromisoformat(days_sorted[0]) - cfg.commissioned).days / 365.25
        since += missing * (year_gain * 365 / max(len(year_keys), 1))
    yearly = year_gain * 365 / max(len(year_keys), 1)
    net_cost = (cfg.cost - cfg.subsidy) if cfg.cost else None
    pay = (
        payback(
            net_cost,
            since,
            yearly,
            age_years=age_years,
            inverter_cost=cfg.inverter_replacement_cost,
            inverter_at_year=cfg.inverter_lifetime_years,
        )
        if net_cost
        else None
    )
    year_records = [history.days[k] for k in year_keys]
    direct = sum(max(d["pv"] - d["export"] - sum(d["batt_in"].values()), 0) for d in year_records)
    restored = sum(sum(d["batt_out"].values()) for d in year_records)
    exported = sum(d["export"] for d in year_records)
    monthly_gains = {}
    for k in days_sorted:
        monthly_gains[k[:7]] = monthly_gains.get(k[:7], 0.0) + gains_by_day[k]

    # ---- alerts
    alerts = []
    if rec.get("clipped", 0) >= CLIPPING_ALERT_KWH:
        recent_clip = sum(1 for k in days_sorted[-7:] if history.days[k].get("clipped", 0) >= CLIPPING_ALERT_KWH)
        alerts.append(
            {
                "kind": "clipping",
                "severity": "error",
                "kwh": _r(rec["clipped"], 2),
                "days_week": recent_clip,
                "level_kw": _r(clip.level, 2),
                "periods": clip.periods,
            }
        )
    alerts.extend(
        {
            "kind": "string_lagging",
            "severity": "warning",
            "name": s["name"],
            "relative": s["relative"],
            "days": s["lagging_days"],
        }
        for s in strings
        if s["lagging_days"] >= 3
    )
    for unit, w in shading or []:
        alerts.append(
            {
                "kind": "shading",
                "severity": "warning",
                "unit": unit,
                "start": w.start_minute,
                "end": w.end_minute,
                "kwh": _r(w.kwh_per_day, 2),
            }
        )
    if soiling and soiling.loss >= SOILING_ALERT:
        alerts.append({"kind": "soiling", "severity": "warning", "loss": _r(soiling.loss, 3)})
    for item in items:
        cells = item["cells"]
        if cells and cells["days_to_threshold"] is not None and cells["days_to_threshold"] <= CELL_ALERT_DAYS:
            alerts.append(
                {
                    "kind": "cell_drift",
                    "severity": "warning",
                    "battery": item["name"],
                    "cell": cells["summary"]["min_index"] + 1,
                    "days": cells["days_to_threshold"],
                }
            )
    if fl and fl.exchange_kw > 0.1:
        alerts.append({"kind": "battery_exchange", "severity": "info", "kw": _r(fl.exchange_kw, 2)})
    if reading and reading.stale:
        alerts.append(
            {"kind": "stale", "severity": "error" if reading.offline else "warning", "entities": reading.stale}
        )
    cell_alerts = [a for a in alerts if a["kind"] == "cell_drift"]
    loss_events = views.events(
        history,
        today,
        clipping_kwh=CLIPPING_ALERT_KWH,
        strings=strings,
        shading=shading,
        soiling_loss=soiling.loss if soiling else None,
        soiling_alert=SOILING_ALERT,
        cell_alerts=[{k: v for k, v in a.items() if k != "severity"} for a in cell_alerts],
    )

    return {
        "demo": demo,
        "generated": now.isoformat(),
        "kwp": kwp,
        "kwp_estimated": kwp_estimated,
        "currency": cfg.currency,
        "inverter_max_kw": limit,
        "export_limit_kw": cfg.export_limit_kw,
        "live": {
            "pv_kw": _r(reading.pv_kw, 3) if reading else None,
            "load_kw": _r(load_now, 3),
            "grid_kw": _r(reading.grid_kw, 3) if reading else None,
            "battery_kw": _r(reading.battery_kw, 3) if reading and reading.batteries else None,
            "expected_kw": _r(reading.expected_kw, 3) if reading else None,
            "peak_share": _r(reading.pv_kw / kwp, 3) if reading and reading.pv_kw is not None and kwp else None,
        },
        "today": {
            "pv_kwh": _r(bal.pv),
            "load_kwh": _r(rec.get("load") or bal.load),
            "import_kwh": _r(bal.grid_import),
            "export_kwh": _r(bal.grid_export),
            "battery_in_kwh": _r(bal.battery_in),
            "battery_out_kwh": _r(bal.battery_out),
            "expected_kwh": _r(rec.get("expected")),
            "self_consumption": _r(self_consumption(bal), 3),
            "self_sufficiency": _r(self_sufficiency(bal), 3),
            "specific_yield": _r(specific_yield(bal.pv, kwp), 2),
            "epi": _r(energy_performance_index(bal.pv, rec.get("expected", 0)), 3),
            "peak_kw": _r(rec.get("peak"), 2),
            "peak_at": rec.get("peak_at"),
            "savings": _r(gain(rec), 2),
            "export_savings": _r(rec["export"] * cfg.export_price, 2),
        },
        "yesterday": {
            "self_consumption": _r(self_consumption(ybal), 3),
            "self_sufficiency": _r(self_sufficiency(ybal), 3),
        },
        "curve": curve,
        "periods": views.periods(history, today),
        "production": {
            "strings": strings,
            "units": units,
            "epi_30d": epi_30,
            "months": month_rows,
            "month_kwh": _r(month_pv, 1),
            "month_expected": _r(sum(d.get("expected", 0) for d in month_days), 1),
        },
        "batteries": {
            "items": items,
            "fleet": asdict(fl) if fl else None,
            "autonomy_h": _r(autonomy_hours(states, load_now or 0.0), 2) if states else None,
        },
        "losses": {
            "today": {
                "potential": _r(potential),
                "clipping": _r(rec.get("clipped", 0)),
                "shading": _r(shading_today),
                "soiling": _r(soiling_today),
                "limitation": _r(limited),
                "unavailability": _r(rec.get("unavailable", 0)),
                "produced": _r(bal.pv),
            },
            "month": {k: _r(v) for k, v in month_causes.items()},
            "month_eur": _r(sum(month_causes.values()) * cfg.import_price),
            "availability": _r(availability, 4),
            "heatmap": heatmap,
            "clipping_periods": clip.periods,
            "events": loss_events,
        },
        "trends": {
            "soiling": (
                {
                    "loss": _r(soiling.loss, 4),
                    "confidence": [_r(c, 4) for c in soiling.confidence],
                    "intervals": len(soiling.intervals),
                    "days": soiling.days_used,
                }
                if soiling
                else _learning(len(clear), SOILING_DAYS)
            ),
            "degradation": (
                {
                    "rate": _r(degr.rate_pct_per_year, 2),
                    "confidence": [_r(c, 2) for c in degr.confidence],
                    "pairs": degr.pairs,
                }
                if degr
                else _learning(len(rows), DEGRADATION_DAYS)
            ),
            "shading": (
                [
                    {
                        "unit": u,
                        "start": w.start_minute,
                        "end": w.end_minute,
                        "depth": _r(w.depth, 2),
                        "kwh": _r(w.kwh_per_day, 3),
                    }
                    for u, w in shading
                ]
                if shading is not None
                else _learning(len(bin_days), MIN_CLEAR_DAYS)
            ),
        },
        "finances": {
            "today": _r(gain(rec), 2),
            "month": _r(sum(gains_by_day[k] for k in days_sorted if k.startswith(month_key)), 2),
            "year": _r(year_gain, 2),
            "since": _r(since, 2),
            "net_cost": net_cost,
            "share_paid": _r(pay.share_paid, 3) if pay else None,
            "years_to_break_even": _r(pay.years_to_break_even, 2) if pay else None,
            "gain_at_horizon": _r(pay.net_gain_at_horizon, 0) if pay else None,
            "yearly": _r(yearly, 2),
            "age_years": _r(age_years, 2),
            "breakdown": {
                "direct": _r(direct * cfg.import_price, 2),
                "battery": _r(restored * cfg.import_price, 2),
                "export": _r(exported * cfg.export_price, 2),
            },
            "monthly": [{"m": k, "eur": _r(v, 2)} for k, v in sorted(monthly_gains.items())[-12:]],
            "calendar": views.gains_calendar(gains_by_day, today),
            "bill": views.bill(history, today, cfg.import_price, cfg.export_price),
            "import_price": _r(reading.import_price, 4) if reading and reading.import_price else cfg.import_price,
            "export_price": cfg.export_price,
            "comparator": views.cached_comparator(history, cfg, inst, today),
            "inverter_replacement_cost": cfg.inverter_replacement_cost,
            "inverter_lifetime_years": cfg.inverter_lifetime_years,
        },
        "alerts": alerts,
        "sources": [asdict(s) for s in inst.sources],
        "roles": inst.roles,
        "excluded": inst.excluded,
        "ages": ages or {},
        "quality": views.quality(history.buckets + buckets[-1:], inst, now),
        "suggestions": views.suggestions(inst, kwp_estimated, items, history.buckets),
        "layout": {
            "strings": [s.name for s in inst.strings],
            "units": len(inst.units),
            "inverter": next((s.name for s in inst.sources if s.role == "pv"), None),
            "meter": next((s.name for s in inst.sources if s.role == "meter"), None),
            "forecast": next((s.name for s in inst.sources if s.role == "forecast"), None),
        },
        "reference": {
            "source": reading.reference if reading else None,
            "irradiance": inst.roles.get("irradiance"),
            "weather": inst.roles.get("weather"),
            "forecast": inst.roles.get("forecast_power"),
        },
    }
