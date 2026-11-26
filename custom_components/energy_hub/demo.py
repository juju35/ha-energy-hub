"""Demo mode: a simulated installation, with history, so the whole panel can be tried and developed without hardware.

Two strings of 3 kWp on a south roof, an inverter clipping at 4.6 kW, string 2 lagging, panel P15 shaded
every afternoon by a chimney, soiling that builds up between rains, 0.5 %/year of degradation, three batteries of
three brands (one of 3 modules of 16 cells read by a BMS, whose cell 8 of module 2 drifts) and a Linky meter that
drops out for a quarter of an hour at night. Two large consumers: an EV charger on its own meter and
price, charging from 6:00 to 8:00 (Monday to Saturday), and a heat pump (heating in winter, hot water every
early afternoon). Every value is deterministic for a given
time, so screenshots and tests are reproducible. Names are neutral.
"""

from __future__ import annotations

import math
import random
from datetime import date, datetime, timedelta
from functools import lru_cache

from .analytics import tariffs
from .analytics.clearsky import Plane, clearsky_power
from .history import BatteryReading, ConsumerReading, History, Reading
from .sources import BatterySource, ConsumerSource, Installation, SourceInfo, UnitSource

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
MODULES = 3
CELLS_PER_MODULE = 16
DRIFTING_CELL = CELLS_PER_MODULE + 7
# The Linky meter's quarter of an hour without value, every night (data quality of the Settings tab).
METER_GAP = (3 * 60 + 10, 3 * 60 + 25)
METER = "sensor.demo_zlinky_apparent_power"
# State of health lost per year since commissioning (the house battery is the oldest and the most cycled).
SOH_PER_YEAR = {"maison": 1.25, "garage": 0.3, "balcon": 0.6}
EV_KW = 3.7
EV_PRICE = 0.1848


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
        "tariff_price": "sensor.demo_tarif_actuel_tempo_9kva_ttc",
        "tariff_color": "sensor.demo_tarif_tempo_couleur",
        "weather": "weather.demo_meteo_france",
    }
    inst.tariff = {"contract": "tempo", "kva": 9}
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
                cells=[f"sensor.demo_jk_bms_cell_{i}" for i in range(1, MODULES * CELLS_PER_MODULE + 1)]
                if key == "maison"
                else [],
                cell_temperatures=[
                    f"sensor.demo_jk_bms_temperature_{i}" for i in range(1, MODULES * CELLS_PER_MODULE + 1)
                ]
                if key == "maison"
                else [],
                cells_per_module=CELLS_PER_MODULE if key == "maison" else None,
            )
        )
    inst.suggestions = [
        {
            "kind": "attach_bms",
            "bms": "Balcon BMS",
            "bms_key": "balcon_bms",
            "battery": "Balcon",
            "battery_key": "balcon",
            "correlation": 0.97,
            "yaml": "energy_hub:\n  batteries:\n    balcon:\n      cells: sensor.demo_balcon_bms_cell_*\n",
        }
    ]
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
        SourceInfo(
            "tarif_edf",
            "Tarif EDF",
            "tarif_edf",
            "beta",
            "",
            "tariff",
            {"tariff": "provided"},
            ["sensor.demo_tarif_actuel_tempo_9kva_ttc", "sensor.demo_tarif_tempo_couleur"],
        ),
        SourceInfo(
            "weather",
            "Météo-France",
            "meteo_france",
            "core",
            "",
            "weather",
            {"clouds": "provided"},
            ["weather.demo_meteo_france"],
        ),
    ]
    inst.consumers = [
        ConsumerSource(
            "wallbox",
            "EV charger",
            "yaml",
            power="sensor.demo_wallbox_power",
            kind="ev_charger",
            import_price=EV_PRICE,
            separate_meter=True,
        ),
        ConsumerSource("heat_pump", "Heat pump", "energy", energy="sensor.demo_heat_pump_energy", kind="heat_pump"),
    ]
    inst.excluded = {"sensor.demo_zendure_ac_input": "double_count"}
    return inst


def _rng(day: date, salt: int = 0) -> random.Random:
    return random.Random(day.toordinal() * 7919 + salt)


TEMPO = tariffs.offers(9)[2]


@lru_cache(maxsize=1024)
def tempo_color(day: date) -> str:
    """The demo's Tempo colour of a day, drawn from the season's mix."""
    r = _rng(day, 5).random()
    for color, share in tariffs.expected_mix(day, "tempo").items():
        if r < share:
            return color
        r -= share
    return "blue"


def tempo_price(local: datetime) -> float:
    days = (local.date(), local.date() - timedelta(days=1))
    return TEMPO.slot_price(local.date(), local.hour * 60 + local.minute, {d.isoformat(): tempo_color(d) for d in days})


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
    """Home consumption on the main meter, kW, without the large consumers: a base of 0.31 kW and peaks at
    breakfast, lunch and dinner."""
    h = local.hour + local.minute / 60
    return (
        0.31
        + 1.2 * math.exp(-(((h - 7.6) / 0.5) ** 2))
        + 0.9 * math.exp(-(((h - 12.6) / 0.4) ** 2))
        + 1.8 * math.exp(-(((h - 19.4) / 0.7) ** 2))
        + 0.05 * math.sin(local.minute / 3)
    )


def heat_pump_now(local: datetime) -> float:
    """The heat pump, kW: heating from November to March (mornings and evenings most), hot water every day
    from 13:00 to 13:50."""
    h = local.hour + local.minute / 60
    cold = max(0.0, math.cos(2 * math.pi * (local.timetuple().tm_yday - 15) / 365) - 0.25) / 0.75
    heating = 1.5 * cold * (1.0 if 6 <= h < 9 or 17 <= h < 23 else 0.45)
    return heating + (1.1 if 13 <= h < 13 + 50 / 60 else 0.0)


def ev_now(local: datetime) -> float:
    """The EV charger, kW: from 6:00 to 8:00, Monday to Saturday."""
    return EV_KW if local.weekday() < 6 and 6 <= local.hour < 8 else 0.0


DEMO_EPOCH = date(2026, 1, 1)
CHARGE_KW = {"maison": 2.5, "garage": 0.6, "balcon": 0.8}


def cells_at(day: date) -> list[float]:
    """Cell voltages of the house battery: cell 8 of module 2 drifts 0.9 mV a day, over cycles of 40 days."""
    k = (day - DEMO_EPOCH).days % 40
    return [
        round(3.333 + (((i * 31) % 11) - 5) * 0.0012 - (0.0009 * k if i == DRIFTING_CELL else 0), 4)
        for i in range(MODULES * CELLS_PER_MODULE)
    ]


def cell_temps_at(local: datetime, power_kw: float) -> list[float]:
    """Cell temperatures: warmer in the middle of each module and while the battery works."""
    work = min(abs(power_kw), 3.0)
    return [
        round(
            20.5
            + 1.6 * math.sin(math.pi * (i % CELLS_PER_MODULE) / (CELLS_PER_MODULE - 1))
            + 0.8 * work
            + 0.3 * (i // CELLS_PER_MODULE),
            1,
        )
        for i in range(MODULES * CELLS_PER_MODULE)
    ]


def soh_at(key: str, day: date) -> float:
    return round(100 - SOH_PER_YEAR[key] * (day - COMMISSIONED).days / 365, 1)


class DemoPlant:
    """The simulated installation, stepped forward in time: the batteries keep their charge from step to step."""

    def __init__(self, lat: float, lon: float) -> None:
        self.lat = lat
        self.lon = lon
        self.soc = {"maison": 55.0, "garage": 50.0, "balcon": 70.0}

    def step(self, local: datetime, seconds: float) -> Reading:
        """The installation at ``local``, after ``seconds`` since the previous step."""
        pv, panels, strings, cs, _clipped = units_now(local, self.lat, self.lon)
        ev = ev_now(local)
        hp = heat_pump_now(local)
        # The main meter's consumption: the EV charger is on a meter of its own.
        load = load_now(local) + hp
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
        batteries = []
        for key in self.soc:
            reading = BatteryReading(
                key,
                round(self.soc[key], 1),
                round(power[key], 3),
                soh=soh_at(key, local.date()),
                cycles={"maison": 380.0, "garage": 120.0, "balcon": 210.0}[key],
                temperature={"maison": 21.0, "garage": 24.0, "balcon": 19.0}[key],
                capacity_kwh=caps[key],
            )
            if key == "maison":
                cells = cells_at(local.date())
                mean = sum(cells) / len(cells)
                reading.cells = cells
                reading.cell_temps = cell_temps_at(local, power[key])
                reading.cells_per_module = CELLS_PER_MODULE
                # The BMS balances the highest cells near the top of the charge.
                reading.balancing = [i for i, v in enumerate(cells) if self.soc[key] > 90 and v > mean + 0.0055]
                reading.modules = [
                    {
                        "name": f"Module {m + 1}",
                        "soc": round(min(100.0, self.soc[key] + (m - 1) * 0.6), 1),
                        "voltage": round(sum(cells[m * CELLS_PER_MODULE : (m + 1) * CELLS_PER_MODULE]), 2),
                        "temperature": round(21.0 + 0.4 * m + 0.8 * min(abs(power[key]), 3.0), 1),
                    }
                    for m in range(MODULES)
                ]
            batteries.append(reading)
        batt = sum(power.values())
        export = pv - load - batt
        if export > EXPORT_LIMIT_KW:
            # The grid connection takes 4.5 kW at most: the inverter limits its output.
            cut = (export - EXPORT_LIMIT_KW) / pv
            pv *= 1 - cut
            strings = {k: v * (1 - cut) for k, v in strings.items()}
            panels = {k: v * (1 - cut) for k, v in panels.items()}
        minute = local.hour * 60 + local.minute
        meter_out = METER_GAP[0] <= minute < METER_GAP[1]
        return Reading(
            t=local.timestamp(),
            pv_kw=round(pv, 3),
            load_kw=round(load + ev, 3),
            grid_kw=None if meter_out else round(load + batt - pv, 3),
            stale=[METER] if meter_out else [],
            expected_kw=round(cs * min(weather(local.date()) + 0.04, 1.0), 3),
            clearsky_kw=round(cs, 3),
            units={k: round(v, 4) for k, v in panels.items()},
            strings={k: round(v, 4) for k, v in strings.items()},
            batteries=batteries,
            consumers={
                "wallbox": ConsumerReading(round(ev, 3), EV_PRICE, separate_meter=True),
                "heat_pump": ConsumerReading(round(hp, 3)),
            },
            import_price=tempo_price(local),
            day_color=tempo_color(local.date()) if local.hour >= 6 else None,
            reference="forecast",
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
    # An inverter outage twelve days ago, back since: a resolved event of the Losses tab.
    outage = history.day((now - timedelta(days=12)).date())
    outage["unavailable"] = outage.get("unavailable", 0.0) + 1.6
    # The old days were integrated at 15 minutes: keep only the recent days' buckets.
    history.buckets = [b for b in history.buckets if b["t"] >= recent.timestamp()]
    return plant
