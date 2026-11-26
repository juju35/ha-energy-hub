"""Reads the source entities every 30 seconds, keeps the history and builds the panel's snapshot."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from . import demo
from .analytics.clearsky import CONDITION_CLOUDS, Plane, clearsky_power, cloud_factor, measured_factor
from .analytics.tariffs import normalize_color
from .config import MULTI_ROLES, HubConfig
from .const import (
    CONF_ENTITIES,
    DOMAIN,
    EVENT_ALERT,
    NOTIFY_HUB,
    STALE_SECONDS,
    STORAGE_KEY,
    STORAGE_VERSION,
    UPDATE_SECONDS,
)
from .engine import build_snapshot, estimate_kwp
from .history import BatteryReading, ConsumerReading, History, Reading
from .sources import Installation, discover, load_profiles, role_entities
from .views import contract_offer

_LOGGER = logging.getLogger(__name__)
# Languages with a translation file of their own
TRANSLATED = frozenset(p.stem for p in (Path(__file__).parent / "translations").glob("*.json"))

type EnergyHubConfigEntry = ConfigEntry[EnergyHubCoordinator]

POWER_FACTORS = {"W": 0.001, "kW": 1.0, "MW": 1000.0, "mW": 1e-6}
ENERGY_FACTORS = {"Wh": 0.001, "kWh": 1.0, "MWh": 1000.0}
# A consumer known by its energy only: its power is the slope between two changes of the energy, and 0 once the
# energy has not moved for this long.
ENERGY_IDLE_SECONDS = 900
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


def energy_kwh(state: State | None) -> float | None:
    """An energy state in kWh, whatever its unit."""
    value = _number(state)
    if value is None:
        return None
    return value * ENERGY_FACTORS.get(state.attributes.get("unit_of_measurement"), 1.0)


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
        # Last energy seen per consumer known by its energy only: {key: (timestamp, kWh, kW)}.
        self._energy_seen: dict[str, tuple[float, float, float | None]] = {}
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
        snapshot["entities"]["configured"] = self._configured_entities()
        await self._async_alerts(snapshot)
        return snapshot

    def _configured_entities(self) -> dict[str, list[str]]:
        """The entities chosen in the options, for the Settings form. Only those: the YAML entities stay in
        configuration.yaml, so saving the form never copies them into the options (where they would win)."""
        return dict(self.config_entry.options.get(CONF_ENTITIES) or {})

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
            """The first entity of the role that answers: that is the alternative-source fallback."""
            for entity_id in role_entities(inst, role):
                value = power_kw(get(entity_id))
                if value is not None:
                    return value
            return None

        def role_sum_kw(role: str) -> float | None:
            """Every entity of the role added up: two PV arrays, two inverters."""
            values = [v for v in (power_kw(get(e)) for e in role_entities(inst, role)) if v is not None]
            return round(sum(values), 4) if values else None

        units = self._units(inst.units)
        strings = self._units(inst.strings)
        pv = role_sum_kw("pv_power")
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
            if p is None and b.charge_power and b.discharge_power:
                charge, discharge = power_kw(get(b.charge_power)), power_kw(get(b.discharge_power))
                if charge is not None and discharge is not None:
                    p = abs(charge) - abs(discharge)
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
        consumers = self._consumers(now.timestamp())
        if load is not None:
            # A consumer on its own meter is not seen by the main meter: added to the home's consumption.
            load += sum(c.kw or 0.0 for c in consumers.values() if c.separate_meter)
        clear = self._clearsky(now)
        expected, reference = self._expected(now, clear, role_kw("forecast_power"))
        color = normalize_color(st.state) if (st := self._role_state("tariff_color")) else None

        def role_offline(role: str) -> bool:
            """Stale for too long: any entity of an added-up role (the sum is incomplete), every entity otherwise
            (a fallback that still answers keeps the role online)."""
            down = [e in stale and ages.get(e, 0) > STALE_SECONDS for e in role_entities(inst, role)]
            if not down:
                return False
            return any(down) if role in MULTI_ROLES else all(down)

        offline = role_offline("pv_power") or role_offline("grid_power")
        return (
            Reading(
                t=now.timestamp(),
                pv_kw=pv,
                load_kw=load,
                grid_kw=grid,
                expected_kw=expected,
                reference=reference,
                clearsky_kw=clear,
                import_price=self._price(now, color),
                # The Tempo day starts at 6:00: before that the colour entity still shows yesterday's.
                day_color=color if now.hour >= 6 else None,
                units=units or {},
                strings=strings,
                batteries=batteries,
                consumers=consumers,
                stale=sorted(stale),
                offline=offline,
            ),
            ages,
        )

    def _consumers(self, t: float) -> dict[str, ConsumerReading]:
        """Each large consumer's power now: its power entity, else the slope of its energy entity."""
        get = self.hass.states.get
        out: dict[str, ConsumerReading] = {}
        for c in self.installation.consumers:
            kw = power_kw(get(c.power)) if c.power else None
            if kw is None and c.energy and (kwh := energy_kwh(get(c.energy))) is not None:
                seen = self._energy_seen.get(c.key)
                if seen is None or kwh < seen[1]:
                    self._energy_seen[c.key] = (t, kwh, None)
                elif kwh > seen[1]:
                    kw = (kwh - seen[1]) * 3600 / max(t - seen[0], 1.0)
                    self._energy_seen[c.key] = (t, kwh, kw)
                else:
                    kw = 0.0 if t - seen[0] > ENERGY_IDLE_SECONDS else seen[2]
            out[c.key] = ConsumerReading(kw, c.import_price, c.separate_meter)
        return out

    def _expected(self, now, clear: float | None, forecast: float | None) -> tuple[float | None, str]:
        """Expected production now and its reference, best first: a measured irradiance (the clear sky scaled by
        measured / clear-sky irradiance), the forecast integration, the weather's cloud cover (Kasten-Czeplak), the
        clear sky alone."""
        get = self.hass.states.get
        inst = self.installation
        lat, lon = self.hass.config.latitude, self.hass.config.longitude
        if clear is not None and (ghi := _number(self._role_state("irradiance"))) is not None:
            factor = measured_factor(ghi, now, lat, lon)
            return (clear * factor if factor is not None else clear), "measured"
        if forecast is not None:
            return forecast, "forecast"
        if clear is not None and (weather := get(inst.roles.get("weather") or "")) is not None:
            cover = weather.attributes.get("cloud_coverage")
            clouds = cover / 100 if isinstance(cover, int | float) else CONDITION_CLOUDS.get(weather.state)
            if clouds is not None:
                return clear * cloud_factor(clouds), "weather"
        return clear, "clearsky"

    def _price(self, now, color: str | None) -> float:
        """Price of the kWh drawn now: the price entity (Tarif EDF), else the contract's grid, else the flat price."""
        if (price := _number(self._role_state("tariff_price"))) is not None:
            return price
        if offer := contract_offer(self.cfg, self.installation):
            # The colour entity shows the colour in force: before 6:00, the Tempo day that started yesterday.
            days = (now.date(), now.date() - timedelta(days=1))
            colors = {d.isoformat(): color for d in days} if color else {}
            return offer.slot_price(now.date(), now.hour * 60 + now.minute, colors)
        return self.cfg.import_price

    def _role_state(self, role: str) -> State | None:
        """The state of the first entity of the role that answers (the alternative-source fallback)."""
        for entity_id in role_entities(self.installation, role):
            state = self.hass.states.get(entity_id)
            if state is not None and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN, ""):
                return state
        return None

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
    @property
    def notify_target(self) -> str | None:
        """Where alerts are sent: the YAML `notify:` target, else Notify Hub's entity when it is installed."""
        if self.cfg.notify:
            return self.cfg.notify
        return NOTIFY_HUB if self.hass.states.get(NOTIFY_HUB) else None

    async def _async_alerts(self, snapshot: dict[str, Any]) -> None:
        """Fire an event, and notify when there is a target, once a day per alert."""
        today = snapshot["generated"][:10]
        for alert in snapshot["alerts"]:
            key = f"{alert['kind']}:{alert.get('name') or alert.get('unit') or alert.get('battery') or ''}"
            if self._notified.get(key) == today:
                continue
            self._notified[key] = today
            self.hass.bus.async_fire(EVENT_ALERT, alert)
            target = self.notify_target
            if target and not self.demo:
                await self._async_notify(target, await self._async_alert_text(alert))

    async def _async_notify(self, target: str, message: str) -> None:
        """Send through a notify entity (`notify.send_message`, Notify Hub's way) or a legacy notify action."""
        data = {"title": "Energy Hub", "message": message}
        domain, _, service = target.partition(".")
        if domain == "notify" and self.hass.states.get(target) is not None:
            await self.hass.services.async_call("notify", "send_message", {"entity_id": target, **data}, blocking=False)
        elif self.hass.services.has_service(domain, service):
            await self.hass.services.async_call(domain, service, data, blocking=False)
        else:
            _LOGGER.warning("Energy Hub: notify target %s not found", target)

    async def _async_alert_text(self, alert: dict[str, Any]) -> str:
        """The alert in Home Assistant's language (translations `exceptions.alert_<kind>`), English as fallback."""
        language = self.hass.config.language or "en"
        # A regional variant without a file of its own (pt-BR) takes its base language rather than English.
        lang = next((x for x in (language, language.split("-")[0]) if x in TRANSLATED), "en")
        texts = await async_get_translations(self.hass, lang, "exceptions", [DOMAIN])
        template = texts.get(f"component.{DOMAIN}.exceptions.alert_{alert['kind']}.message")
        if template:
            try:
                return template.format(**alert_params(alert))
            except (KeyError, IndexError, ValueError):
                pass
        return _alert_text(alert)


def alert_params(alert: dict[str, Any]) -> dict[str, str]:
    """The placeholders of the translated alert messages."""

    def hm(minute: int | None) -> str:
        return "" if minute is None else f"{minute // 60}:{minute % 60:02d}"

    return {
        "kwh": f"{alert.get('kwh', 0)}",
        "name": str(alert.get("name") or ""),
        "pct": f"{round((1 - (alert.get('relative') or 1)) * 100)}",
        "unit": str(alert.get("unit") or ""),
        "start": hm(alert.get("start")),
        "end": hm(alert.get("end")),
        "loss": f"{round((alert.get('loss') or 0) * 100, 1)}",
        "battery": str(alert.get("battery") or ""),
        "cell": str(alert.get("cell") or ""),
        "days": str(alert.get("days") or ""),
        "kw": f"{alert.get('kw', 0)}",
        "entities": ", ".join(alert.get("entities") or []),
    }


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
