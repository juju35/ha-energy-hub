"""Which entities feed Energy Hub, in three layers (later ones win):

1. the Energy dashboard's preferences (``energy/get_prefs``): solar, grid and battery energies and their powers;
2. the profile of each source integration (``profiles/<integration>.yaml``): roles, strings, micro-inverters,
   batteries, signs and capabilities, matched on the entity ids of that integration;
3. the user's YAML (``entities:``, ``batteries:``, ``forecast:``, ``ignore:``).

Every capability carries a status: ``provided`` by the source, ``estimated`` by the hub, or ``absent``.
"""

from __future__ import annotations

import fnmatch
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .config import BatteryConfig, HubConfig

_LOGGER = logging.getLogger(__name__)

PROFILES_DIR = Path(__file__).parent / "profiles"
DEFAULT_CAPACITY_KWH = 5.0


@dataclass(slots=True)
class Profile:
    key: str
    name: str
    platform: str
    status: str
    url: str
    roles: dict[str, list[re.Pattern]]
    strings: dict[str, list[re.Pattern]]
    units: dict[str, list[re.Pattern]]
    battery: dict[str, list[re.Pattern]]
    signs: dict[str, str]
    capabilities: dict[str, str]
    match_device: list[re.Pattern]


def _patterns(section: dict[str, list[str]] | None) -> dict[str, list[re.Pattern]]:
    return {k: [re.compile(p) for p in v] for k, v in (section or {}).items()}


def load_profiles(directory: Path = PROFILES_DIR) -> list[Profile]:
    """Every profile of the integration (blocking: run in the executor)."""
    profiles = []
    for path in sorted(directory.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        profiles.append(
            Profile(
                key=path.stem,
                name=raw["name"],
                platform=raw["platform"],
                status=raw.get("status", "beta"),
                url=raw.get("url", ""),
                roles=_patterns(raw.get("roles")),
                strings=_patterns(raw.get("strings")),
                units=_patterns(raw.get("units")),
                battery=_patterns(raw.get("battery")),
                signs=dict(raw.get("signs") or {}),
                capabilities=dict(raw.get("capabilities") or {}),
                match_device=[re.compile(p, re.IGNORECASE) for p in raw.get("match_device", [])],
            )
        )
    return profiles


@dataclass(slots=True)
class UnitSource:
    """A string / MPPT input or a micro-inverter: power, or voltage and current to multiply."""

    name: str
    power: str | None = None
    voltage: str | None = None
    current: str | None = None
    kwp: float | None = None


@dataclass(slots=True)
class BatterySource:
    key: str
    name: str
    platform: str
    soc: str | None = None
    power: str | None = None
    charge_positive: bool = True
    capacity_kwh: float | None = None
    capacity_entity: str | None = None
    reserve: float = 10.0
    soh: str | None = None
    cycles: str | None = None
    temperature: str | None = None
    charge_energy: str | None = None
    discharge_energy: str | None = None
    cells: list[str] = field(default_factory=list)
    cells_attribute: str | None = None
    cell_temperatures: list[str] = field(default_factory=list)
    cells_per_module: int | None = None


@dataclass(slots=True)
class SourceInfo:
    """A source integration as the Settings tab shows it."""

    key: str
    name: str
    platform: str
    status: str
    url: str
    role: str
    capabilities: dict[str, str]
    entities: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Installation:
    roles: dict[str, str] = field(default_factory=dict)
    signs: dict[str, str] = field(default_factory=dict)
    strings: list[UnitSource] = field(default_factory=list)
    units: list[UnitSource] = field(default_factory=list)
    batteries: list[BatterySource] = field(default_factory=list)
    sources: list[SourceInfo] = field(default_factory=list)
    excluded: dict[str, str] = field(default_factory=dict)
    # What the detection could not decide alone (a BMS to attach to a battery…), shown in the Settings tab.
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    # Contract and power read from Tarif EDF's price entity (``tarif_actuel_tempo_9kva_ttc``).
    tariff: dict[str, Any] = field(default_factory=dict)

    def entity_ids(self) -> set[str]:
        ids = set(self.roles.values())
        for u in [*self.strings, *self.units]:
            ids |= {e for e in (u.power, u.voltage, u.current) if e}
        for b in self.batteries:
            ids |= {e for e in (b.soc, b.power, b.soh, b.cycles, b.temperature, b.capacity_entity) if e}
            ids |= set(b.cells) | set(b.cell_temperatures)
        return ids


def _first(patterns: list[re.Pattern], object_ids: dict[str, str]) -> str | None:
    for pattern in patterns:
        for object_id, entity_id in sorted(object_ids.items()):
            if pattern.search(object_id):
                return entity_id
    return None


def _all(patterns: list[re.Pattern], object_ids: dict[str, str]) -> dict[str, str]:
    """``{label: entity_id}`` of every match, the label being the pattern's first group (or the object id)."""
    found: dict[str, str] = {}
    for pattern in patterns:
        for object_id, entity_id in sorted(object_ids.items()):
            m = pattern.search(object_id)
            if m:
                found.setdefault(m.group(1) if m.groups() else object_id, entity_id)
    return found


def _units(spec: dict[str, list[re.Pattern]], object_ids: dict[str, str], prefix: str) -> list[UnitSource]:
    power = _all(spec.get("power", []), object_ids)
    voltage = _all(spec.get("voltage", []), object_ids)
    current = _all(spec.get("current", []), object_ids)
    labels = sorted(set(power) | (set(voltage) & set(current)), key=lambda s: (len(s), s))
    return [
        UnitSource(f"{prefix} {label}", power.get(label), voltage.get(label), current.get(label)) for label in labels
    ]


def _object_ids(entries: list[er.RegistryEntry]) -> dict[str, str]:
    return {e.entity_id.split(".", 1)[1]: e.entity_id for e in entries if e.domain == "sensor"}


def _apply_profile(
    profile: Profile, entries: list[er.RegistryEntry], devices: dr.DeviceRegistry, inst: Installation
) -> SourceInfo | None:
    if profile.match_device:
        kept = []
        for entry in entries:
            device = devices.async_get(entry.device_id) if entry.device_id else None
            label = " ".join(
                filter(None, [device.name if device else "", device.model if device else "", entry.entity_id])
            )
            if any(p.search(label) for p in profile.match_device):
                kept.append(entry)
        entries = kept
    object_ids = _object_ids(entries)
    if not object_ids:
        return None
    used: list[str] = []
    for role, patterns in profile.roles.items():
        if role not in inst.roles and (entity_id := _first(patterns, object_ids)):
            inst.roles[role] = entity_id
            used.append(entity_id)
    for sign_role, sign in profile.signs.items():
        inst.signs.setdefault(sign_role, sign)
    strings = _units(profile.strings, object_ids, "String")
    units = _units(profile.units, object_ids, "Panel")
    inst.strings.extend(strings)
    inst.units.extend(units)
    used += [e for u in [*strings, *units] for e in (u.power, u.voltage, u.current) if e]

    if profile.battery:
        by_device: dict[str, list[er.RegistryEntry]] = {}
        for entry in entries:
            by_device.setdefault(entry.device_id or "", []).append(entry)
        for index, (device_id, device_entries) in enumerate(sorted(by_device.items())):
            ids = _object_ids(device_entries)
            soc = _first(profile.battery.get("soc", []), ids)
            if not soc:
                continue
            device = devices.async_get(device_id) if device_id else None
            battery = BatterySource(
                key=f"{profile.key}_{index}",
                name=(device.name_by_user or device.name) if device else profile.name,
                platform=profile.platform,
                soc=soc,
                power=_first(profile.battery.get("power", []), ids),
                charge_positive=profile.signs.get("battery_power", "charge_positive") == "charge_positive",
                capacity_entity=_first(profile.battery.get("capacity", []), ids),
                soh=_first(profile.battery.get("soh", []), ids),
                cycles=_first(profile.battery.get("cycles", []), ids),
                temperature=_first(profile.battery.get("temperature", []), ids),
                charge_energy=_first(profile.battery.get("charge_energy", []), ids),
                discharge_energy=_first(profile.battery.get("discharge_energy", []), ids),
            )
            if cells := _first(profile.battery.get("cells", []), ids):
                battery.cells = [cells]
                battery.cells_attribute = "cell_voltages"
            inst.batteries.append(battery)
            used += [e for e in (battery.soc, battery.power, battery.soh, battery.cycles) if e]
    if not used:
        return None
    caps = profile.capabilities
    role = "forecast" if "forecast" in caps else "tariff" if "tariff" in caps else "meter" if "tempo" in caps else "pv"
    if profile.battery and not profile.roles:
        role = "storage"
    return SourceInfo(
        profile.key, profile.name, profile.platform, profile.status, profile.url, role, dict(profile.capabilities), used
    )


def _from_energy_prefs(prefs: dict[str, Any] | None, inst: Installation, hass: HomeAssistant) -> None:
    """Roles from the Energy dashboard's preferences: the user already said which entity is what there."""
    if not prefs:
        return
    ent_reg = er.async_get(hass)
    for source in prefs.get("energy_sources", []):
        kind = source.get("type")
        if kind == "solar":
            inst.roles.setdefault("pv_energy", source["stat_energy_from"])
            if source.get("stat_rate"):
                inst.roles.setdefault("pv_power", source["stat_rate"])
        elif kind == "grid":
            if flows := source.get("flow_from"):
                inst.roles.setdefault("grid_import_energy", flows[0]["stat_energy_from"])
            if flows := source.get("flow_to"):
                inst.roles.setdefault("grid_export_energy", flows[0]["stat_energy_to"])
            for power in source.get("power") or []:
                if power.get("stat_rate"):
                    inst.roles.setdefault("grid_power", power["stat_rate"])
                    inst.signs.setdefault("grid_power", "import_positive")
        elif kind == "battery":
            energy_entity = ent_reg.async_get(source["stat_energy_from"])
            soc = None
            if energy_entity and energy_entity.device_id:
                for entry in er.async_entries_for_device(ent_reg, energy_entity.device_id):
                    if (entry.device_class or entry.original_device_class) == "battery" and entry.domain == "sensor":
                        soc = entry.entity_id
                        break
            if soc and all(b.soc != soc for b in inst.batteries):
                inst.batteries.append(
                    BatterySource(
                        key=f"energy_{len(inst.batteries)}",
                        name="Battery",
                        platform="energy",
                        soc=soc,
                        power=source.get("stat_rate"),
                        charge_positive=False,
                        charge_energy=source.get("stat_energy_to"),
                        discharge_energy=source.get("stat_energy_from"),
                    )
                )


def _apply_yaml(cfg: HubConfig, inst: Installation, all_entity_ids: list[str]) -> None:
    for role, entity_id in cfg.entities.items():
        inst.roles[role] = entity_id
    if cfg.forecast:
        inst.roles["forecast_power"] = cfg.forecast[0]
    for battery_cfg in cfg.batteries:
        _merge_battery(battery_cfg, inst, all_entity_ids)
    for entity_id in cfg.ignore:
        inst.excluded[entity_id] = "ignore"
    inst.roles = {r: e for r, e in inst.roles.items() if e not in inst.excluded}
    inst.strings = [u for u in inst.strings if (u.power or u.voltage) not in inst.excluded]
    inst.units = [u for u in inst.units if u.power not in inst.excluded]
    inst.batteries = [b for b in inst.batteries if b.soc not in inst.excluded]


def _merge_battery(cfg: BatteryConfig, inst: Installation, all_entity_ids: list[str]) -> None:
    battery = next((b for b in inst.batteries if cfg.soc and b.soc == cfg.soc), None)
    if battery is None:
        battery = BatterySource(key=cfg.key, name=cfg.name, platform="yaml")
        inst.batteries.append(battery)
    battery.key = cfg.key
    battery.name = cfg.name
    for attr in ("soc", "power", "soh", "cycles", "temperature"):
        if value := getattr(cfg, attr):
            setattr(battery, attr, value)
    if cfg.power:
        battery.charge_positive = cfg.charge_positive
    if cfg.capacity_kwh:
        battery.capacity_kwh = cfg.capacity_kwh
    battery.reserve = cfg.reserve
    if cfg.cells:
        battery.cells = sorted(fnmatch.filter(all_entity_ids, cfg.cells), key=_natural)
        battery.cells_attribute = None
    if cfg.cell_temperatures:
        battery.cell_temperatures = sorted(fnmatch.filter(all_entity_ids, cfg.cell_temperatures), key=_natural)
    if cfg.cells_per_module:
        battery.cells_per_module = cfg.cells_per_module


TARIFF_ID = re.compile(r"tarif_actuel_(base|hphc|tempo)_(\d+)kva_ttc$")


def _tariff(inst: Installation) -> None:
    """The contract and power Tarif EDF was set up with, read from its price entity's object id."""
    if m := TARIFF_ID.search(inst.roles.get("tariff_price", "")):
        inst.tariff = {"contract": m.group(1), "kva": int(m.group(2))}


def _title(platform: str) -> str:
    return platform.replace("_", " ").title()


def _weather(hass: HomeAssistant, cfg: HubConfig, inst: Installation, entries: list[er.RegistryEntry]) -> None:
    """The references of the expected production found in Home Assistant: an irradiance sensor (W/m², a weather
    station's pyranometer: Ecowitt, WeatherFlow, Buienradar…) and a weather entity for the cloud cover."""
    if "irradiance" not in inst.roles:
        for entry in sorted(entries, key=lambda e: e.entity_id):
            if entry.domain == "sensor" and (entry.device_class or entry.original_device_class) == "irradiance":
                inst.roles["irradiance"] = entry.entity_id
                inst.sources.append(
                    SourceInfo(
                        "irradiance",
                        _title(entry.platform),
                        entry.platform,
                        "core",
                        "",
                        "weather",
                        {"irradiance": "provided"},
                        [entry.entity_id],
                    )
                )
                break
    weather = cfg.weather
    if weather is None:
        states = sorted(
            hass.states.async_all("weather"), key=lambda st: ("cloud_coverage" not in st.attributes, st.entity_id)
        )
        weather = states[0].entity_id if states else None
    if weather:
        inst.roles["weather"] = weather
        entry = er.async_get(hass).async_get(weather)
        platform = entry.platform if entry else "weather"
        inst.sources.append(
            SourceInfo("weather", _title(platform), platform, "core", "", "weather", {"clouds": "provided"}, [weather])
        )


def _natural(text: str) -> list[Any]:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", text)]


def _suggest_bms(inst: Installation) -> None:
    """A BMS seen as a battery of its own while a battery has no cells: probably the same battery. Suggested only;
    the engine adds how well their charges follow each other."""
    targets = [b for b in inst.batteries if b.platform != "bms_ble" and not b.cells]
    for bms in (b for b in inst.batteries if b.platform == "bms_ble" and b.cells):
        for target in targets:
            inst.suggestions.append(
                {
                    "kind": "attach_bms",
                    "bms": bms.name,
                    "bms_key": bms.key,
                    "battery": target.name,
                    "battery_key": target.key,
                    "yaml": f"energy_hub:\n  batteries:\n    {target.key}:\n      cells: {bms.cells[0]}\n",
                }
            )


def discover(
    hass: HomeAssistant, cfg: HubConfig, prefs: dict[str, Any] | None, profiles: list[Profile]
) -> Installation:
    """The installation as Home Assistant describes it now."""
    inst = Installation()
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    entries = [e for e in ent_reg.entities.values() if not e.disabled_by and e.entity_id not in cfg.ignore]
    by_platform: dict[str, list[er.RegistryEntry]] = {}
    for entry in entries:
        by_platform.setdefault(entry.platform, []).append(entry)
    for profile in profiles:
        if profile.platform in by_platform:
            info = _apply_profile(profile, by_platform[profile.platform], dev_reg, inst)
            if info:
                inst.sources.append(info)
    _from_energy_prefs(prefs, inst, hass)
    if prefs and any(s.get("type") in ("solar", "grid", "battery") for s in prefs.get("energy_sources", [])):
        inst.sources.append(SourceInfo("energy", "Energy dashboard", "energy", "core", "", "prefs", {}, []))
    all_ids = [e.entity_id for e in entries] + [s.entity_id for s in hass.states.async_all("sensor")]
    _apply_yaml(cfg, inst, sorted(set(all_ids)))
    _weather(hass, cfg, inst, entries)
    _tariff(inst)
    # A charge input already counted by an inverter's battery: listed as excluded for the Settings tab.
    for entry in entries:
        if entry.platform == "zendure_ha" and entry.entity_id.endswith("ac_input") and inst.roles.get("pv_power"):
            inst.excluded.setdefault(entry.entity_id, "double_count")
    _suggest_bms(inst)
    _LOGGER.debug("Energy Hub installation: %s", inst)
    return inst
