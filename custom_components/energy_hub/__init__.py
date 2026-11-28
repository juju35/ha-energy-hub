"""Energy Hub: solar production, self-consumption, batteries, panel efficiency and production losses, in one panel."""

from __future__ import annotations

import hashlib
import logging
from functools import partial
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HassJob, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.typing import ConfigType

from .config import INSTALLATION_SCHEMA, ROLES, YAML_SCHEMA, entity_ids, parse
from .const import (
    BADGE_FILENAME,
    CONF_ENTITIES,
    CONF_PANELS,
    CONF_PLANES,
    CONF_SHOW_PANEL,
    CONF_STRINGS,
    DOMAIN,
    FRONTEND_URL,
    PANEL_FILENAME,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL_PATH,
    VERSION,
)
from .coordinator import EnergyHubConfigEntry, EnergyHubCoordinator
from .sources import role_entities

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]
FRONTEND_DIR = Path(__file__).parent / "frontend"
PANEL_REMOVE_DELAY = 10
DATA_YAML = f"{DOMAIN}_yaml"

CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): YAML_SCHEMA}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the panel, register the websocket commands, and import the YAML block into an entry."""
    await hass.http.async_register_static_paths([StaticPathConfig(FRONTEND_URL, str(FRONTEND_DIR), True)])
    _base, badge_url = await _file_url(hass, BADGE_FILENAME)
    add_extra_js_url(hass, badge_url)
    websocket_api.async_register_command(hass, ws_snapshot)
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_settings)
    websocket_api.async_register_command(hass, ws_set_entities)
    websocket_api.async_register_command(hass, ws_set_installation)
    if DOMAIN in config:
        # Kept unvalidated: config.parse validates it again with the entry's options.
        hass.data[DATA_YAML] = dict(config[DOMAIN])
        if not hass.config_entries.async_entries(DOMAIN):
            hass.async_create_task(
                hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_IMPORT}, data={})
            )
    return True


async def _file_url(hass: HomeAssistant, filename: str) -> tuple[str, str]:
    """Base URL of a frontend file, and the same URL versioned with the file's hash for the browser cache."""
    path = FRONTEND_DIR / filename
    digest = await hass.async_add_executor_job(
        lambda: hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()[:8]
    )
    base_url = f"{FRONTEND_URL}/{filename}"
    return base_url, f"{base_url}?v={digest}"


async def async_setup_entry(hass: HomeAssistant, entry: EnergyHubConfigEntry) -> bool:
    cfg = parse(hass.data.get(DATA_YAML), dict(entry.options))
    coordinator = EnergyHubCoordinator(hass, entry, cfg)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await _async_update_panel(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EnergyHubConfigEntry) -> bool:
    await entry.runtime_data.async_save()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        async_call_later(
            hass, PANEL_REMOVE_DELAY, HassJob(partial(_async_check_panel_later, hass), cancel_on_shutdown=True)
        )
    return unloaded


async def _async_reload(hass: HomeAssistant, entry: EnergyHubConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _loaded_entries(hass: HomeAssistant) -> list[EnergyHubConfigEntry]:
    return [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]


async def _async_update_panel(hass: HomeAssistant, entry: EnergyHubConfigEntry) -> None:
    """Show the sidebar panel unless the option turns it off."""
    wanted = entry.runtime_data.cfg.show_panel
    registered = PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {})
    if wanted and not registered:
        _base, url = await _file_url(hass, PANEL_FILENAME)
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name="energy-hub-panel",
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            module_url=url,
            require_admin=False,
            config={"version": VERSION},
        )
    elif not wanted and registered:
        frontend.async_remove_panel(hass, PANEL_URL_PATH)


@callback
def _async_check_panel_later(hass: HomeAssistant, _now: Any) -> None:
    if not _loaded_entries(hass) and PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {}):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)


def _coordinator(hass: HomeAssistant) -> EnergyHubCoordinator | None:
    entries = _loaded_entries(hass)
    return entries[0].runtime_data if entries else None


@websocket_api.websocket_command({vol.Required("type"): "energy_hub/snapshot"})
@callback
def ws_snapshot(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """The panel's whole snapshot, once."""
    coordinator = _coordinator(hass)
    if coordinator is None or coordinator.data is None:
        connection.send_error(msg["id"], "not_loaded", "Energy Hub is not loaded")
        return
    connection.send_result(msg["id"], coordinator.data)


@websocket_api.websocket_command({vol.Required("type"): "energy_hub/subscribe"})
@callback
def ws_subscribe(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """The snapshot now, then again after every update of the coordinator (every 30 seconds)."""
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "Energy Hub is not loaded")
        return

    @callback
    def forward() -> None:
        if coordinator.data is not None:
            connection.send_message(websocket_api.event_message(msg["id"], coordinator.data))

    connection.subscriptions[msg["id"]] = coordinator.async_add_listener(forward)
    connection.send_result(msg["id"])
    forward()


@websocket_api.websocket_command({vol.Required("type"): "energy_hub/settings"})
@callback
def ws_settings(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """What the Settings tab shows: the YAML in use (rebuilt from the configuration) and the entry's options."""
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "Energy Hub is not loaded")
        return
    connection.send_result(
        msg["id"],
        settings_payload(
            coordinator.cfg,
            coordinator.installation,
            yaml_configured=DATA_YAML in hass.data,
            show_panel=coordinator.config_entry.options.get(CONF_SHOW_PANEL, True),
            notify=coordinator.notify_target,
        ),
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "energy_hub/set_entities",
        vol.Required("roles"): {vol.In(ROLES): vol.Any(None, cv.entity_id, [cv.entity_id])},
    }
)
@websocket_api.async_response
async def ws_set_entities(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Save the entities chosen for each role in the entry's options; the integration reloads."""
    entries = _loaded_entries(hass)
    if not entries:
        connection.send_error(msg["id"], "not_loaded", "Energy Hub is not loaded")
        return
    entry = entries[0]
    chosen = {role: ids for role, value in msg["roles"].items() if (ids := entity_ids(value))}
    options = dict(entry.options)
    if chosen:
        options[CONF_ENTITIES] = chosen
    else:
        options.pop(CONF_ENTITIES, None)
    hass.config_entries.async_update_entry(entry, options=options)
    connection.send_result(msg["id"], {"roles": chosen})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "energy_hub/set_installation", **INSTALLATION_SCHEMA})
@websocket_api.async_response
async def ws_set_installation(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Save the planes, strings and panels declared from the Settings tab; the integration reloads.

    A list in the message replaces the YAML's for that key; an empty list removes the key, so the YAML (or the
    detection) speaks again. The update listener reloads the entry: the sensors follow the new declaration.
    """
    entries = _loaded_entries(hass)
    if not entries:
        connection.send_error(msg["id"], "not_loaded", "Energy Hub is not loaded")
        return
    entry = entries[0]
    options = dict(entry.options)
    for key in (CONF_PLANES, CONF_STRINGS, CONF_PANELS):
        if key not in msg:
            continue
        values = msg[key] or []
        if values:
            options[key] = values
        else:
            options.pop(key, None)
    hass.config_entries.async_update_entry(entry, options=options)
    connection.send_result(
        msg["id"], {key: list(entry.options.get(key) or []) for key in (CONF_PLANES, CONF_STRINGS, CONF_PANELS)}
    )


def _unit_payload(unit) -> dict[str, Any]:
    """A declared string or panel, as the Settings tab edits it."""
    return {
        "name": unit.name,
        # Detected by the profile but not declared by the user: the panel must not write it back
        # as a declaration (that would make it count on top of the pv_power role and double count).
        "declared": bool(getattr(unit, "declared", False)),
        "kwp": unit.kwp,
        "tilt": unit.tilt,
        "azimuth": unit.azimuth,
        "power": unit.power,
        "voltage": unit.voltage,
        "current": unit.current,
        "count_in_total": unit.count_in_total,
    }


def settings_payload(
    cfg, inst, *, yaml_configured: bool, show_panel: bool, notify: str | None = None
) -> dict[str, Any]:
    """What the Settings tab shows: the YAML in use (rebuilt from the configuration) and the values behind it."""
    return {
        "yaml_configured": yaml_configured,
        "demo": cfg.demo,
        "show_panel": show_panel,
        "yaml": settings_yaml(cfg, inst),
        "planes": [{"kwp": p.kwp, "tilt": p.tilt, "azimuth": p.azimuth} for p in cfg.planes],
        # Whether a pv_power meter is there: without one the units are the total, so an unset count_in_total counts.
        "pv_metered": bool(role_entities(inst, "pv_power")),
        "kwp": cfg.kwp,
        "strings": [_unit_payload(u) for u in inst.strings],
        "panels": [_unit_payload(u) for u in inst.units],
        "batteries": [
            {
                "key": b.key,
                "name": b.name,
                "soc": b.soc,
                "power": b.power,
                "capacity_kwh": b.capacity_kwh,
                "reserve": b.reserve,
                "cells": len(b.cells),
            }
            for b in inst.batteries
        ],
        "tariff": {"import": cfg.import_price, "export": cfg.export_price, "currency": cfg.currency},
        "installation": {
            "cost": cfg.cost,
            "subsidy": cfg.subsidy,
            "commissioned": cfg.commissioned.isoformat() if cfg.commissioned else None,
        },
        "notify": notify or cfg.notify,
        "notify_auto": bool(notify) and not cfg.notify,
    }


def settings_yaml(cfg, inst) -> str:
    """A YAML block equivalent to what is in use, to copy into configuration.yaml and adjust."""
    lines = ["energy_hub:"]
    if cfg.planes:
        lines.append("  planes:")
        for p in cfg.planes:
            lines += [f"    - kwp: {p.kwp:g}", f"      tilt: {p.tilt:g}", f"      azimuth: {p.azimuth:g}"]
    if cfg.inverter_max_kw:
        lines.append(f"  inverter_max_kw: {cfg.inverter_max_kw:g}")
    if cfg.export_limit_kw:
        lines.append(f"  export_limit_kw: {cfg.export_limit_kw:g}")
    roles = {k: role_entities(inst, k) for k in inst.roles if not k.startswith("forecast") and k != "weather"}
    if roles:
        lines.append("  entities:")
        for role, ids in sorted(roles.items()):
            value = ids[0] if len(ids) == 1 else "[" + ", ".join(ids) + "]"
            lines.append(f"    {role}: {value}")
    for key, units in (("strings", cfg.strings), ("panels", cfg.panels)):
        if not units:
            continue
        lines.append(f"  {key}:")
        for u in units:
            lines.append(f"    - name: {u.name}")
            for attr in ("power", "voltage", "current"):
                if getattr(u, attr):
                    lines.append(f"      {attr}: {getattr(u, attr)}")
            for attr in ("kwp", "tilt", "azimuth"):
                if getattr(u, attr) is not None:
                    lines.append(f"      {attr}: {getattr(u, attr):g}")
            if u.count_in_total is not None:
                lines.append(f"      count_in_total: {str(u.count_in_total).lower()}")
    if inst.batteries:
        lines.append("  batteries:")
        for b in inst.batteries:
            lines.append(f"    {b.key}:")
            lines.append(f"      name: {b.name}")
            for attr in ("soc", "power"):
                if getattr(b, attr):
                    lines.append(f"      {attr}: {getattr(b, attr)}")
            if b.capacity_kwh:
                lines.append(f"      capacity_kwh: {b.capacity_kwh:g}")
            lines.append(f"      reserve: {b.reserve:g}")
            if b.cells and not b.cells_attribute:
                prefix = b.cells[0].rstrip("0123456789")
                lines.append(f"      cells: {prefix}*")
            if b.cell_temperatures:
                lines.append(f"      cell_temperatures: {b.cell_temperatures[0].rstrip('0123456789')}*")
            if b.cells_per_module:
                lines.append(f"      cells_per_module: {b.cells_per_module}")
    if inst.consumers:
        lines.append("  consumers:")
        for c in inst.consumers:
            name = c.name.replace("\\", "\\\\").replace('"', '\\"')
            lines += [f"    {c.key}:", f'      name: "{name}"']
            for attr in ("power", "energy"):
                if getattr(c, attr):
                    lines.append(f"      {attr}: {getattr(c, attr)}")
            lines.append(f"      kind: {c.kind}")
            if c.import_price is not None:
                lines.append(f"      import_price: {c.import_price:g}")
            if c.separate_meter:
                lines.append("      separate_meter: true")
    if inst.excluded:
        lines.append("  ignore:")
        lines += [f"    - {e}" for e in sorted(inst.excluded)]
    lines += ["  tariff:", f"    import: {cfg.import_price:g}", f"    export: {cfg.export_price:g}"]
    if contract := cfg.contract or inst.tariff.get("contract"):
        lines.append(f"    contract: {contract}")
    if kva := cfg.kva or inst.tariff.get("kva"):
        lines.append(f"    kva: {kva}")
    if cfg.offpeak:
        lines.append(f'    offpeak: "{cfg.offpeak}"')
    if inst.roles.get("weather"):
        lines.append(f"  weather: {inst.roles['weather']}")
    if cfg.cost:
        lines += ["  installation:", f"    cost: {cfg.cost:g}", f"    subsidy: {cfg.subsidy:g}"]
        if cfg.commissioned:
            lines.append(f"    commissioned: {cfg.commissioned.isoformat()}")
    if cfg.notify:
        lines.append(f"  notify: {cfg.notify}")
    return "\n".join(lines) + "\n"
