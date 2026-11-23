"""Reads the source entities every 30 seconds, keeps the history and builds the panel's snapshot."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from . import demo
from .analytics.clearsky import Plane, clearsky_power
from .config import HubConfig
from .const import DOMAIN, EVENT_ALERT, STALE_SECONDS, STORAGE_KEY, STORAGE_VERSION, UPDATE_SECONDS
from .engine import build_snapshot, estimate_kwp
from .history import BatteryReading, History, Reading
from .sources import Installation, discover, load_profiles

_LOGGER = logging.getLogger(__name__)

type EnergyHubConfigEntry = ConfigEntry[EnergyHubCoordinator]

POWER_FACTORS = {"W": 0.001, "kW": 1.0, "MW": 1000.0, "mW": 1e-6}
SAVE_DELAY = 300
# Installation re-detected this often (a new integration, a renamed entity).
DISCOVER_SECONDS = 3600


def _number(state: State | None) -> float | None:
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, ""):
        return None
    try:
        return float(state.state)
    except ValueError:
        return None


def power_kw(state: State | None) -> float | None:
    """A power state in kW, whatever its unit (W when the unit is missing and the value is large)."""
    value = _number(state)
    if value is None:
        return None
    unit = state.attributes.get("unit_of_measurement")
    if unit in POWER_FACTORS:
        return value * POWER_FACTORS[unit]
    return value / 1000 if abs(value) > 100 else value


class EnergyHubCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    config_entry: EnergyHubConfigEntry

    def __init__(self, hass: HomeAssistant, entry: EnergyHubConfigEntry, cfg: HubConfig) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=UPDATE_SECONDS), config_entry=entry
        )
        self.cfg = cfg
        self.store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}")
        self.history = History()
        self.installation = Installation()
        self.profiles = []
        self._discovered_at = 0.0
        self._plant: demo.DemoPlant | None = None
        self._last_t: float | None = None
        self._notified: dict[str, str] = {}
        self.reading: Reading | None = None

    @property
    def demo(self) -> bool:
        return self.cfg.demo

    async def async_setup(self) -> None:
        """Load the profiles and the stored history (or build the demo's)."""
        self.profiles = await self.hass.async_add_executor_job(load_profiles)
        if self.demo:
            now = dt_util.now()
            self.cfg.planes = self.cfg.planes or list(demo.PLANES)
            self.cfg.inverter_max_kw = self.cfg.inverter_max_kw or demo.INVERTER_MAX_KW
            self.cfg.export_limit_kw = self.cfg.export_limit_kw or demo.EXPORT_LIMIT_KW
            self.cfg.cost = self.cfg.cost or 9800.0
            self.cfg.subsidy = self.cfg.subsidy or 1140.0
            self.cfg.commissioned = self.cfg.commissioned or demo.COMMISSIONED
            self._plant = await self.hass.async_add_executor_job(
                demo.backfill, self.history, now, self.hass.config.latitude, self.hass.config.longitude
            )
            self._last_t = now.timestamp()
            self.installation = demo.installation()
            return
        self.history = History.from_json(await self.store.async_load())
        await self._async_discover()

    async def _async_discover(self) -> None:
        prefs = None
        try:
            from homeassistant.components.energy.data import async_get_manager  # noqa: PLC0415

            manager = await async_get_manager(self.hass)
            prefs = manager.data
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Energy preferences not available: %s", err)
        self.installation = discover(self.hass, self.cfg, prefs, self.profiles)
        self._discovered_at = time.monotonic()

    async def async_save(self) -> None:
        if not self.demo:
            await self.store.async_save(self.history.to_json())

    @callback
    def _data_to_save(self) -> dict[str, Any]:
        return self.history.to_json()

    async def _async_update_data(self) -> dict[str, Any]:
        now = dt_util.now()
        if self.demo:
            seconds = now.timestamp() - (self._last_t or now.timestamp())
            self._last_t = now.timestamp()
            reading = self._plant.step(now, max(seconds, 1.0)) if self._plant else None
            ages: dict[str, float] = {}
        else:
            if time.monotonic() - self._discovered_at > DISCOVER_SECONDS:
                await self._async_discover()
            reading, ages = self._read(now)
        if reading is not None:
            self.history.add(reading, now)
            self.reading = reading
        if not self.demo:
            self.store.async_delay_save(self._data_to_save, SAVE_DELAY)
        snapshot = await self.hass.async_add_executor_job(
            build_snapshot, self.history, self.installation, self.cfg, reading, now, ages, self.demo
        )
        await self._async_alerts(snapshot)
        return snapshot

    # ---- reading the states
    def _read(self, now) -> tuple[Reading, dict[str, float]]:
        inst = self.installation
        get = self.hass.states.get
        ages: dict[str, float] = {}
        stale: list[str] = []
        for entity_id in inst.entity_ids():
            state = get(entity_id)
            if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                stale.append(entity_id)
            if state is None:
                continue
            age = now - state.last_reported if hasattr(state, "last_reported") else now - state.last_updated
            ages[entity_id] = round(age.total_seconds())

        def role_kw(role: str) -> float | None:
            entity_id = inst.roles.get(role)
            return power_kw(get(entity_id)) if entity_id else None

        units = self._units(inst.units)
        strings = self._units(inst.strings)
        pv = role_kw("pv_power")
        if pv is None and (strings or units):
            pv = sum((strings or units).values())
        grid = role_kw("grid_power")
        if grid is not None and inst.signs.get("grid_power") == "export_positive":
            grid = -grid
        batteries = []
        for b in inst.batteries:
            p = power_kw(get(b.power)) if b.power else None
            if p is not None and not b.charge_positive:
                p = -p
            cap = b.capacity_kwh
            if cap is None and b.capacity_entity:
                cap = _number(get(b.capacity_entity))
            cells: list[float] = []
            if b.cells_attribute and b.cells:
                st = get(b.cells[0])
                raw = st.attributes.get(b.cells_attribute) if st else None
                if isinstance(raw, list | tuple):
                    cells = [float(v) for v in raw if isinstance(v, int | float)]
            else:
                cells = [v for v in (_number(get(e)) for e in b.cells) if v is not None]
                cells = [v / 1000 if v > 100 else v for v in cells]
            batteries.append(
                BatteryReading(
                    b.key,
                    _number(get(b.soc)) if b.soc else None,
                    p,
                    soh=_number(get(b.soh)) if b.soh else None,
                    cycles=_number(get(b.cycles)) if b.cycles else None,
                    temperature=_number(get(b.temperature)) if b.temperature else None,
                    capacity_kwh=cap,
                    cells=cells,
                    cell_temps=[v for v in (_number(get(e)) for e in b.cell_temperatures) if v is not None],
                    cells_per_module=b.cells_per_module,
                )
            )
        batt = sum(b.power_kw or 0.0 for b in batteries)
        load = role_kw("load_power")
        if grid is None and load is not None and pv is not None:
            grid = load + batt - pv
        if load is None and grid is not None and pv is not None:
            load = max(pv + grid - batt, 0.0)
        clear = self._clearsky(now)
        forecast = role_kw("forecast_power")
        offline = any(
            entity_id in stale and ages.get(entity_id, 0) > STALE_SECONDS
            for entity_id in (inst.roles.get("pv_power"), inst.roles.get("grid_power"))
            if entity_id
        )
        return (
            Reading(
                t=now.timestamp(),
                pv_kw=pv,
                load_kw=load,
                grid_kw=grid,
                expected_kw=forecast if forecast is not None else clear,
                clearsky_kw=clear,
                units=units or {},
                strings=strings,
                batteries=batteries,
                stale=sorted(stale),
                offline=offline,
            ),
            ages,
        )

    def _units(self, units) -> dict[str, float]:
        get = self.hass.states.get
        out = {}
        for u in units:
            if u.power:
                kw = power_kw(get(u.power))
            else:
                v, i = _number(get(u.voltage)), _number(get(u.current))
                kw = v * i / 1000 if v is not None and i is not None else None
            if kw is not None:
                out[u.name] = max(kw, 0.0)
        return out

    def _clearsky(self, now) -> float | None:
        planes = self.cfg.planes
        if not planes:
            kwp, _estimated = estimate_kwp(self.cfg, self.history)
            if not kwp:
                return None
            planes = [Plane(kwp)]
        return clearsky_power(now, self.hass.config.latitude, self.hass.config.longitude, planes)

    # ---- alerts
    async def _async_alerts(self, snapshot: dict[str, Any]) -> None:
        """Fire an event, and notify when configured, once a day per alert."""
        today = snapshot["generated"][:10]
        for alert in snapshot["alerts"]:
            key = f"{alert['kind']}:{alert.get('name') or alert.get('unit') or alert.get('battery') or ''}"
            if self._notified.get(key) == today:
                continue
            self._notified[key] = today
            self.hass.bus.async_fire(EVENT_ALERT, alert)
            if self.cfg.notify and not self.demo:
                domain, _, service = self.cfg.notify.partition(".")
                if self.hass.services.has_service(domain, service):
                    await self.hass.services.async_call(
                        domain,
                        service,
                        {"title": "Energy Hub", "message": _alert_text(alert)},
                        blocking=False,
                    )


def _alert_text(alert: dict[str, Any]) -> str:
    kind = alert["kind"]
    if kind == "clipping":
        return f"Inverter clipping today: {alert['kwh']} kWh lost."
    if kind == "string_lagging":
        return f"{alert['name']} produces {round((1 - (alert['relative'] or 1)) * 100)} % less than its peers."
    if kind == "shading":
        unit = f"{alert['unit']}: " if alert.get("unit") else ""
        start, end = alert["start"], alert["end"]
        return f"{unit}recurring shading {start // 60}:{start % 60:02d}-{end // 60}:{end % 60:02d}."
    if kind == "soiling":
        return f"Soiling loss {round(alert['loss'] * 100, 1)} %: cleaning may pay."
    if kind == "cell_drift":
        return f"{alert['battery']}: cell {alert['cell']} reaches the spread threshold in {alert['days']} days."
    if kind == "battery_exchange":
        return f"One battery charges another ({alert['kw']} kW): energy lost in round trips."
    if kind == "stale":
        return "A source of Energy Hub stopped updating: " + ", ".join(alert["entities"])
    return kind
