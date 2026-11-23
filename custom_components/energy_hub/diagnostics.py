"""Diagnostics: the detected installation and capabilities, never the home's location."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant

from .const import VERSION
from .coordinator import EnergyHubConfigEntry


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: EnergyHubConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    inst = coordinator.installation
    data = coordinator.data or {}
    return {
        "version": VERSION,
        "demo": coordinator.demo,
        "roles": inst.roles,
        "signs": inst.signs,
        "strings": [asdict(u) for u in inst.strings],
        "units": [asdict(u) for u in inst.units],
        "batteries": [asdict(b) for b in inst.batteries],
        "sources": [asdict(s) for s in inst.sources],
        "excluded": inst.excluded,
        "days_of_history": len(coordinator.history.days),
        "kwp": data.get("kwp"),
        "kwp_estimated": data.get("kwp_estimated"),
        "alerts": [a.get("kind") for a in data.get("alerts", [])],
        "trends": data.get("trends"),
    }
