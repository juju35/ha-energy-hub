"""The parts of the snapshot that only reshape the history for a screen of the panel: period charts, a battery's
charge and health over time, the cells' history, the loss events and their status, the gains calendar, the bill
with and without solar, the data quality of the last 24 hours, the DC/AC layout and the attachment suggestions.

Everything here reads the History and the Installation; nothing is persisted.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from .analytics import tariffs, theil_sen
from .config import HubConfig
from .history import BatteryReading, History, Reading
from .sources import Installation

# Platforms whose battery sits on the inverter's DC bus (hybrid inverters); the others are AC-coupled.
DC_COUPLED_PLATFORMS = {
    "huawei_solar",
    "solaredge",
    "solaredge_modbus_multi",
    "fronius",
    "sma",
    "solax_modbus",
    "solarman",
    "victron",
}
# A loss seen on this many of the last 7 days is recurring; one not seen for this many days is resolved.
RECURRING_DAYS = 3
RESOLVED_AFTER_DAYS = 3
# A cell whose deviation moves faster than this is drifting (mV per day).
CELL_DRIFT_MV_PER_DAY = 0.3
QUALITY_SLOTS = 96


def _r(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


# ---- periods of the overview chart
def consumers(inst: Installation, record: dict[str, Any], reading: Reading | None) -> list[dict[str, Any]]:
    """The large consumers: now, and today's energy, solar share and cost."""
    days = record.get("consumers") or {}
    out = []
    for c in inst.consumers:
        kwh, solar, eur = days.get(c.key, (0.0, 0.0, 0.0))
        now = reading.consumers.get(c.key) if reading else None
        out.append(
            {
                "key": c.key,
                "name": c.name,
                "kind": c.kind,
                "kw": _r(now.kw, 3) if now else None,
                "kwh": _r(kwh),
                "solar_share": _r(solar / kwh, 3) if kwh > 0.01 else None,
                "eur": _r(eur),
                "import_price": c.import_price,
                "separate_meter": c.separate_meter,
                "power": c.power,
                "energy": c.energy,
            }
        )
    return out


def periods(history: History, today: date) -> dict[str, list[dict[str, Any]]]:
    """Daily rows of the last 7 and 30 days, and monthly rows of the last 12 months (kWh)."""
    keys = sorted(k for k in history.days if k <= today.isoformat())

    def row(key: str, d: dict[str, Any]) -> dict[str, Any]:
        cons = {k: _r(v[0], 2) for k, v in (d.get("consumers") or {}).items()}
        return {
            **({"c": cons} if cons else {}),
            "d": key,
            "pv": _r(d["pv"], 2),
            "exp": _r(d.get("expected"), 2),
            "load": _r(d.get("load"), 2),
            "import": _r(d.get("import"), 2),
            "export": _r(d.get("export"), 2),
            "clipped": _r(d.get("clipped", 0), 2),
        }

    months: dict[str, dict[str, float]] = {}
    month_c: dict[str, dict[str, float]] = {}
    for key in keys:
        d = history.days[key]
        m = months.setdefault(
            key[:7], {"pv": 0.0, "exp": 0.0, "load": 0.0, "import": 0.0, "export": 0.0, "clipped": 0.0}
        )
        m["pv"] += d["pv"]
        m["exp"] += d.get("expected", 0.0)
        m["load"] += d.get("load", 0.0)
        m["import"] += d.get("import", 0.0)
        m["export"] += d.get("export", 0.0)
        m["clipped"] += d.get("clipped", 0.0)
        for k, v in (d.get("consumers") or {}).items():
            month_cons = month_c.setdefault(key[:7], {})
            month_cons[k] = month_cons.get(k, 0.0) + v[0]
    return {
        "7d": [row(k, history.days[k]) for k in keys[-7:]],
        "30d": [row(k, history.days[k]) for k in keys[-30:]],
        "12m": [
            {
                "d": k,
                **{kk: _r(v, 1) for kk, v in m.items()},
                **({"c": {kk: _r(v, 1) for kk, v in month_c[k].items()}} if k in month_c else {}),
            }
            for k, m in sorted(months.items())[-12:]
        ],
    }


# ---- one battery over time
def soc_today(buckets: list[dict[str, Any]], key: str) -> list[list[float]]:
    return [[b["t"], b[f"soc:{key}"]] for b in buckets if b.get(f"soc:{key}") is not None]


def soc_projection(
    now: datetime, soc: float | None, power_kw: float | None, capacity_kwh: float, reserve: float
) -> list[list[float]]:
    """The charge until midnight at the current power, stopped at full or at the reserve (15-minute points)."""
    if soc is None or not power_kw or abs(power_kw) < 0.05 or capacity_kwh <= 0:
        return []
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    per_hour = power_kw / capacity_kwh * 100
    points = [[now.timestamp(), soc]]
    t, level = now, soc
    while t < midnight:
        t += timedelta(minutes=15)
        level += per_hour / 4
        if level >= 100 or level <= reserve:
            points.append([t.timestamp(), 100.0 if level >= 100 else reserve])
            break
        points.append([t.timestamp(), round(level, 1)])
    return points


def soh_trend(history: History, key: str, today: date, years: int = 3) -> dict[str, Any] | None:
    """Weekly state of health over the last ``years`` years and its Theil-Sen projection ``years`` years ahead."""
    start = (today - timedelta(days=365 * years)).isoformat()
    rows = [(k, d["soh"][key]) for k, d in sorted(history.days.items()) if k >= start and key in d.get("soh", {})]
    if len(rows) < 14:
        return None
    weekly = rows[::7]
    if weekly[-1] != rows[-1]:
        weekly.append(rows[-1])
    xs = [date.fromisoformat(k).toordinal() for k, _v in weekly]
    slope, intercept = theil_sen(xs, [v for _k, v in weekly])
    end = today + timedelta(days=365 * years)
    return {
        "points": [[k, _r(v, 1)] for k, v in weekly],
        "per_year": _r(slope * 365, 2),
        "projected": [end.isoformat(), _r(slope * end.toordinal() + intercept, 1)],
    }


def cells_detail(history: History, b: BatteryReading, today: date) -> dict[str, Any]:
    """Temperatures, balancing, modules layout, and each cell's deviation over 30 days with its drift (mV/day)."""
    keys = [k for k in sorted(history.days)[-30:] if b.key in history.days[k].get("cells_v", {})]
    series: list[list[float]] = []
    dates: list[str] = []
    for k in keys:
        volts = history.days[k]["cells_v"][b.key]
        if len(volts) != len(b.cells):
            continue
        mean = sum(volts) / len(volts)
        dates.append(k)
        series.append([round((v - mean) * 1000, 1) for v in volts])
    by_cell = [[day[i] for day in series] for i in range(len(b.cells))] if series else []
    drift: list[float | None] = []
    for values in by_cell:
        if len(values) >= 7:
            xs = [float(i) for i in range(len(values))]
            drift.append(_r(theil_sen(xs, values)[0], 2))
        else:
            drift.append(None)
    return {
        "temps": b.cell_temps if len(b.cell_temps) == len(b.cells) else [],
        "balancing": b.balancing,
        "per_module": b.cells_per_module if b.cells_per_module and len(b.cells) % b.cells_per_module == 0 else None,
        "history_dates": dates,
        "history": by_cell,
        "drift_mv_day": drift,
        "drifting": [i for i, s in enumerate(drift) if s is not None and abs(s) >= CELL_DRIFT_MV_PER_DAY],
    }


# ---- loss events
def _status(dates: list[str], today: date) -> str:
    if not dates:
        return "resolved"
    last = date.fromisoformat(max(dates))
    if (today - last).days >= RESOLVED_AFTER_DAYS:
        return "resolved"
    recent = [d for d in dates if (today - date.fromisoformat(d)).days < 7]
    return "recurring" if len(recent) >= RECURRING_DAYS else "watch"


def events(
    history: History,
    today: date,
    *,
    clipping_kwh: float,
    strings: list[dict[str, Any]],
    shading: list[tuple[str | None, Any]] | None,
    soiling_loss: float | None,
    soiling_alert: float,
    cell_alerts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """The losses of the last 30 days as events: what, since when, how often, how much, and a status — recurring
    (seen on 3 of the last 7 days or more), to watch (seen lately, not yet recurring) or resolved (not seen for 3
    days)."""
    keys = sorted(history.days)[-30:]
    out: list[dict[str, Any]] = []
    clip_days = [k for k in keys if history.days[k].get("clipped", 0) >= clipping_kwh]
    if clip_days:
        out.append(
            {
                "kind": "clipping",
                "status": _status(clip_days, today),
                "first": clip_days[0],
                "last": clip_days[-1],
                "days": len(clip_days),
                "kwh": _r(sum(history.days[k]["clipped"] for k in clip_days), 2),
            }
        )
    off_days = [k for k in keys if history.days[k].get("unavailable", 0) >= 0.05]
    if off_days:
        out.append(
            {
                "kind": "unavailability",
                "status": _status(off_days, today),
                "first": off_days[0],
                "last": off_days[-1],
                "days": len(off_days),
                "kwh": _r(sum(history.days[k]["unavailable"] for k in off_days), 2),
            }
        )
    for unit, w in shading or []:
        first = min(history.unit_bins or history.bins or {today.isoformat(): None})
        out.append(
            {
                "kind": "shading",
                "status": "recurring",
                "unit": unit,
                "start": w.start_minute,
                "end": w.end_minute,
                "first": first,
                "last": today.isoformat(),
                "kwh": _r(w.kwh_per_day * len(keys), 2),
            }
        )
    out.extend(
        {
            "kind": "string_lagging",
            "status": "recurring" if s["lagging_days"] >= 7 else "watch",
            "name": s["name"],
            "relative": s.get("relative"),
            "days": s["lagging_days"],
            "first": (today - timedelta(days=s["lagging_days"] - 1)).isoformat(),
            "last": today.isoformat(),
        }
        for s in strings
        if s.get("lagging_days", 0) >= RECURRING_DAYS
    )
    if soiling_loss is not None and soiling_loss >= soiling_alert:
        out.append({"kind": "soiling", "status": "watch", "loss": _r(soiling_loss, 3), "last": today.isoformat()})
    out.extend({**a, "status": "watch", "last": today.isoformat()} for a in cell_alerts)
    order = {"recurring": 0, "watch": 1, "resolved": 2}
    return sorted(out, key=lambda e: order[e["status"]])


# ---- finances
def gains_calendar(gains_by_day: dict[str, float], today: date, weeks: int = 6) -> list[dict[str, Any]]:
    """The gains of each day of the last ``weeks`` weeks, starting on a Monday, for the calendar."""
    start = today - timedelta(days=today.weekday() + 7 * (weeks - 1))
    return [
        {
            "d": (start + timedelta(days=i)).isoformat(),
            "eur": _r(gains_by_day.get((start + timedelta(days=i)).isoformat()), 2),
        }
        for i in range((today - start).days + 1)
    ]


def bill(history: History, today: date, import_price: float, export_price: float) -> dict[str, Any]:
    """What the electricity cost this month and over 12 months, with the solar installation and without it."""

    def period(keys: list[str]) -> dict[str, float | None]:
        recs = [history.days[k] for k in keys]
        # A day valued at its half hours' prices (import_eur / load_eur) when they were known, else the flat price.
        with_solar = (
            sum(d.get("import_eur", d.get("import", 0) * import_price) for d in recs)
            - sum(d.get("export", 0) for d in recs) * export_price
        )
        without = sum(d.get("load_eur", d.get("load", 0) * import_price) for d in recs)
        return {"with": _r(with_solar, 2), "without": _r(without, 2)}

    keys = sorted(history.days)
    return {"month": period([k for k in keys if k.startswith(today.isoformat()[:7])]), "year": period(keys[-365:])}


# ---- data quality
def quality(buckets: list[dict[str, Any]], inst: Installation, now: datetime) -> list[dict[str, Any]]:
    """For each entity in use, the share of the last 24 hours with a usable value, in 96 quarter-hour slots
    (1 = every reading usable, 0 = none), and the gaps."""
    start = now.timestamp() - 86400
    rows = [b for b in buckets if b["t"] >= start]
    ids: list[tuple[str, str]] = [(role, e) for role, e in sorted(inst.roles.items())]
    for b in inst.batteries:
        ids += [(f"{b.key}.soc", b.soc), (f"{b.key}.power", b.power)] if b.soc and b.power else []
        if b.soc and b.charge_power and b.discharge_power:
            ids += [(f"{b.key}.soc", b.soc), (f"{b.key}.charge_power", b.charge_power)]
            ids += [(f"{b.key}.discharge_power", b.discharge_power)]
    out = []
    slot_len = 86400 / QUALITY_SLOTS
    for role, entity_id in ids:
        if not entity_id:
            continue
        slots = [[0, 0] for _ in range(QUALITY_SLOTS)]
        gaps: list[list[float]] = []
        for b in rows:
            i = min(int((b["t"] - start) // slot_len), QUALITY_SLOTS - 1)
            bad = entity_id in b.get("stale", ())
            slots[i][0] += 0 if bad else 1
            slots[i][1] += 1
            if bad:
                if gaps and b["t"] - gaps[-1][1] <= 300:
                    gaps[-1][1] = b["t"] + 300
                else:
                    gaps.append([b["t"], b["t"] + 300])
        seen = [ok / n for ok, n in slots if n]
        out.append(
            {
                "role": role,
                "entity": entity_id,
                "share": _r(sum(seen) / len(seen), 4) if seen else None,
                "slots": [_r(ok / n, 2) if n else None for ok, n in slots],
                "gaps": gaps,
            }
        )
    return out


# ---- layout and suggestions
def coupling(platform: str) -> str:
    return "dc" if platform in DC_COUPLED_PLATFORMS else "ac"


def correlation(buckets: list[dict[str, Any]], a: str, b: str) -> float | None:
    """Pearson correlation of two batteries' charge over the buckets kept (None under 12 common points)."""
    pairs = [
        (r[f"soc:{a}"], r[f"soc:{b}"])
        for r in buckets
        if r.get(f"soc:{a}") is not None and r.get(f"soc:{b}") is not None
    ]
    if len(pairs) < 12:
        return None
    n = len(pairs)
    mx = sum(x for x, _y in pairs) / n
    my = sum(y for _x, y in pairs) / n
    sxy = sum((x - mx) * (y - my) for x, y in pairs)
    sxx = sum((x - mx) ** 2 for x, _y in pairs)
    syy = sum((y - my) ** 2 for _x, y in pairs)
    return _r(sxy / (sxx * syy) ** 0.5, 2) if sxx > 0 and syy > 0 else None


def suggestions(
    inst: Installation, kwp_estimated: bool, items: list[dict[str, Any]], buckets: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """What would make the hub more accurate, each with the YAML that does it."""
    out = [
        {**s, "correlation": correlation(buckets, s["bms_key"], s["battery_key"])}
        if s.get("kind") == "attach_bms" and "correlation" not in s
        else s
        for s in inst.suggestions
    ]
    if kwp_estimated:
        out.append(
            {"kind": "planes", "yaml": "energy_hub:\n  planes:\n    - kwp: 3.0\n      tilt: 30\n      azimuth: 180\n"}
        )
    out.extend(
        {
            "kind": "capacity",
            "battery": item["name"],
            "yaml": f"energy_hub:\n  batteries:\n    {item['key']}:\n      capacity_kwh: 5\n",
        }
        for item in items
        if item.get("capacity_estimated")
    )
    if not inst.roles.get("forecast_power"):
        out.append(
            {"kind": "forecast", "yaml": "energy_hub:\n  entities:\n    forecast_power: sensor.power_production_now\n"}
        )
    return out


# ---- contract and offer comparator
COMPARATOR_MIN_DAYS = 14
DEFAULT_KVA = 6


def contract(cfg: HubConfig, inst: Installation) -> dict[str, Any]:
    """The contract as known: from the YAML, else from Tarif EDF, with what had to be assumed."""
    detected = inst.tariff
    return {
        "contract": cfg.contract or detected.get("contract"),
        "contract_source": "yaml" if cfg.contract else "tarif_edf" if detected.get("contract") else None,
        "kva": cfg.kva or detected.get("kva") or DEFAULT_KVA,
        "kva_assumed": not (cfg.kva or detected.get("kva")),
        "offpeak": cfg.offpeak or "22:00-06:00",
        "offpeak_assumed": cfg.offpeak is None,
    }


def offer_list(cfg: HubConfig, inst: Installation) -> list[tariffs.Offer]:
    c = contract(cfg, inst)
    return tariffs.offers(c["kva"], tariffs.parse_ranges(c["offpeak"]), cfg.offers)


def contract_offer(cfg: HubConfig, inst: Installation) -> tariffs.Offer | None:
    key = contract(cfg, inst)["contract"]
    return next((o for o in offer_list(cfg, inst) if o.key == key), None)


def comparator(history: History, cfg: HubConfig, inst: Installation, today: date) -> dict[str, Any]:
    """Yearly cost of the last 12 months' grid draw under each offer, the current contract marked."""
    c = contract(cfg, inst)
    keys = [k for k in sorted(history.days) if k < today.isoformat()][-365:]
    days = [(date.fromisoformat(k), history.days[k]["imp48"]) for k in keys if "imp48" in history.days[k]]
    colors = {k: d["color"] for k, d in history.days.items() if d.get("color")}
    grid_age = (today - date.fromisoformat(tariffs.GRID_DATE)).days
    base = {
        **c,
        "days": len(days),
        "needed": COMPARATOR_MIN_DAYS,
        "colors": sum(1 for day, _ in days if day.isoformat() in colors),
        "grid_date": tariffs.GRID_DATE,
        "grid_stale": grid_age > tariffs.GRID_STALE_MONTHS * 30.5,
        "sources": tariffs.GRID_SOURCES,
        "offers": [],
    }
    if len(days) < COMPARATOR_MIN_DAYS:
        return base
    result, scale = tariffs.compare(days, offer_list(cfg, inst), colors)
    current = next((r for r in result if r.key == c["contract"]), None)
    kwh = sum(sum(slots) for _, slots in days) * scale
    base.update(
        {
            "scale": _r(scale, 3),
            "kwh": _r(kwh, 0),
            "current": current.key if current else None,
            "best": result[0].key,
            "saving": _r(current.total_eur - result[0].total_eur, 0) if current else None,
            "offers": [
                {
                    "key": r.key,
                    "name": r.name,
                    "regulated": r.regulated,
                    "custom": r.custom,
                    "energy": _r(r.energy_eur, 0),
                    "subscription": _r(r.subscription_eur, 0),
                    "total": _r(r.total_eur, 0),
                    "avg_price": _r(r.energy_eur / kwh, 4) if kwh else None,
                    "delta": _r(r.total_eur - current.total_eur, 0) if current else None,
                }
                for r in result
            ],
        }
    )
    return base


def cached_comparator(history: History, cfg: HubConfig, inst: Installation, today: date) -> dict[str, Any]:
    """The comparator once a day (a year of half hours under each offer is too much for every 30 s refresh)."""
    key = (today.isoformat(), repr(contract(cfg, inst)), repr(cfg.offers), len(history.days))
    if history.cache.get("comparator_key") != key:
        history.cache["comparator"] = comparator(history, cfg, inst, today)
        history.cache["comparator_key"] = key
    return history.cache["comparator"]
