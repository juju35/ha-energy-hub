"""Demo mode: a simulated installation, with history, so the whole panel can be tried and developed without hardware.

Two strings of 3 kWp on a south roof, an inverter clipping at 4.6 kW, string 2 lagging, panel P15 shaded
every afternoon by a chimney, soiling that builds up between rains, 0.5 %/year of degradation, three batteries of
three brands (one with a 16-cell BMS whose cell 8 drifts) and a Linky meter. Every value is deterministic for a given
time, so screenshots and tests are reproducible. Names are neutral.
"""

from __future__ import annotations

import math
import random
from datetime import date, datetime, timedelta
from functools import lru_cache

from .analytics.clearsky import Plane, clearsky_power
from .history import BatteryReading, History, Reading
from .sources import BatterySource, Installation, SourceInfo, UnitSource

# Two strings of 8 panels on the same south roof: strings and panels can then be compared with each other.
PLANES = [Plane(3.28, 30, 190), Plane(3.28, 30, 190)]
INVERTER_MAX_KW = 4.2
EXPORT_LIMIT_KW = 4.5
COMMISSIONED = date(2023, 4, 12)
STRING2_FACTOR = 0.84
SHADE_START, SHADE_END = 15 * 60 + 30, 16 * 60 + 10
BATTERIES = (
    ("maison", "Maison", "huawei_solar", 15.0),
    ("garage", "Garage", "zendure_ha", 2.88),
    ("balcon", "Balcon", "marstek_local_api", 5.12),
)
PANELS = 16


def installation() -> Installation:
    """The demo installation as the Settings tab lists it."""
    inst = Installation()
    inst.roles = {
        "pv_power": "sensor.demo_inverter_input_power",
        "pv_energy": "sensor.demo_inverter_total_yield",
        "grid_power": "sensor.demo_zlinky_apparent_power",
        "grid_import_energy": "sensor.demo_zlinky_summation_delivered",
        "grid_export_energy": "sensor.demo_zlinky_summation_received",
        "forecast_power": "sensor.demo_solcast_power_now",
    }
    inst.strings = [
        UnitSource("String 1", "sensor.demo_pv_01_power"),
        UnitSource("String 2", "sensor.demo_pv_02_power"),
    ]
    inst.units = [UnitSource(f"P{i + 1}", f"sensor.demo_optimizer_{i + 1}_output_power") for i in range(PANELS)]
    for key, name, platform, cap in BATTERIES:
        inst.batteries.append(
            BatterySource(
                key=key,
                name=name,
                platform=platform,
                soc=f"sensor.demo_{key}_soc",
                power=f"sensor.demo_{key}_power",
                capacity_kwh=cap,
                cells=[f"sensor.demo_jk_bms_cell_{i}" for i in range(1, 17)] if key == "maison" else [],
            )
        )
    inst.sources = [
        SourceInfo(
            "huawei_solar",
            "Huawei Solar",
            "huawei_solar",
            "beta",
            "",
            "pv",
            {
                "strings": "provided",
                "optimizers": "provided",
                "pmax": "provided",
                "export_limit": "provided",
                "soc": "provided",
                "soh": "estimated",
                "cycles": "estimated",
                "modules": "provided",
                "cells": "absent",
            },
            ["sensor.demo_inverter_input_power", "sensor.demo_maison_soc"],
        ),
        SourceInfo(
            "zendure_ha",
            "Zendure",
            "zendure_ha",
            "beta",
            "",
            "storage",
            {"soc": "provided", "soh": "provided", "cycles": "provided"},
            ["sensor.demo_garage_soc"],
        ),
        SourceInfo(
            "marstek_local_api",
            "Marstek Local API",
            "marstek_local_api",
            "beta",
            "",
            "storage",
            {"soc": "provided", "soh": "estimated", "cycles": "estimated"},
            ["sensor.demo_balcon_soc"],
        ),
        SourceInfo(
            "bms_ble",
            "BLE Battery Management",
            "bms_ble",
            "beta",
            "",
            "storage",
            {"cells": "provided", "cycles": "provided"},
            ["sensor.demo_jk_bms_delta_voltage"],
        ),
        SourceInfo(
            "zha_zlinky",
            "ZLinky (ZHA)",
            "zha",
            "beta",
            "",
            "meter",
            {"tempo": "provided"},
            ["sensor.demo_zlinky_apparent_power"],
        ),
        SourceInfo(
            "solcast_solar",
            "Solcast PV Forecast",
            "solcast_solar",
            "beta",
            "",
            "forecast",
            {"forecast": "provided"},
            ["sensor.demo_solcast_power_now"],
        ),
    ]
    inst.excluded = {"sensor.demo_zendure_ac_input": "double_count"}
    return inst


def _rng(day: date, salt: int = 0) -> random.Random:
    return random.Random(day.toordinal() * 7919 + salt)


@lru_cache(maxsize=1024)
def weather(day: date) -> float:
    """Share of the clear sky reaching the panels that day (1 = clear): mostly clear in summer, grey in winter."""
    season = 0.5 + 0.5 * math.cos(2 * math.pi * (day.timetuple().tm_yday - 172) / 365)
    r = _rng(day).random()
    if r < 0.25 + 0.35 * season:
        return 0.95 + 0.05 * _rng(day, 1).random()
    if r < 0.55 + 0.25 * season:
        return 0.6 + 0.3 * _rng(day, 2).random()
    return 0.15 + 0.35 * _rng(day, 3).random()


@lru_cache(maxsize=1024)
def rain(day: date) -> float:
    """Rain of the day, mm: a soiling reset when over 1 mm."""
    w = weather(day)
    return 6.0 * _rng(day, 4).random() if w < 0.4 and _rng(day, 5).random() < 0.7 else 0.0


@lru_cache(maxsize=1024)
def soiling(day: date) -> float:
    """Soiling factor (1 = clean): -0.3 %/day since the last rain, capped at 10 %."""
    days = 0
    d = day
    while days < 60 and rain(d) < 1.0:
        days += 1
        d -= timedelta(days=1)
    return max(1 - 0.003 * days, 0.9)


@lru_cache(maxsize=1024)
def degradation(day: date) -> float:
    return 1 - 0.005 * (day - COMMISSIONED).days / 365


def units_now(
    local: datetime, lat: float, lon: float
) -> tuple[float, dict[str, float], dict[str, float], float, float]:
    """PV power, panels' power, strings' power (kW), the clear-sky power and the power lost to clipping."""
    day = local.date()
    cs = clearsky_power(local, lat, lon, PLANES)
    w = weather(day)
    # Clouds pass: a slow wave on cloudy days.
    minute = local.hour * 60 + local.minute
    sky = w if w > 0.9 else max(0.05, w + 0.25 * math.sin(minute / 23.0 + day.toordinal()))
    factor = sky * soiling(day) * degradation(day)
    per_plane = [clearsky_power(local, lat, lon, [p]) * factor for p in PLANES]
    panels: dict[str, float] = {}
    for i in range(PANELS):
        plane = per_plane[0] if i < 8 else per_plane[1] * STRING2_FACTOR
        share = plane / 8 * (1 - 0.01 * ((i * 37) % 5))
        if i == 14 and SHADE_START <= minute < SHADE_END:
            share *= 0.25
        panels[f"P{i + 1}"] = max(share, 0.0)
    strings = {"String 1": sum(list(panels.values())[:8]), "String 2": sum(list(panels.values())[8:])}
    raw = sum(strings.values())
    pv = min(raw, INVERTER_MAX_KW)
    scale = pv / raw if raw > 0 else 0
    strings = {k: v * scale for k, v in strings.items()}
    panels = {k: v * scale for k, v in panels.items()}
    return pv, panels, strings, cs, raw - pv


def load_now(local: datetime) -> float:
    """Home consumption, kW: a base of 0.31 kW and peaks at breakfast, lunch and dinner."""
    h = local.hour + local.minute / 60
    return (
        0.31
        + 1.2 * math.exp(-(((h - 7.6) / 0.5) ** 2))
        + 0.9 * math.exp(-(((h - 12.6) / 0.4) ** 2))
        + 1.8 * math.exp(-(((h - 19.4) / 0.7) ** 2))
        + 0.05 * math.sin(local.minute / 3)
    )


DEMO_EPOCH = date(2026, 1, 1)
CHARGE_KW = {"maison": 2.5, "garage": 0.6, "balcon": 0.8}


def cells_at(day: date) -> list[float]:
    """Cell voltages of the house battery: cell 8 drifts 0.9 mV a day, over cycles of 40 days."""
    k = (day - DEMO_EPOCH).days % 40
    return [round(3.333 + (((i * 31) % 11) - 5) * 0.0012 - (0.0009 * k if i == 7 else 0), 4) for i in range(16)]


class DemoPlant:
    """The simulated installation, stepped forward in time: the batteries keep their charge from step to step."""

    def __init__(self, lat: float, lon: float) -> None:
        self.lat = lat
        self.lon = lon
        self.soc = {"maison": 55.0, "garage": 50.0, "balcon": 70.0}

    def step(self, local: datetime, seconds: float) -> Reading:
        """The installation at ``local``, after ``seconds`` since the previous step."""
        pv, panels, strings, cs, _clipped = units_now(local, self.lat, self.lon)
        load = load_now(local)
        h = local.hour + local.minute / 60
        power = dict.fromkeys(self.soc, 0.0)
        caps = {key: cap for key, _n, _p, cap in BATTERIES}
        if 16 <= h < 17:
            # The garage battery feeds the house while the house battery charges: an exchange, reported as a loss.
            power["garage"] = -0.3 if self.soc["garage"] > 15 else 0.0
        surplus = pv - load - power["garage"]
        order = ("maison", "balcon", "garage")
        for key in order:
            if key == "garage" and 16 <= h < 17:
                continue
            room = (100 - self.soc[key]) / 100 * caps[key] * 3600 / max(seconds, 1)
            usable = (self.soc[key] - 10) / 100 * caps[key] * 3600 / max(seconds, 1)
            if surplus > 0:
                p = min(surplus, CHARGE_KW[key], max(room, 0))
            else:
                p = -min(-surplus, CHARGE_KW[key], max(usable, 0))
            power[key] = p
            surplus -= p
        for key, p in power.items():
            eff = 0.97 if p > 0 else 1 / 0.97
            self.soc[key] = max(0.0, min(100.0, self.soc[key] + p * eff * seconds / 3600 / caps[key] * 100))
        batteries = [
            BatteryReading(
                key,
                round(self.soc[key], 1),
                round(power[key], 3),
                soh={"maison": 96.0, "garage": 99.0, "balcon": 98.0}[key],
                cycles={"maison": 380.0, "garage": 120.0, "balcon": 210.0}[key],
                temperature={"maison": 21.0, "garage": 24.0, "balcon": 19.0}[key],
                capacity_kwh=caps[key],
                cells=cells_at(local.date()) if key == "maison" else [],
            )
            for key in self.soc
        ]
        batt = sum(power.values())
        export = pv - load - batt
        if export > EXPORT_LIMIT_KW:
            # The grid connection takes 4.5 kW at most: the inverter limits its output.
            cut = (export - EXPORT_LIMIT_KW) / pv
            pv *= 1 - cut
            strings = {k: v * (1 - cut) for k, v in strings.items()}
            panels = {k: v * (1 - cut) for k, v in panels.items()}
        return Reading(
            t=local.timestamp(),
            pv_kw=round(pv, 3),
            load_kw=round(load, 3),
            grid_kw=round(load + batt - pv, 3),
            expected_kw=round(cs * min(weather(local.date()) + 0.04, 1.0), 3),
            clearsky_kw=round(cs, 3),
            units={k: round(v, 4) for k, v in panels.items()},
            strings={k: round(v, 4) for k, v in strings.items()},
            batteries=batteries,
        )


def backfill(history: History, now: datetime, lat: float, lon: float, days: int = 420) -> DemoPlant:
    """Fill the history with ``days`` simulated days before ``now``, and today up to ``now`` (15-minute steps for
    the old days, 1-minute steps for the last two days and today)."""
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    plant = DemoPlant(lat, lon)
    t = start
    recent = (now - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
    while t <= now:
        step = timedelta(minutes=1) if t >= recent else timedelta(minutes=15)
        history.add(plant.step(t, step.total_seconds()), t)
        record = history.day(t.date())
        record["rain"] = rain(t.date())
        if t < recent:
            lost = units_now(t, lat, lon)[4] * step.total_seconds() / 3600
            if lost > 0:
                record["clipped"] += lost
                clip_h = record.setdefault("clip_h", [0.0] * 24)
                clip_h[t.hour] += lost
        t += step
    # The old days were integrated at 15 minutes: keep only the recent days' buckets.
    history.buckets = [b for b in history.buckets if b["t"] >= recent.timestamp()]
    return plant
