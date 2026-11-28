"""FusionSolarPlus: the plant total feeds pv_power, each inverter is a string, nothing is counted twice."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_hub.config import parse
from custom_components.energy_hub.const import DOMAIN
from custom_components.energy_hub.coordinator import EnergyHubCoordinator
from custom_components.energy_hub.history import Reading
from custom_components.energy_hub.sources import discover, load_profiles

PLATFORM = "fusionsolarplus"
PLANT_ID = "plant0001"
INVERTERS = (("inv0001", "SUN2000-5KTL-M1 (roof east)"), ("inv0002", "SUN2000-6KTL-L1 (garage)"))


def _device(hass: HomeAssistant, device_name: str, serial: str, values: dict[str, tuple[str, str]]) -> None:
    """One FusionSolarPlus device: sensors whose entity ids follow the integration's `fsp_<serial>_<signal>` scheme."""
    hub = MockConfigEntry(domain=PLATFORM)
    hub.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=hub.entry_id, identifiers={(PLATFORM, serial)}, name=device_name
    )
    reg = er.async_get(hass)
    for signal, (value, unit) in values.items():
        object_id = f"fsp_{serial}_{signal}"
        reg.async_get_or_create("sensor", PLATFORM, object_id, suggested_object_id=object_id, device_id=device.id)
        hass.states.async_set(f"sensor.{object_id}", value, {"unit_of_measurement": unit})


def _installation_with_plant(hass: HomeAssistant) -> None:
    """The plant total plus two inverters, every device name different from the entity-id prefix."""
    _device(
        hass,
        "FusionSolar Plant NE 151700628",
        PLANT_ID,
        {
            "flow_solar_power": ("2.4", "kW"),
            "today_energy": ("11.6", "kWh"),
            "total_energy": ("4821.3", "kWh"),
        },
    )
    _device(
        hass,
        INVERTERS[0][1],
        INVERTERS[0][0],
        {
            "current_active_power": ("1.5", "kW"),
            "rated_power": ("5.0", "kW"),
            "total_energy_produced": ("3120.4", "kWh"),
            "daily_energy": ("7.1", "kWh"),
        },
    )
    _device(
        hass,
        INVERTERS[1][1],
        INVERTERS[1][0],
        {
            "current_active_power": ("0.9", "kW"),
            "total_energy_produced": ("1700.9", "kWh"),
            "daily_energy": ("4.5", "kWh"),
        },
    )


def _read(hass: HomeAssistant, inst) -> Reading:
    entry = MockConfigEntry(domain=DOMAIN, options={})
    entry.add_to_hass(hass)
    coordinator = EnergyHubCoordinator(hass, entry, parse({}, {}))
    coordinator.installation = inst
    reading, _ages = coordinator._read(dt_util.now())
    return reading


async def test_fusionsolarplus_plant_total_drives_pv_power(hass: HomeAssistant) -> None:
    """The plant flow sensor is the installation total and the inverters become strings under it."""
    _installation_with_plant(hass)
    inst = discover(hass, parse({}, {}), None, load_profiles())

    (source,) = [s for s in inst.sources if s.platform == PLATFORM]
    assert source.role == "pv"
    assert inst.roles["pv_power"] == f"sensor.fsp_{PLANT_ID}_flow_solar_power"
    assert inst.roles["pv_energy"] == f"sensor.fsp_{PLANT_ID}_total_energy"
    assert inst.roles["inverter_max_power"] == f"sensor.fsp_{INVERTERS[0][0]}_rated_power"
    assert [s.power for s in inst.strings] == [
        f"sensor.fsp_{INVERTERS[0][0]}_current_active_power",
        f"sensor.fsp_{INVERTERS[1][0]}_current_active_power",
    ]

    reading = _read(hass, inst)
    assert reading.pv_kw == 2.4  # the plant total, not 2.4 + 1.5 + 0.9


async def test_fusionsolarplus_inverters_only_fall_back_to_strings(hass: HomeAssistant) -> None:
    """No plant flow sensor (the integration skips a flow signal whose value is None): the strings add up."""
    _device(hass, "FusionSolar Plant NE 151700628", PLANT_ID, {"today_energy": ("11.6", "kWh")})
    _device(hass, INVERTERS[0][1], INVERTERS[0][0], {"current_active_power": ("1.5", "kW")})
    _device(hass, INVERTERS[1][1], INVERTERS[1][0], {"current_active_power": ("0.9", "kW")})

    inst = discover(hass, parse({}, {}), None, load_profiles())

    assert "pv_power" not in inst.roles
    assert len(inst.strings) == 2
    assert _read(hass, inst).pv_kw == 2.4
