"""Sensors of Energy Hub: the indicators the panel computes, with long-term statistics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION
from .coordinator import EnergyHubConfigEntry, EnergyHubCoordinator


def _pct(value: float | None) -> float | None:
    return None if value is None else round(value * 100, 1)


@dataclass(frozen=True, kw_only=True)
class HubSensorDescription(SensorEntityDescription):
    value: Callable[[dict[str, Any]], Any]
    attrs: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSORS: tuple[HubSensorDescription, ...] = (
    HubSensorDescription(
        key="self_consumption",
        translation_key="self_consumption",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-lightning-bolt",
        value=lambda d: _pct(d["today"]["self_consumption"]),
    ),
    HubSensorDescription(
        key="self_sufficiency",
        translation_key="self_sufficiency",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:shield-sun",
        value=lambda d: _pct(d["today"]["self_sufficiency"]),
    ),
    HubSensorDescription(
        key="pv_energy_today",
        translation_key="pv_energy_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        value=lambda d: d["today"]["pv_kwh"],
    ),
    HubSensorDescription(
        key="specific_yield",
        translation_key="specific_yield",
        native_unit_of_measurement="kWh/kWp",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power-variant",
        value=lambda d: d["today"]["specific_yield"],
    ),
    HubSensorDescription(
        key="performance_index",
        translation_key="performance_index",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:target",
        value=lambda d: _pct(d["today"]["epi"]),
    ),
    HubSensorDescription(
        key="losses_today",
        translation_key="losses_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:trending-down",
        value=lambda d: round(
            sum(v or 0 for k, v in d["losses"]["today"].items() if k not in ("potential", "produced")), 2
        ),
        attrs=lambda d: {k: v for k, v in d["losses"]["today"].items() if k not in ("potential", "produced")},
    ),
    HubSensorDescription(
        key="clipping_today",
        translation_key="clipping_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:chart-bell-curve",
        value=lambda d: d["losses"]["today"]["clipping"],
    ),
    HubSensorDescription(
        key="battery_soc",
        translation_key="battery_soc",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda d: (
            round(d["batteries"]["fleet"]["soc"], 1)
            if d["batteries"]["fleet"] and d["batteries"]["fleet"]["soc"] is not None
            else None
        ),
        attrs=lambda d: {
            "batteries": [
                {"name": b["name"], "soc": b["soc"], "power_kw": b["power_kw"]} for b in d["batteries"]["items"]
            ]
        },
    ),
    HubSensorDescription(
        key="battery_power",
        translation_key="battery_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda d: d["live"]["battery_kw"],
    ),
    HubSensorDescription(
        key="battery_autonomy",
        translation_key="battery_autonomy",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer-sand",
        value=lambda d: d["batteries"]["autonomy_h"],
    ),
    HubSensorDescription(
        key="savings_today",
        translation_key="savings_today",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:piggy-bank-outline",
        value=lambda d: d["finances"]["today"],
    ),
    HubSensorDescription(
        key="alerts",
        translation_key="alerts",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:bell-alert-outline",
        value=lambda d: len(d["alerts"]),
        attrs=lambda d: {"alerts": d["alerts"]},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: EnergyHubConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(HubSensor(coordinator, description) for description in SENSORS)


class HubSensor(CoordinatorEntity[EnergyHubCoordinator], SensorEntity):
    _attr_has_entity_name = True
    entity_description: HubSensorDescription

    def __init__(self, coordinator: EnergyHubCoordinator, description: HubSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        if description.device_class is SensorDeviceClass.MONETARY:
            self._attr_native_unit_of_measurement = coordinator.cfg.currency
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)},
            name="Energy Hub",
            manufacturer="juju35",
            model="Demo" if coordinator.demo else "Energy Hub",
            sw_version=VERSION,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.coordinator.data is None or self.entity_description.attrs is None:
            return None
        return self.entity_description.attrs(self.coordinator.data)
