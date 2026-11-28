"""FoxESS Modbus (issue #32): strings, battery SoC / SoH / cycles, a capacity sensor, the Energy dashboard's battery
not added a second time."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_hub.config import parse
from custom_components.energy_hub.const import DOMAIN
from custom_components.energy_hub.coordinator import EnergyHubCoordinator
from custom_components.energy_hub.sources import discover, load_profiles

PLATFORM = "foxess_modbus"
SENSORS = {
    "pv_power_now": ("3.1", "kW"),
    "pv1_power": ("1.9", "kW"),
    "pv1_voltage": ("380", "V"),
    "pv1_current": ("5.0", "A"),
    "pv2_power": ("1.2", "kW"),
    "solar_energy_total": ("8123.4", "kWh"),
    "grid_ct": ("0.4", "kW"),
    "feed_in_energy_total": ("2110.0", "kWh"),
    "grid_consumption_energy_total": ("3005.2", "kWh"),
    "load_power": ("1.6", "kW"),
    "battery_soc": ("64", "%"),
    "battery_soh": ("97", "%"),
    "bms_cycle_count": ("312", None),
    "battery_charge": ("1.1", "kW"),
    "battery_discharge": ("0", "kW"),
    "battery_temp": ("21.5", "°C"),
    "battery_charge_total": ("2950.1", "kWh"),
    "battery_discharge_total": ("2801.7", "kWh"),
    "bms_design_capacity": ("10360", "Wh"),
}


def _inverter(hass: HomeAssistant, prefix: str = "foxessmodbus_") -> str:
    entry = MockConfigEntry(domain=PLATFORM)
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(PLATFORM, "inv1")}, name="FoxESS H1"
    )
    reg = er.async_get(hass)
    for signal, (value, unit) in SENSORS.items():
        object_id = f"{prefix}{signal}"
        reg.async_get_or_create("sensor", PLATFORM, object_id, suggested_object_id=object_id, device_id=device.id)
        hass.states.async_set(f"sensor.{object_id}", value, {"unit_of_measurement": unit} if unit else {})
    return device.id


def _read(hass: HomeAssistant, inst):
    entry = MockConfigEntry(domain=DOMAIN, options={})
    entry.add_to_hass(hass)
    coordinator = EnergyHubCoordinator(hass, entry, parse({}, {}))
    coordinator.installation = inst
    reading, _ages = coordinator._read(dt_util.now())
    return reading


async def test_foxess_modbus_profile(hass: HomeAssistant) -> None:
    _inverter(hass)
    inst = discover(hass, parse({}, {}), None, load_profiles())

    p = "sensor.foxessmodbus_"
    assert inst.roles["pv_power"] == f"{p}pv_power_now"
    assert inst.roles["pv_energy"] == f"{p}solar_energy_total"
    assert inst.roles["grid_power"] == f"{p}grid_ct"
    assert inst.roles["load_power"] == f"{p}load_power"
    assert [s.power for s in inst.strings] == [f"{p}pv1_power", f"{p}pv2_power"]
    (battery,) = inst.batteries
    assert battery.soc == f"{p}battery_soc"
    assert (battery.soh, battery.cycles) == (f"{p}battery_soh", f"{p}bms_cycle_count")
    assert (battery.charge_power, battery.discharge_power) == (f"{p}battery_charge", f"{p}battery_discharge")

    reading = _read(hass, inst)
    assert reading.pv_kw == 3.1  # the inverter's total, the strings are inside it
    (b,) = reading.batteries
    assert b.capacity_kwh == 10.36  # Wh converted
    assert (b.soc, b.soh, b.cycles) == (64.0, 97.0, 312.0)
    assert b.power_kw == 1.1  # charging


async def test_foxess_modbus_without_a_prefix(hass: HomeAssistant) -> None:
    _inverter(hass, prefix="")
    inst = discover(hass, parse({}, {}), None, load_profiles())
    assert inst.roles["pv_power"] == "sensor.pv_power_now"
    assert len(inst.strings) == 2


async def test_yaml_battery_capacity_sensor(hass: HomeAssistant) -> None:
    """`capacity:` reads the capacity from a sensor (kWh / Wh); `capacity_kwh` still wins when both are set."""
    _inverter(hass)
    hass.states.async_set("sensor.my_capacity", "11.2", {"unit_of_measurement": "kWh"})
    yaml = {"batteries": {"house": {"soc": "sensor.foxessmodbus_battery_soc", "capacity": "sensor.my_capacity"}}}
    inst = discover(hass, parse(yaml, {}), None, load_profiles())
    (battery,) = inst.batteries
    assert battery.key == "house"
    assert battery.capacity_entity == "sensor.my_capacity"
    assert _read(hass, inst).batteries[0].capacity_kwh == 11.2

    hass.states.async_set("sensor.my_capacity", "200", {"unit_of_measurement": "Ah"})
    assert _read(hass, inst).batteries[0].capacity_kwh is None  # a charge, not an energy: not read as 200 kWh

    yaml["batteries"]["house"]["capacity_kwh"] = 10
    inst = discover(hass, parse(yaml, {}), None, load_profiles())
    assert _read(hass, inst).batteries[0].capacity_kwh == 10


async def test_energy_dashboard_battery_not_added_twice(hass: HomeAssistant) -> None:
    """The Energy dashboard's battery on the device a profile already read is the same battery (#32)."""
    _inverter(hass)
    reg = er.async_get(hass)
    # A second battery-class sensor on the inverter: the prefs would pick it as another SoC.
    device_id = reg.async_get("sensor.foxessmodbus_battery_soc").device_id
    reg.async_get_or_create(
        "sensor",
        PLATFORM,
        "bms_soc_alt",
        suggested_object_id="foxessmodbus_aaa_soc",
        device_id=device_id,
        original_device_class="battery",
    )
    prefs = {
        "energy_sources": [
            {
                "type": "battery",
                "stat_energy_from": "sensor.foxessmodbus_battery_discharge_total",
                "stat_energy_to": "sensor.foxessmodbus_battery_charge_total",
            }
        ]
    }
    inst = discover(hass, parse({}, {}), prefs, load_profiles())
    assert [b.soc for b in inst.batteries] == ["sensor.foxessmodbus_battery_soc"]
