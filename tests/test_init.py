"""The integration in demo mode: setup from the UI and from YAML, sensors, websocket commands, panel, unload."""

from __future__ import annotations

from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_hub.const import DOMAIN, PANEL_URL_PATH
from custom_components.energy_hub.diagnostics import async_get_config_entry_diagnostics

DEMO_YAML = {
    "demo": True,
    "planes": [{"kwp": 3.28, "tilt": 30, "azimuth": 190}, {"kwp": 3.28, "tilt": 30, "azimuth": 190}],
    "inverter_max_kw": 4.2,
    "export_limit_kw": 4.5,
    "installation": {"cost": 9800, "subsidy": 1140, "commissioned": "2023-04-12"},
}


async def _setup_demo(hass: HomeAssistant) -> MockConfigEntry:
    hass.config.latitude, hass.config.longitude = 48.11, -1.68
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, options={"demo": True, "show_panel": True})
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: DEMO_YAML})
    await hass.async_block_till_done()
    return entry


async def test_demo_entry_sets_up_sensors_and_panel(hass: HomeAssistant) -> None:
    entry = await _setup_demo(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert PANEL_URL_PATH in hass.data[frontend.DATA_PANELS]
    states = {s.entity_id: s for s in hass.states.async_all("sensor")}
    assert len(states) == 12
    produced = next(s for s in states.values() if s.attributes.get("unit_of_measurement") == "kWh/kWp")
    assert float(produced.state) >= 0
    alerts = next(s for s in states.values() if "alerts" in s.attributes)
    assert int(alerts.state) == len(alerts.attributes["alerts"])


async def test_websocket_snapshot_subscribe_and_settings(hass: HomeAssistant, hass_ws_client) -> None:
    await _setup_demo(hass)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "energy_hub/snapshot"})
    snap = (await client.receive_json())["result"]
    assert snap["demo"] is True
    assert {"live", "today", "curve", "production", "batteries", "losses", "finances", "alerts"} <= set(snap)
    assert len(snap["batteries"]["items"]) == 3
    assert snap["kwp"] == 6.56

    await client.send_json_auto_id({"type": "energy_hub/subscribe"})
    assert (await client.receive_json())["success"]
    event = await client.receive_json()
    assert event["type"] == "event"
    assert event["event"]["kwp"] == 6.56

    await client.send_json_auto_id({"type": "energy_hub/settings"})
    settings = (await client.receive_json())["result"]
    assert settings["yaml_configured"] is True
    assert settings["yaml"].startswith("energy_hub:\n")
    assert "inverter_max_kw: 4.2" in settings["yaml"]


async def test_websocket_errors_when_not_loaded(hass: HomeAssistant, hass_ws_client) -> None:
    assert await async_setup_component(hass, DOMAIN, {})
    client = await hass_ws_client(hass)
    for command in ("energy_hub/snapshot", "energy_hub/subscribe", "energy_hub/settings"):
        await client.send_json_auto_id({"type": command})
        reply = await client.receive_json()
        assert reply["success"] is False
        assert reply["error"]["code"] == "not_loaded"


async def test_yaml_imports_a_single_entry(hass: HomeAssistant) -> None:
    hass.config.latitude, hass.config.longitude = 48.11, -1.68
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: DEMO_YAML})
    await hass.async_block_till_done()
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.LOADED


async def test_user_flow_and_single_instance(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    if result["type"] is FlowResultType.FORM:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    again = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert again["type"] is FlowResultType.ABORT


async def test_options_hide_the_panel(hass: HomeAssistant) -> None:
    entry = await _setup_demo(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"demo": True, "show_panel": False})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert PANEL_URL_PATH not in hass.data[frontend.DATA_PANELS]


async def test_diagnostics_and_unload(hass: HomeAssistant) -> None:
    entry = await _setup_demo(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_badge_script_is_added(hass: HomeAssistant, stub_frontend) -> None:
    await _setup_demo(hass)
    urls = [call.args[1] for call in stub_frontend.call_args_list]
    assert any("/energy_hub_static/energy-hub-badge.js?v=" in url for url in urls)
