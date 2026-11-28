"""Config flow of Energy Hub: one entry, then the options for the panel and the entities.

The YAML block, when present, creates the entry by itself and wins over these options.

The entities step is the manual substitution: one picker per role, so the detection can be
overridden without writing YAML. A role accepts several entities; they add up for the PV roles
(see config.MULTI_ROLES) and the first one that answers wins for the other roles, which is how an
alternative data source is declared (a Zigbee module instead of the inverter, a Linky instead of
the meter).
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
import yaml
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig, TextSelector, TextSelectorConfig

from .config import INSTALLATION_ITEMS, ROLES, entity_ids
from .const import CONF_DEMO, CONF_ENTITIES, CONF_SHOW_PANEL, DOMAIN


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(CONF_DEMO, default=defaults.get(CONF_DEMO, False)): bool,
            vol.Optional(CONF_SHOW_PANEL, default=defaults.get(CONF_SHOW_PANEL, True)): bool,
        }
    )


def _entities_schema(entities: dict[str, list[str]]) -> vol.Schema:
    """One entity picker per role: several entities allowed (added up or used as a fallback)."""
    fields: dict[Any, Any] = {}
    for role in ROLES:
        fields[vol.Optional(role, default=list(entities.get(role) or []))] = EntitySelector(
            EntitySelectorConfig(multiple=True)
        )
    return vol.Schema(fields)


def _installation_text(values: Any) -> str:
    """A declared list as YAML text (what the box shows): empty when nothing is declared."""
    if isinstance(values, str):
        return values
    if not values:
        return ""
    return yaml.safe_dump(list(values), sort_keys=False, allow_unicode=True).strip()


def _installation_schema(values: dict[str, Any]) -> vol.Schema:
    """One YAML box per list: planes, strings, panels. Empty text removes the key."""
    fields: dict[Any, Any] = {}
    for key in INSTALLATION_ITEMS:
        fields[vol.Optional(key, default=_installation_text(values.get(key)))] = TextSelector(
            TextSelectorConfig(multiline=True)
        )
    return vol.Schema(fields)


class EnergyHubConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Energy Hub", data={}, options=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema({}))

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Energy Hub", data={}, options={})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return EnergyHubOptionsFlow()


class EnergyHubOptionsFlow(OptionsFlow):
    """The three options screens: the switches, the entities, then the declared installation."""

    def __init__(self) -> None:
        self._options: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._options = dict(user_input)
            return await self.async_step_entities()
        return self.async_show_form(step_id="init", data_schema=_schema(dict(self.config_entry.options)))

    async def async_step_entities(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = dict(self.config_entry.options.get(CONF_ENTITIES) or {})
        if user_input is not None:
            chosen: dict[str, list[str]] = {}
            for role, value in user_input.items():
                ids = entity_ids(value)
                if ids:
                    chosen[role] = ids
            self._options[CONF_ENTITIES] = chosen
            return await self.async_step_installation()
        return self.async_show_form(step_id="entities", data_schema=_entities_schema(current))

    async def async_step_installation(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The planes, the strings and the panels declared here: they win over the YAML block.

        Empty text removes the key, so the YAML block (or the detection) speaks again for that list.
        """
        if user_input is None:
            return self.async_show_form(
                step_id="installation", data_schema=_installation_schema(dict(self.config_entry.options))
            )
        errors: dict[str, str] = {}
        for key, item_schema in INSTALLATION_ITEMS.items():
            text = str(user_input.get(key) or "").strip()
            if not text:
                self._options.pop(key, None)
                continue
            try:
                values = yaml.safe_load(text)
                if values is None:
                    self._options.pop(key, None)
                elif not isinstance(values, list):
                    errors[key] = "invalid_installation"
                else:
                    self._options[key] = [item_schema(item) for item in values]
            except (yaml.YAMLError, vol.Invalid):
                errors[key] = "invalid_installation"
        if errors:
            defaults = {k: (user_input.get(k) if k in errors else self._options.get(k)) for k in INSTALLATION_ITEMS}
            return self.async_show_form(
                step_id="installation", data_schema=_installation_schema(defaults), errors=errors
            )
        return self.async_create_entry(data=self._options)
