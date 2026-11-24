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


async def test_alerts_go_to_notify_hub_in_the_user_language(hass: HomeAssistant) -> None:
    from homeassistant.core import ServiceCall

    entry = await _setup_demo(hass)
    coordinator = entry.runtime_data
    calls: list[ServiceCall] = []
    hass.services.async_register("notify", "send_message", calls.append)
    assert coordinator.notify_target is None
    hass.states.async_set("notify.notify_hub", "unknown")
    assert coordinator.notify_target == "notify.notify_hub"

    hass.config.language = "fr"
    text = await coordinator._async_alert_text({"kind": "clipping", "kwh": 2.3})
    assert text == "Écrêtage de l'onduleur aujourd'hui : 2.3 kWh perdus."
    hass.config.language = "pt-BR"
    text = await coordinator._async_alert_text({"kind": "string_lagging", "name": "String 2", "relative": 0.84})
    assert text == "String 2 produz 16 % menos do que os outros."

    await coordinator._async_notify("notify.notify_hub", text)
    await hass.async_block_till_done()
    assert calls[0].data == {"entity_id": "notify.notify_hub", "title": "Energy Hub", "message": text}


async def test_legacy_notify_action(hass: HomeAssistant) -> None:
    from homeassistant.core import ServiceCall

    entry = await _setup_demo(hass)
    calls: list[ServiceCall] = []
    hass.services.async_register("notify", "mobile_app_phone", calls.append)
    await entry.runtime_data._async_notify("notify.mobile_app_phone", "hello")
    await hass.async_block_till_done()
    assert calls[0].data == {"title": "Energy Hub", "message": "hello"}


async def test_tarif_edf_irradiance_and_weather_are_detected(hass: HomeAssistant) -> None:
    """A real installation: price and contract from Tarif EDF, an irradiance sensor, a weather entity."""
    from datetime import datetime, timedelta, timezone

    from homeassistant.helpers import entity_registry as er

    hass.config.latitude, hass.config.longitude = 48.11, -1.68
    reg = er.async_get(hass)
    reg.async_get_or_create("sensor", "tarif_edf", "price", suggested_object_id="tarif_actuel_tempo_9kva_ttc")
    reg.async_get_or_create("sensor", "tarif_edf", "color", suggested_object_id="tarif_tempo_couleur")
    reg.async_get_or_create(
        "sensor", "ecowitt", "rad", suggested_object_id="solar_radiation", original_device_class="irradiance"
    )
    hass.states.async_set("sensor.tarif_actuel_tempo_9kva_ttc", "0.1654")
    hass.states.async_set("sensor.tarif_tempo_couleur", "bleu")
    hass.states.async_set("sensor.solar_radiation", "400", {"unit_of_measurement": "W/m²"})
    hass.states.async_set("weather.home", "cloudy", {"cloud_coverage": 80})
    hass.states.async_set("sensor.pv", "2000", {"unit_of_measurement": "W"})
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, options={"demo": False, "show_panel": False})
    entry.add_to_hass(hass)
    config = {"planes": [{"kwp": 6}], "entities": {"pv_power": "sensor.pv"}}
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: config})
    await hass.async_block_till_done()
    coordinator = entry.runtime_data
    inst = coordinator.installation
    assert inst.roles["irradiance"] == "sensor.solar_radiation"
    assert inst.roles["weather"] == "weather.home"
    assert inst.tariff == {"contract": "tempo", "kva": 9}
    assert {s.role for s in inst.sources} >= {"tariff", "weather"}

    noon = datetime(2026, 6, 21, 13, 50, tzinfo=timezone(timedelta(hours=2)))
    clear = coordinator._clearsky(noon)
    expected, ref = coordinator._expected(noon, clear, None)
    assert ref == "measured" and 0.35 * clear < expected < 0.5 * clear
    hass.states.async_set("sensor.solar_radiation", "unavailable")
    expected, ref = coordinator._expected(noon, clear, 1.2)
    assert (expected, ref) == (1.2, "forecast")
    expected, ref = coordinator._expected(noon, clear, None)
    assert ref == "weather" and abs(expected - clear * (1 - 0.75 * 0.8**3.4)) < 1e-9
    assert coordinator._price(noon, "blue") == 0.1654
    hass.states.async_set("sensor.tarif_actuel_tempo_9kva_ttc", "unavailable")
    assert coordinator._price(noon, "red") == 0.7295  # the embedded grid, a red peak hour

    snap = coordinator.data
    assert snap["finances"]["comparator"]["contract"] == "tempo"
    assert snap["reference"]["irradiance"] == "sensor.solar_radiation"


async def test_hoymiles_battery_power_from_charge_and_discharge(hass: HomeAssistant) -> None:
    """Hoymiles S-Miles Home: an unsigned battery power, the direction from the charge / discharge sensors."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er
    from homeassistant.util import dt as dt_util

    hass.config.latitude, hass.config.longitude = 48.11, -1.68
    hub = MockConfigEntry(domain="hoymiles_home")
    hub.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=hub.entry_id, identifiers={("hoymiles_home", "station_1")}, name="S-Miles Home 1"
    )
    reg = er.async_get(hass)
    values = {
        "pv_power": "800",
        "load_power": "300",
        "grid_power": "0",
        "battery_power": "500",
        "battery_charge_power": "0",
        "battery_discharge_power": "500",
        "battery_state_of_charge": "62",
    }
    for key, value in values.items():
        object_id = f"s_miles_home_1_{key}"
        reg.async_get_or_create("sensor", "hoymiles_home", key, suggested_object_id=object_id, device_id=device.id)
        hass.states.async_set(
            f"sensor.{object_id}", value, {"unit_of_measurement": "%" if key.endswith("of_charge") else "W"}
        )
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, options={"demo": False, "show_panel": False})
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: {"planes": [{"kwp": 1.6}]}})
    await hass.async_block_till_done()
    coordinator = entry.runtime_data
    inst = coordinator.installation
    assert inst.roles["pv_power"] == "sensor.s_miles_home_1_pv_power"
    assert inst.roles["load_power"] == "sensor.s_miles_home_1_load_power"
    (battery,) = inst.batteries
    assert battery.soc == "sensor.s_miles_home_1_battery_state_of_charge"
    assert battery.power is None
    assert battery.charge_power == "sensor.s_miles_home_1_battery_charge_power"
    reading, _ = coordinator._read(dt_util.now())
    assert reading.batteries[0].power_kw == -0.5
    assert reading.batteries[0].soc == 62
