"""What Energy Hub remembers: 5-minute buckets of the last days and one record per day.

Readings arrive every 30 seconds; their powers are integrated into the day's energies and averaged into 5-minute
buckets. The buckets feed the day's curve and the clipping detection; the daily records feed the trends (soiling,
degradation, shading, string mismatch, battery health). Everything is plain JSON for the Store.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from .const import BUCKET_SECONDS, BUCKETS_KEPT, DAYS_KEPT

# Daily 15-minute bins (actual, clear-sky kWh) are kept this many days, for the shading analysis.
BIN_DAYS_KEPT = 45
BIN_MINUTES = 15
# The same bins per string / panel, for the shading of one panel among its peers.
UNIT_BIN_DAYS_KEPT = 21
# Grid draw per half hour (48 kWh a day), for the offer comparator: a year and a little more.
IMPORT_SLOT_DAYS_KEPT = 400


@dataclass(slots=True)
class BatteryReading:
    key: str
    soc: float | None
    power_kw: float | None
    soh: float | None = None
    cycles: float | None = None
    temperature: float | None = None
    capacity_kwh: float | None = None
    cells: list[float] = field(default_factory=list)
    # Optional, when the BMS gives them: one temperature per cell, the cells being balanced, the cells per module.
    cell_temps: list[float] = field(default_factory=list)
    balancing: list[int] = field(default_factory=list)
    cells_per_module: int | None = None
    # Modules of the battery, when the integration exposes them: name, soc, voltage, temperature.
    modules: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class Reading:
    """One look at the installation: powers in kW (grid positive = import, battery positive = charging)."""

    t: float
    pv_kw: float | None = None
    load_kw: float | None = None
    grid_kw: float | None = None
    expected_kw: float | None = None
    clearsky_kw: float | None = None
    units: dict[str, float] = field(default_factory=dict)
    strings: dict[str, float] = field(default_factory=dict)
    batteries: list[BatteryReading] = field(default_factory=list)
    # Entities read without a usable value (unavailable, unknown, gone), and whether production or grid is off-line.
    stale: list[str] = field(default_factory=list)
    offline: bool = False
    # Price of the kWh drawn now (EUR, the contract's price of this half hour) and the day's Tempo / Zen Flex kind.
    import_price: float | None = None
    day_color: str | None = None
    # What the expected production was taken from: measured, forecast, weather or clearsky.
    reference: str | None = None

    @property
    def battery_kw(self) -> float:
        return sum(b.power_kw or 0.0 for b in self.batteries)


def _empty_day(day: str) -> dict[str, Any]:
    return {
        "date": day,
        "pv": 0.0,
        "expected": 0.0,
        "clearsky": 0.0,
        "import": 0.0,
        "export": 0.0,
        "load": 0.0,
        "batt_in": {},
        "batt_out": {},
        "units": {},
        "strings": {},
        "peak": 0.0,
        "peak_at": None,
        "clipped": 0.0,
        "limited": 0.0,
        "unavailable": 0.0,
        "cells_spread": {},
        "soc_min": {},
        "soc_max": {},
        "soh": {},
        "cells_v": {},
        "seconds": 0.0,
    }


@dataclass(slots=True)
class History:
    buckets: list[dict[str, Any]] = field(default_factory=list)
    days: dict[str, dict[str, Any]] = field(default_factory=dict)
    bins: dict[str, dict[str, list[float]]] = field(default_factory=dict)
    unit_bins: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)
    _open: dict[str, Any] | None = None
    _last: Reading | None = None
    # Results computed from the history and kept until it changes (not stored).
    cache: dict[str, Any] = field(default_factory=dict)

    # ---- persistence
    def to_json(self) -> dict[str, Any]:
        return {"buckets": self.buckets, "days": self.days, "bins": self.bins, "unit_bins": self.unit_bins}

    @classmethod
    def from_json(cls, data: dict[str, Any] | None) -> History:
        if not data:
            return cls()
        return cls(
            buckets=data.get("buckets", []),
            days=data.get("days", {}),
            bins=data.get("bins", {}),
            unit_bins=data.get("unit_bins", {}),
        )

    # ---- feeding
    def day(self, when: date) -> dict[str, Any]:
        key = when.isoformat()
        if key not in self.days:
            self.days[key] = _empty_day(key)
            self._trim_days()
        return self.days[key]

    def _trim_days(self) -> None:
        for key in sorted(self.days)[:-DAYS_KEPT]:
            del self.days[key]
        for key in sorted(self.bins)[:-BIN_DAYS_KEPT]:
            del self.bins[key]
        for key in sorted(self.unit_bins)[:-UNIT_BIN_DAYS_KEPT]:
            del self.unit_bins[key]
        for key in sorted(self.days)[:-IMPORT_SLOT_DAYS_KEPT]:
            self.days[key].pop("imp48", None)

    def add(self, reading: Reading, local: datetime) -> bool:
        """Integrate a reading into today's record and the open bucket; True when a bucket was closed."""
        record = self.day(local.date())
        last = self._last
        self._last = reading
        dt = reading.t - last.t if last else 0.0
        if 0 < dt <= 900:
            h = dt / 3600
            pv = _avg(last.pv_kw, reading.pv_kw)
            record["seconds"] += dt
            if pv is not None:
                record["pv"] += pv * h
            if (exp := _avg(last.expected_kw, reading.expected_kw)) is not None:
                record["expected"] += exp * h
            if (cs := _avg(last.clearsky_kw, reading.clearsky_kw)) is not None:
                record["clearsky"] += cs * h
                minute = (local.hour * 60 + local.minute) // BIN_MINUTES * BIN_MINUTES
                bin_ = self.bins.setdefault(record["date"], {}).setdefault(str(minute), [0.0, 0.0])
                bin_[0] += (pv or 0.0) * h
                bin_[1] += cs * h
                if cs > 0.05 and (reading.units or reading.strings):
                    ubin = self.unit_bins.setdefault(record["date"], {}).setdefault(str(minute), {})
                    for name, kw in (reading.units or reading.strings).items():
                        ubin[name] = ubin.get(name, 0.0) + kw * h
            price = last.import_price if last.import_price is not None else reading.import_price
            grid = _avg(last.grid_kw, reading.grid_kw)
            if grid is not None:
                record["import" if grid > 0 else "export"] += abs(grid) * h
                slots = record.setdefault("imp48", [0.0] * 48)
                if grid > 0:
                    begin = local - timedelta(seconds=dt)
                    slots[(begin.hour * 60 + begin.minute) // 30] += grid * h
            load = _avg(last.load_kw, reading.load_kw)
            if load is not None:
                record["load"] += load * h
            if price is not None:
                # Energies valued at the price of their half hour: the bill, and what self-consumption avoided.
                record["import_eur"] = record.get("import_eur", 0.0) + max(grid or 0.0, 0.0) * h * price
                if load is not None:
                    record["load_eur"] = record.get("load_eur", 0.0) + load * h * price
                if pv is not None:
                    self_kw = max(pv - max(-(grid or 0.0), 0.0), 0.0)
                    record["self_eur"] = record.get("self_eur", 0.0) + self_kw * h * price
            for name, kw in reading.units.items():
                record["units"][name] = record["units"].get(name, 0.0) + kw * h
            for name, kw in reading.strings.items():
                record["strings"][name] = record["strings"].get(name, 0.0) + kw * h
            for b in reading.batteries:
                if b.power_kw is None:
                    continue
                side = "batt_in" if b.power_kw > 0 else "batt_out"
                record[side][b.key] = record[side].get(b.key, 0.0) + abs(b.power_kw) * h
            if reading.offline and reading.expected_kw:
                record["unavailable"] += reading.expected_kw * h
        if reading.day_color:
            record["color"] = reading.day_color
        if reading.pv_kw is not None and reading.pv_kw > record["peak"]:
            record["peak"] = reading.pv_kw
            record["peak_at"] = local.isoformat()
        for b in reading.batteries:
            if b.soc is not None:
                record["soc_min"][b.key] = min(record["soc_min"].get(b.key, 101), b.soc)
                record["soc_max"][b.key] = max(record["soc_max"].get(b.key, -1), b.soc)
            if b.soh is not None:
                record["soh"][b.key] = b.soh
            if len(b.cells) > 1:
                spread = (max(b.cells) - min(b.cells)) * 1000
                record["cells_spread"][b.key] = max(record["cells_spread"].get(b.key, 0.0), spread)
                # The last voltages of the day, for each cell's 30-day curve and drift.
                record.setdefault("cells_v", {})[b.key] = [round(v, 4) for v in b.cells]
        return self._bucket(reading)

    def _bucket(self, reading: Reading) -> bool:
        start = reading.t // BUCKET_SECONDS * BUCKET_SECONDS
        closed = False
        if self._open and self._open["t"] != start:
            self.buckets.append(_close(self._open))
            del self.buckets[:-BUCKETS_KEPT]
            self._open = None
            closed = True
        if self._open is None:
            self._open = {"t": start, "n": 0, "sum": {}}
        acc = self._open
        acc["n"] += 1
        values = {
            "pv": reading.pv_kw,
            "load": reading.load_kw,
            "grid": reading.grid_kw,
            "batt": reading.battery_kw if reading.batteries else None,
            "exp": reading.expected_kw,
            "cs": reading.clearsky_kw,
        }
        socs = [b for b in reading.batteries if b.soc is not None and b.capacity_kwh]
        if socs:
            cap = sum(b.capacity_kwh for b in socs)
            values["soc"] = sum(b.soc * b.capacity_kwh for b in socs) / cap
        for b in reading.batteries:
            if b.soc is not None:
                values[f"soc:{b.key}"] = b.soc
        # Entities without a fresh value during the bucket, for the data quality of the last 24 hours.
        if reading.stale:
            acc.setdefault("stale", set()).update(reading.stale)
        for k, v in values.items():
            if v is not None:
                s = acc["sum"].setdefault(k, [0.0, 0])
                s[0] += v
                s[1] += 1
        return closed

    def today_buckets(self, day_start: float) -> list[dict[str, Any]]:
        rows = [b for b in self.buckets if b["t"] >= day_start]
        if self._open and self._open["t"] >= day_start:
            rows.append(_close(self._open))
        return rows


def _close(acc: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {"t": acc["t"]}
    for k, (total, n) in acc["sum"].items():
        row[k] = round(total / n, 4)
    if acc.get("stale"):
        row["stale"] = sorted(acc["stale"])
    return row


def _avg(a: float | None, b: float | None) -> float | None:
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return (a + b) / 2
