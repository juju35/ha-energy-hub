"""Large consumers: the YAML, the detection from the Energy dashboard, and what a day records for them."""

from __future__ import annotations

from datetime import datetime

import pytest
import voluptuous as vol

from custom_components.energy_hub.config import parse
from custom_components.energy_hub.history import ConsumerReading, History, Reading
from custom_components.energy_hub.sources import Installation, _apply_yaml, consumer_kind

NOW = datetime(2026, 7, 17, 12, 0)


def test_yaml_consumers_are_parsed() -> None:
    cfg = parse(
        {
            "consumers": {
                "wallbox": {"power": "sensor.wallbox_power", "kind": "ev_charger"},
                "heat_pump": {"energy": "sensor.hp_energy", "import_price": 0.24, "separate_meter": True},
            }
        }
    )
    wallbox, heat_pump = cfg.consumers
    assert (wallbox.name, wallbox.kind, wallbox.import_price, wallbox.separate_meter) == (
        "Wallbox",
        "ev_charger",
        None,
        False,
    )
    assert (heat_pump.name, heat_pump.import_price, heat_pump.separate_meter) == ("Heat pump", 0.24, True)


def test_a_consumer_needs_an_entity() -> None:
    with pytest.raises(vol.Invalid):
        parse({"consumers": {"wallbox": {"name": "Wallbox"}}})


def test_kind_guessed_from_the_entity_id() -> None:
    assert consumer_kind("sensor.easee_home_power") == "ev_charger"
    assert consumer_kind("sensor.heat_pump_energy") == "heat_pump"
    assert consumer_kind("sensor.chauffe_eau_power") == "water_heater"
    assert consumer_kind("sensor.fridge_power") == "other"


def test_yaml_completes_a_detected_consumer() -> None:
    from custom_components.energy_hub.sources import ConsumerSource

    inst = Installation(consumers=[ConsumerSource("device_0", "Wallbox", "energy", energy="sensor.wb_energy")])
    cfg = parse({"consumers": {"car": {"energy": "sensor.wb_energy", "import_price": 0.2}}})
    _apply_yaml(cfg, inst, [])
    assert len(inst.consumers) == 1
    car = inst.consumers[0]
    assert (car.key, car.import_price, car.platform) == ("car", 0.2, "energy")


def _feed(consumers: dict[str, ConsumerReading], load: float, grid: float, pv: float) -> dict:
    history = History()
    for minute in (0, 15, 30, 45, 60):  # readings 15 minutes apart: one hour integrated
        t = NOW.replace(minute=0).timestamp() + minute * 60
        history.add(
            Reading(t=t, pv_kw=pv, load_kw=load, grid_kw=grid, consumers=consumers, import_price=0.20),
            datetime.fromtimestamp(t),
        )
    return history.day(NOW.date())


def test_a_consumer_on_the_main_meter_gets_the_home_solar_share() -> None:
    # 4 kW at home, 1 kW from the grid: 75 % solar; the 2 kW wallbox is priced at its own 0.10 for its grid part.
    day = _feed({"wb": ConsumerReading(2.0, 0.10)}, load=4.0, grid=1.0, pv=3.0)
    kwh, solar, eur = day["consumers"]["wb"]
    assert kwh == pytest.approx(2.0)
    assert solar == pytest.approx(1.5)
    assert eur == pytest.approx(0.5 * 0.10)
    # The main bill: 1 kWh at 0.20, of which the wallbox's 0.5 kWh at 0.10 instead
    assert day["import_eur"] == pytest.approx(0.20 - 0.5 * 0.10)


def test_a_consumer_on_its_own_meter_is_bought_apart() -> None:
    # The home is all solar, the heat pump (1 kW, own meter) is outside the main meter but counted in the load.
    day = _feed({"hp": ConsumerReading(1.0, 0.18, separate_meter=True)}, load=3.0, grid=0.0, pv=2.0)
    kwh, solar, eur = day["consumers"]["hp"]
    assert (kwh, solar) == (pytest.approx(1.0), 0.0)
    assert eur == pytest.approx(0.18)
    assert day["import"] == pytest.approx(1.0)
    assert day["import_eur"] == pytest.approx(0.18)
    assert "imp48" not in day or sum(day["imp48"]) == 0


def test_power_derived_from_the_energy_when_no_power_entity() -> None:
    from types import SimpleNamespace

    from homeassistant.core import State

    from custom_components.energy_hub.coordinator import EnergyHubCoordinator
    from custom_components.energy_hub.sources import ConsumerSource

    states = {"sensor.hp_energy": State("sensor.hp_energy", "1000", {"unit_of_measurement": "Wh"})}
    fake = SimpleNamespace(
        hass=SimpleNamespace(states=SimpleNamespace(get=states.get)),
        installation=Installation(consumers=[ConsumerSource("hp", "Heat pump", "yaml", energy="sensor.hp_energy")]),
        _energy_seen={},
    )
    read = EnergyHubCoordinator._consumers
    assert read(fake, 0.0)["hp"].kw is None  # first value: no slope yet
    states["sensor.hp_energy"] = State("sensor.hp_energy", "1500", {"unit_of_measurement": "Wh"})
    assert read(fake, 1800.0)["hp"].kw == pytest.approx(1.0)  # 0.5 kWh in half an hour
    assert read(fake, 1830.0)["hp"].kw == pytest.approx(1.0)  # unchanged: the last slope holds
    assert read(fake, 1800.0 + 901)["hp"].kw == 0.0  # still for 15 minutes: idle
