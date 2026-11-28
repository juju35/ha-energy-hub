"""The integration in demo mode: setup from the UI and from YAML, sensors, websocket commands, panel, unload."""

from __future__ import annotations

import pytest
from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_hub.config import parse
from custom_components.energy_hub.const import (
    CONF_ENTITIES,
    CONF_PANELS,
    CONF_PLANES,
    CONF_STRINGS,
    DOMAIN,
    PANEL_URL_PATH,
)
from custom_components.energy_hub.coordinator import EnergyHubCoordinator
from custom_components.energy_hub.diagnostics import async_get_config_entry_diagnostics
from custom_components.energy_hub.sources import Installation, _apply_yaml

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


async def test_entities_can_be_chosen_in_the_options(hass: HomeAssistant) -> None:
    entry = await _setup_demo(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"demo": True, "show_panel": True})
    assert result["step_id"] == "entities"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"grid_power": ["sensor.solaire_zigbee_power"], "pv_power": ["sensor.pv_a", "sensor.pv_b"]},
    )
    assert result["step_id"] == "installation"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_ENTITIES] == {
        "grid_power": ["sensor.solaire_zigbee_power"],
        "pv_power": ["sensor.pv_a", "sensor.pv_b"],
    }


async def test_the_installation_can_be_declared_in_the_options(hass: HomeAssistant) -> None:
    entry = await _setup_demo(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"demo": True, "show_panel": True})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["step_id"] == "installation"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "strings": "- name: Toit sud\n  power: sensor.pv_sud\n  kwp: 1.5\n  tilt: 30\n  azimuth: 200\n",
            "panels": "- name: Garage\n  power: sensor.pv_garage\n  kwp: 0.4\n  count_in_total: false\n",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert CONF_PLANES not in result["data"]  # an empty box keeps the YAML block
    strings = result["data"][CONF_STRINGS]
    assert (strings[0]["name"], strings[0]["kwp"], strings[0]["tilt"], strings[0]["azimuth"]) == (
        "Toit sud",
        1.5,
        30.0,
        200.0,
    )
    panels = result["data"][CONF_PANELS]
    assert (panels[0]["name"], panels[0]["count_in_total"]) == ("Garage", False)


async def test_an_invalid_installation_box_is_shown_again(hass: HomeAssistant) -> None:
    entry = await _setup_demo(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"demo": True, "show_panel": True})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"strings": "name: pas une liste"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "installation"
    assert result["errors"] == {"strings": "invalid_installation"}


async def test_websocket_set_installation_saves_the_declaration(hass: HomeAssistant, hass_ws_client) -> None:
    entry = await _setup_demo(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "energy_hub/set_installation",
            "planes": [{"kwp": 3.28, "tilt": 30, "azimuth": 190}],
            "strings": [{"name": "Toit sud", "power": "sensor.pv_sud", "kwp": 1.5, "tilt": 30, "azimuth": 200}],
            "panels": [{"name": "Garage", "power": "sensor.pv_garage", "kwp": 0.4, "count_in_total": False}],
        }
    )
    reply = await client.receive_json()
    assert reply["success"] is True
    await hass.async_block_till_done()
    options = hass.config_entries.async_get_entry(entry.entry_id).options
    assert [p["kwp"] for p in options[CONF_PLANES]] == [3.28]
    assert options[CONF_STRINGS][0]["name"] == "Toit sud"
    assert options[CONF_STRINGS][0]["tilt"] == 30
    assert options[CONF_PANELS][0]["count_in_total"] is False
    assert reply["result"][CONF_PANELS][0]["name"] == "Garage"

    # An empty list removes the declaration: the YAML block (or the detection) applies again.
    await client.send_json_auto_id({"type": "energy_hub/set_installation", "planes": [], "strings": []})
    assert (await client.receive_json())["success"] is True
    await hass.async_block_till_done()
    options = hass.config_entries.async_get_entry(entry.entry_id).options
    assert CONF_PLANES not in options
    assert CONF_STRINGS not in options
    assert options[CONF_PANELS][0]["name"] == "Garage"


async def test_websocket_set_installation_rejects_an_invalid_entity(hass: HomeAssistant, hass_ws_client) -> None:
    await _setup_demo(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "energy_hub/set_installation", "strings": [{"name": "Toit", "power": "pas_une_entite"}]}
    )
    reply = await client.receive_json()
    assert reply["success"] is False
    assert reply["error"]["code"] == "invalid_format"


async def test_websocket_set_installation_needs_an_admin(hass: HomeAssistant, hass_ws_client) -> None:
    from homeassistant.auth.const import GROUP_ID_USER

    entry = await _setup_demo(hass)
    user = await hass.auth.async_create_user("limited", group_ids=[GROUP_ID_USER])
    token = hass.auth.async_create_access_token(await hass.auth.async_create_refresh_token(user, "test"))
    client = await hass_ws_client(hass, token)
    await client.send_json_auto_id({"type": "energy_hub/set_installation", "planes": [{"kwp": 1.0}]})
    reply = await client.receive_json()
    assert reply["success"] is False
    assert reply["error"]["code"] == "unauthorized"
    assert CONF_PLANES not in hass.config_entries.async_get_entry(entry.entry_id).options


async def test_websocket_set_entities_saves_the_substitution(hass: HomeAssistant, hass_ws_client) -> None:
    entry = await _setup_demo(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "energy_hub/set_entities", "roles": {"grid_power": "sensor.solaire_zigbee_power", "pv_power": None}}
    )
    assert (await client.receive_json())["success"] is True
    await hass.async_block_till_done()
    options = hass.config_entries.async_get_entry(entry.entry_id).options
    assert options[CONF_ENTITIES] == {"grid_power": ["sensor.solaire_zigbee_power"]}


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
    assert result["step_id"] == "entities"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["step_id"] == "installation"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
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


def _registry_sensors(hass: HomeAssistant, platform: str, device_name: str, values: dict[str, str], prefix: str):
    """One device of `platform` carrying a sensor per object id suffix, with its state."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    hub = MockConfigEntry(domain=platform)
    hub.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=hub.entry_id, identifiers={(platform, device_name)}, name=device_name
    )
    reg = er.async_get(hass)
    for key, value in values.items():
        object_id = f"{prefix}_{key}"
        reg.async_get_or_create("sensor", platform, object_id, suggested_object_id=object_id, device_id=device.id)
        unit = (
            "%" if "soc" in key else "kWh" if "energy" in key or key.endswith(("east", "eait", "hchc", "hchp")) else "W"
        )
        hass.states.async_set(f"sensor.{object_id}", value, {"unit_of_measurement": unit})


async def _setup_real(hass: HomeAssistant) -> MockConfigEntry:
    hass.config.latitude, hass.config.longitude = 48.11, -1.68
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, options={"demo": False, "show_panel": False})
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: {"planes": [{"kwp": 1.6}]}})
    await hass.async_block_till_done()
    return entry


async def test_indevolt_core_integration(hass: HomeAssistant) -> None:
    """Indevolt (core integration, one device): the pack SOC is not the battery, the home load is derived."""
    from homeassistant.util import dt as dt_util

    values = {
        "dc_output_power": "800",
        "dc_input_power_1": "420",
        "dc_input_power_2": "380",
        "cumulative_production": "1234.5",
        "ac_output_power": "500",
        "meter_power": "200",
        "battery_power": "300",
        "battery_soc": "62",
        "main_soc": "61",
        "battery_pack_1_soc": "63",
        "main_temperature": "24",
        "equivalent_full_cycles": "57",
        "rated_capacity": "2",
    }
    _registry_sensors(hass, "indevolt", "Indevolt PG2000", values, "pg2000")
    coordinator = (await _setup_real(hass)).runtime_data
    inst = coordinator.installation
    assert inst.roles["pv_power"] == "sensor.pg2000_dc_output_power"
    assert inst.roles["pv_energy"] == "sensor.pg2000_cumulative_production"
    assert inst.roles["grid_power"] == "sensor.pg2000_meter_power"
    assert "load_power" not in inst.roles  # the AC output is not the home load
    assert [s.power for s in inst.strings] == ["sensor.pg2000_dc_input_power_1", "sensor.pg2000_dc_input_power_2"]
    (battery,) = inst.batteries
    assert battery.soc == "sensor.pg2000_battery_soc"
    assert battery.temperature == "sensor.pg2000_main_temperature"
    assert battery.cycles == "sensor.pg2000_equivalent_full_cycles"
    reading, _ = coordinator._read(dt_util.now())
    assert abs(reading.load_kw - 0.7) < 1e-9  # 0.8 PV + 0.2 grid - 0.3 charging


async def test_indevolt_custom_integration_packs_stay_out(hass: HomeAssistant) -> None:
    """Indevolt custom integration (GEN2): the packs live on their own devices and are not counted as batteries."""
    main = {"total_dc_output_power": "600", "meter_power": "0", "battery_soc_total": "55", "battery_soc_mb": "54"}
    _registry_sensors(hass, "indevolt", "PG2000 (SN1)", main, "pg2000_sn1")
    pack = {"battery_soc_pack1": "56", "battery_temp_pack1": "22"}
    _registry_sensors(hass, "indevolt", "SFA/PFA Battery Pack 1 (SN2)", pack, "sfa_pfa_battery_pack_1_sn2")
    inst = (await _setup_real(hass)).runtime_data.installation
    assert inst.roles["pv_power"] == "sensor.pg2000_sn1_total_dc_output_power"
    (battery,) = inst.batteries
    assert battery.soc == "sensor.pg2000_sn1_battery_soc_total"


async def test_denky_d4_as_linky_meter(hass: HomeAssistant) -> None:
    """Denky D4 (Tasmota Teleinfo): SINSTS before PAPP, EAST before the ENERGY total; other Tasmota devices ignored."""
    denky = {"tic_sinsts": "900", "tic_papp": "910", "tic_east": "15234", "tic_eait": "12", "energy_total": "15234"}
    _registry_sensors(hass, "tasmota", "Denky D4", denky, "denky_d4")
    _registry_sensors(hass, "tasmota", "Garage plug", {"energy_total": "42", "energy_power": "60"}, "garage_plug")
    inst = (await _setup_real(hass)).runtime_data.installation
    assert inst.roles["grid_power"] == "sensor.denky_d4_tic_sinsts"
    assert inst.roles["grid_import_energy"] == "sensor.denky_d4_tic_east"
    assert inst.roles["grid_export_energy"] == "sensor.denky_d4_tic_eait"
    assert not any("garage_plug" in e for e in inst.roles.values())


async def test_denky_d4_off_peak_meter_uses_the_energy_total(hass: HomeAssistant) -> None:
    """A Denky on an HC/HP meter in historical mode: the import is Tasmota's total, not the off-peak index alone."""
    denky = {"tic_papp": "700", "tic_hchc": "8000", "tic_hchp": "6000", "energy_total": "14000"}
    _registry_sensors(hass, "tasmota", "teleinfo-garage", denky, "teleinfo_garage")
    inst = (await _setup_real(hass)).runtime_data.installation
    assert inst.roles["grid_power"] == "sensor.teleinfo_garage_tic_papp"
    assert inst.roles["grid_import_energy"] == "sensor.teleinfo_garage_energy_total"


async def test_the_settings_payload_lists_the_declared_units(hass: HomeAssistant, hass_ws_client) -> None:
    await _setup_real(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "energy_hub/set_installation",
            "planes": [{"kwp": 3.28}],
            "strings": [{"name": "Toit sud", "power": "sensor.pv_sud", "kwp": 1.5, "tilt": 30, "azimuth": 200}],
            "panels": [
                {
                    "name": "Garage",
                    "voltage": "sensor.u_garage",
                    "current": "sensor.i_garage",
                    "kwp": 0.4,
                    "count_in_total": False,
                }
            ],
        }
    )
    assert (await client.receive_json())["success"] is True
    await hass.async_block_till_done()
    await client.send_json_auto_id({"type": "energy_hub/settings"})
    settings = (await client.receive_json())["result"]
    # The strings and panels sit on the declared plane: the capacity is the plane's, not counted twice.
    assert settings["kwp"] == pytest.approx(3.28)
    assert settings["strings"][0] == {
        "name": "Toit sud",
        "declared": True,
        "kwp": 1.5,
        "tilt": 30.0,
        "azimuth": 200.0,
        "power": "sensor.pv_sud",
        "voltage": None,
        "current": None,
        "count_in_total": None,
    }
    panel = settings["panels"][0]
    assert (panel["name"], panel["voltage"], panel["current"], panel["kwp"]) == (
        "Garage",
        "sensor.u_garage",
        "sensor.i_garage",
        0.4,
    )
    assert (panel["tilt"], panel["azimuth"], panel["count_in_total"]) == (None, None, False)


def _pv_coordinator(hass: HomeAssistant, yaml: dict):
    entry = MockConfigEntry(domain=DOMAIN, options={})
    entry.add_to_hass(hass)
    cfg = parse(yaml, {})
    coordinator = EnergyHubCoordinator(hass, entry, cfg)
    coordinator.installation = Installation()
    _apply_yaml(cfg, coordinator.installation, ["sensor.plant_power", "sensor.string_power", "sensor.other_power"])
    return coordinator


async def test_the_pv_total_adds_a_declared_string_the_role_does_not_read(hass: HomeAssistant) -> None:
    """The plant meter already counts a string wired behind it: only the units outside the role are added."""
    coordinator = _pv_coordinator(
        hass,
        {
            "entities": {"pv_power": "sensor.plant_power"},
            "strings": [
                {"name": "Toit sud", "power": "sensor.string_power", "count_in_total": True},
                {"name": "Toit nord", "power": "sensor.plant_power", "count_in_total": True},
                {"name": "Hors total", "power": "sensor.other_power", "count_in_total": False},
            ],
        },
    )
    hass.states.async_set("sensor.plant_power", "2000", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.string_power", "500", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.other_power", "700", {"unit_of_measurement": "W"})
    reading, _ages = coordinator._read(dt_util.now())
    assert reading.pv_kw == 2.5


async def test_a_string_declared_the_1_9_way_is_not_added_on_top_of_the_meter(hass: HomeAssistant) -> None:
    """A 1.9.0 YAML names the MPPT strings behind the inverter's meter: no count_in_total, no double count."""
    coordinator = _pv_coordinator(
        hass,
        {
            "entities": {"pv_power": "sensor.plant_power"},
            "strings": [{"name": "MPPT 1", "power": "sensor.string_power"}],
        },
    )
    hass.states.async_set("sensor.plant_power", "2000", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.string_power", "500", {"unit_of_measurement": "W"})
    reading, _ages = coordinator._read(dt_util.now())
    assert reading.pv_kw == 2.0


async def test_the_units_sum_leaves_out_a_string_kept_out_of_the_total(hass: HomeAssistant) -> None:
    coordinator = _pv_coordinator(
        hass,
        {
            "strings": [
                {"name": "Toit", "power": "sensor.string_power"},
                {"name": "Abri", "power": "sensor.other_power", "count_in_total": False},
            ]
        },
    )
    hass.states.async_set("sensor.string_power", "500", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.other_power", "700", {"unit_of_measurement": "W"})
    reading, _ages = coordinator._read(dt_util.now())
    assert reading.pv_kw == 0.5


async def test_the_pv_total_falls_back_to_the_units_without_a_role(hass: HomeAssistant) -> None:
    coordinator = _pv_coordinator(hass, {"strings": [{"name": "Toit", "power": "sensor.string_power", "kwp": 1.5}]})
    hass.states.async_set("sensor.string_power", "500", {"unit_of_measurement": "W"})
    reading, _ages = coordinator._read(dt_util.now())
    assert reading.pv_kw == 0.5
