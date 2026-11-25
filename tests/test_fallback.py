"""The alternative sources at read time: fallback per role, offline status, what the panel edits."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_hub.config import parse
from custom_components.energy_hub.const import CONF_ENTITIES, DOMAIN, STALE_SECONDS
from custom_components.energy_hub.coordinator import EnergyHubCoordinator
from custom_components.energy_hub.sources import Installation


def _coordinator(hass: HomeAssistant, options: dict | None = None, yaml: dict | None = None) -> EnergyHubCoordinator:
    entry = MockConfigEntry(domain=DOMAIN, options=options or {})
    entry.add_to_hass(hass)
    return EnergyHubCoordinator(hass, entry, parse(yaml or {}, options or {}))


async def test_a_fallback_tariff_colour_and_price_are_read(hass: HomeAssistant) -> None:
    coordinator = _coordinator(hass)
    coordinator.installation = Installation(
        roles={"tariff_color": "sensor.edf_color", "tariff_price": "sensor.edf_price"},
        alternatives={"tariff_color": ["sensor.rte_color"], "tariff_price": ["sensor.zen_price"]},
    )
    hass.states.async_set("sensor.edf_color", "unavailable")
    hass.states.async_set("sensor.rte_color", "red")
    hass.states.async_set("sensor.edf_price", "unknown")
    hass.states.async_set("sensor.zen_price", "0.2")
    assert coordinator._role_state("tariff_color").state == "red"
    assert coordinator._price(dt_util.now(), None) == 0.2


async def test_a_fallback_that_answers_keeps_the_grid_online(hass: HomeAssistant) -> None:
    coordinator = _coordinator(hass)
    coordinator.installation = Installation(
        roles={"grid_power": "sensor.meter_power"}, alternatives={"grid_power": ["sensor.zlinky_power"]}
    )
    hass.states.async_set("sensor.meter_power", "unavailable")
    hass.states.async_set("sensor.zlinky_power", "850", {"unit_of_measurement": "W"})
    later = dt_util.now() + timedelta(seconds=STALE_SECONDS + 60)
    reading, _ages = coordinator._read(later)
    assert reading.grid_kw == 0.85
    assert reading.offline is False


async def test_one_stale_array_marks_the_added_up_production_offline(hass: HomeAssistant) -> None:
    coordinator = _coordinator(hass)
    coordinator.installation = Installation(
        roles={"pv_power": "sensor.pv_a"}, alternatives={"pv_power": ["sensor.pv_b"]}
    )
    hass.states.async_set("sensor.pv_a", "1200", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.pv_b", "unavailable")
    later = dt_util.now() + timedelta(seconds=STALE_SECONDS + 60)
    reading, _ages = coordinator._read(later)
    assert reading.pv_kw == 1.2
    assert reading.offline is True


async def test_the_panel_edits_the_options_not_the_yaml(hass: HomeAssistant) -> None:
    coordinator = _coordinator(
        hass,
        options={CONF_ENTITIES: {"pv_power": ["sensor.pv_a"]}},
        yaml={"entities": {"grid_power": "sensor.yaml_grid"}},
    )
    payload = coordinator._entities_payload()
    assert payload["configured"] == {"pv_power": ["sensor.pv_a"]}
