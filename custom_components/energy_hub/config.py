"""YAML configuration of Energy Hub: everything is optional, the detection fills the rest.

```yaml
energy_hub:
  demo: false
  planes:
    - kwp: 3.0
      tilt: 30
      azimuth: 225
  inverter_max_kw: 4.6
  export_limit_kw: 3
  entities:                     # override a detected role
    pv_power: sensor.inverter_input_power
  batteries:
    maison:
      name: Maison
      soc: sensor.battery_state_of_capacity
      power: sensor.battery_charge_discharge_power
      capacity_kwh: 15
      reserve: 10
      cells: sensor.jk_bms_cell_*
  ignore:
    - sensor.zendure_ac_input
  panels:                       # panels no profile finds (template sensors…); strings: works the same
    - name: TM 1
      power: sensor.solar_tm_l2000m_pv1_power
  consumers:                    # large consumers drawn apart in the curve and the flow
    wallbox:
      name: EV charger
      power: sensor.wallbox_power
      kind: ev_charger            # ev_charger, heat_pump, climate, water_heater, other (icon and colour)
    heat_pump:
      energy: sensor.heat_pump_energy   # power derived from the energy when no power sensor is given
      import_price: 0.24          # its own price per kWh drawn from the grid
      separate_meter: true        # on its own meter: no solar reaches it, outside the main contract
  tariff:
    import: 0.2016              # flat price when no contract is known
    export: 0.04
    contract: tempo             # base, hphc, tempo, zen_weekend, zen_weekend_hc, zen_flex (Tarif EDF: detected)
    kva: 9
    offpeak: "22:00-06:00"      # your Enedis off-peak hours
    price: sensor.tarif_actuel_tempo_9kva_ttc
    color: sensor.rte_tempo_couleur_actuelle
    offers:                     # override the embedded grid, or add an offer to compare
      zen_weekend:
        prices: {week: 0.2285, weekend: 0.1710}
  weather: weather.home         # cloud cover for the expected production (irradiance sensor: entities)
  installation:
    cost: 9800
    subsidy: 1140
    commissioned: 2023-04-12
  notify: notify.notify_hub
```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .analytics.clearsky import Plane
from .analytics.tariffs import CONTRACTS
from .const import (
    CONF_AZIMUTH,
    CONF_BATTERIES,
    CONF_CONSUMERS,
    CONF_DEMO,
    CONF_ENTITIES,
    CONF_EXPORT_LIMIT_KW,
    CONF_FORECAST,
    CONF_IGNORE,
    CONF_INSTALLATION,
    CONF_INVERTER_MAX_KW,
    CONF_KWP,
    CONF_NOTIFY,
    CONF_PANELS,
    CONF_PLANES,
    CONF_SHOW_PANEL,
    CONF_STRINGS,
    CONF_TARIFF,
    CONF_TILT,
    CONF_WEATHER,
)

ROLES = (
    "pv_power",
    "pv_energy",
    "grid_power",
    "grid_import_energy",
    "grid_export_energy",
    "load_power",
    "forecast_power",
    "forecast_energy_today",
    "irradiance",
    "tariff_price",
    "tariff_color",
)
KINDS = ("base", "hphc", "tempo", "weekend", "weekend_hphc", "flex")
OFFPEAK_RE = r"^\s*\d{1,2}:\d{2}-\d{1,2}:\d{2}(\s*,\s*\d{1,2}:\d{2}-\d{1,2}:\d{2})*\s*$"

OFFER_SCHEMA = vol.Schema(
    {
        vol.Optional("name"): cv.string,
        vol.Optional("kind"): vol.In(KINDS),
        vol.Optional("subscription"): vol.Coerce(float),
        vol.Optional("prices", default={}): {cv.string: vol.Coerce(float)},
    }
)

PLANE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_KWP): vol.All(vol.Coerce(float), vol.Range(min=0.05, max=1000)),
        vol.Optional(CONF_TILT, default=30): vol.All(vol.Coerce(float), vol.Range(min=0, max=90)),
        vol.Optional(CONF_AZIMUTH, default=180): vol.All(vol.Coerce(float), vol.Range(min=0, max=360)),
    }
)

MULTI_ROLES = ("pv_power",)  # roles where every entity counts, instead of the first available one


def entity_ids(value: str | list[str] | None) -> list[str]:
    """A role's entities, always as a list: a single entity, or several added together."""
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [e for e in value if e]


def _roles(values: dict[str, Any]) -> dict[str, list[str]]:
    """Keep the roles that got an entity, all as lists."""
    return {role: ids for role, value in values.items() if (ids := entity_ids(value))}


BATTERY_SCHEMA = vol.Schema(
    {
        vol.Optional("name"): cv.string,
        vol.Optional("soc"): cv.entity_id,
        vol.Optional("power"): cv.entity_id,
        vol.Optional("power_sign", default="charge_positive"): vol.In(["charge_positive", "discharge_positive"]),
        vol.Optional("capacity_kwh"): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
        vol.Optional("reserve", default=10): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
        vol.Optional("soh"): cv.entity_id,
        vol.Optional("cycles"): cv.entity_id,
        vol.Optional("temperature"): cv.entity_id,
        vol.Optional("cells"): cv.string,
        vol.Optional("cell_temperatures"): cv.string,
        vol.Optional("cells_per_module"): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)

CONSUMER_KINDS = ("ev_charger", "heat_pump", "climate", "water_heater", "other")


def _power_or_energy(value: dict[str, Any]) -> dict[str, Any]:
    if not value.get("power") and not value.get("energy"):
        raise vol.Invalid("a consumer needs a power or an energy entity")
    return value


CONSUMER_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional("name"): cv.string,
            vol.Optional("power"): cv.entity_id,
            vol.Optional("energy"): cv.entity_id,
            vol.Optional("kind", default="other"): vol.In(CONSUMER_KINDS),
            vol.Optional("import_price"): vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Optional("separate_meter", default=False): cv.boolean,
        }
    ),
    _power_or_energy,
)


def _power_or_voltage_current(value: dict[str, Any]) -> dict[str, Any]:
    if not value.get("power") and not (value.get("voltage") and value.get("current")):
        raise vol.Invalid("a panel or string needs a power entity, or a voltage and a current entity")
    return value


# A panel (micro-inverter input) or a string / MPPT input declared by hand: power, or voltage × current.
UNIT_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required("name"): cv.string,
            vol.Optional("power"): cv.entity_id,
            vol.Optional("voltage"): cv.entity_id,
            vol.Optional("current"): cv.entity_id,
            vol.Optional(CONF_KWP): vol.All(vol.Coerce(float), vol.Range(min=0.01, max=1000)),
        }
    ),
    _power_or_voltage_current,
)

YAML_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DEMO): cv.boolean,
        vol.Optional(CONF_SHOW_PANEL): cv.boolean,
        vol.Optional(CONF_PLANES, default=[]): [PLANE_SCHEMA],
        vol.Optional(CONF_INVERTER_MAX_KW): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
        vol.Optional(CONF_EXPORT_LIMIT_KW): vol.All(vol.Coerce(float), vol.Range(min=0)),
        vol.Optional(CONF_ENTITIES, default={}): {vol.In(ROLES): vol.Any(cv.entity_id, [cv.entity_id])},
        vol.Optional(CONF_BATTERIES, default={}): {cv.slug: BATTERY_SCHEMA},
        vol.Optional(CONF_IGNORE, default=[]): [cv.entity_id],
        vol.Optional(CONF_CONSUMERS, default={}): {cv.slug: CONSUMER_SCHEMA},
        vol.Optional(CONF_FORECAST, default=[]): [cv.entity_id],
        vol.Optional(CONF_PANELS, default=[]): [UNIT_SCHEMA],
        vol.Optional(CONF_STRINGS, default=[]): [UNIT_SCHEMA],
        vol.Optional(CONF_TARIFF, default={}): vol.Schema(
            {
                vol.Optional("import", default=0.2016): vol.Coerce(float),
                vol.Optional("export", default=0.04): vol.Coerce(float),
                vol.Optional("currency", default="EUR"): cv.string,
                vol.Optional("contract"): vol.In(CONTRACTS),
                vol.Optional("kva"): vol.All(vol.Coerce(int), vol.Range(min=3, max=36)),
                vol.Optional("offpeak"): vol.Match(OFFPEAK_RE),
                vol.Optional("price"): cv.entity_id,
                vol.Optional("color"): cv.entity_id,
                vol.Optional("offers", default={}): {cv.slug: OFFER_SCHEMA},
            }
        ),
        vol.Optional(CONF_INSTALLATION, default={}): vol.Schema(
            {
                vol.Optional("cost"): vol.Coerce(float),
                vol.Optional("subsidy", default=0): vol.Coerce(float),
                vol.Optional("commissioned"): cv.date,
                vol.Optional("inverter_replacement_cost", default=1400): vol.Coerce(float),
                vol.Optional("inverter_lifetime_years", default=12): vol.Coerce(float),
            }
        ),
        vol.Optional(CONF_NOTIFY): cv.string,
        vol.Optional(CONF_WEATHER): cv.entity_id,
    }
)


@dataclass(slots=True)
class BatteryConfig:
    key: str
    name: str
    soc: str | None = None
    power: str | None = None
    charge_positive: bool = True
    capacity_kwh: float | None = None
    reserve: float = 10.0
    soh: str | None = None
    cycles: str | None = None
    temperature: str | None = None
    cells: str | None = None
    cell_temperatures: str | None = None
    cells_per_module: int | None = None


@dataclass(slots=True)
class ConsumerConfig:
    key: str
    name: str
    power: str | None = None
    energy: str | None = None
    kind: str = "other"
    # Price of the kWh it draws from the grid (None: the contract's), and whether it has its own meter.
    import_price: float | None = None
    separate_meter: bool = False


@dataclass(slots=True)
class UnitConfig:
    name: str
    power: str | None = None
    voltage: str | None = None
    current: str | None = None
    kwp: float | None = None


@dataclass(slots=True)
class HubConfig:
    demo: bool = False
    show_panel: bool = True
    planes: list[Plane] = field(default_factory=list)
    inverter_max_kw: float | None = None
    export_limit_kw: float | None = None
    # One entity per role, or several: they add up for MULTI_ROLES, the first one answering wins otherwise.
    entities: dict[str, list[str]] = field(default_factory=dict)
    batteries: list[BatteryConfig] = field(default_factory=list)
    ignore: set[str] = field(default_factory=set)
    consumers: list[ConsumerConfig] = field(default_factory=list)
    forecast: list[str] = field(default_factory=list)
    # Panels and strings declared by hand (template sensors no profile finds): added, or renaming a detected one.
    panels: list[UnitConfig] = field(default_factory=list)
    strings: list[UnitConfig] = field(default_factory=list)
    import_price: float = 0.2016
    export_price: float = 0.04
    currency: str = "EUR"
    contract: str | None = None
    kva: int | None = None
    offpeak: str | None = None
    offers: dict[str, dict[str, Any]] = field(default_factory=dict)
    weather: str | None = None
    cost: float | None = None
    subsidy: float = 0.0
    commissioned: date | None = None
    inverter_replacement_cost: float = 1400.0
    inverter_lifetime_years: float = 12.0
    notify: str | None = None

    @property
    def kwp(self) -> float:
        return sum(p.kwp for p in self.planes)


def parse(raw: dict[str, Any] | None, options: dict[str, Any] | None = None) -> HubConfig:
    """HubConfig from the YAML block (validated here) and the entry's options.

    YAML wins where both say something, except the entities: those chosen in the options (the panel's
    Settings tab or the options flow) are an explicit substitution and win over the YAML and the detection.
    """
    options = options or {}
    data = YAML_SCHEMA(dict(raw or {}))
    tariff = data[CONF_TARIFF] or YAML_SCHEMA({})[CONF_TARIFF]
    tariff = {"import": 0.2016, "export": 0.04, "currency": "EUR", **tariff}
    inst = {
        "subsidy": 0.0,
        "inverter_replacement_cost": 1400.0,
        "inverter_lifetime_years": 12.0,
        **data[CONF_INSTALLATION],
    }
    return HubConfig(
        demo=bool(data[CONF_DEMO] if raw and CONF_DEMO in raw else options.get(CONF_DEMO, False)),
        show_panel=bool(
            data[CONF_SHOW_PANEL] if raw and CONF_SHOW_PANEL in raw else options.get(CONF_SHOW_PANEL, True)
        ),
        planes=[Plane(p[CONF_KWP], p[CONF_TILT], p[CONF_AZIMUTH]) for p in data[CONF_PLANES]],
        inverter_max_kw=data.get(CONF_INVERTER_MAX_KW),
        export_limit_kw=data.get(CONF_EXPORT_LIMIT_KW),
        entities=_roles(
            {
                **{
                    role: tariff[key]
                    for role, key in (("tariff_price", "price"), ("tariff_color", "color"))
                    if tariff.get(key)
                },
                **data[CONF_ENTITIES],
                **(options.get(CONF_ENTITIES) or {}),
            }
        ),
        batteries=[
            BatteryConfig(
                key=key,
                name=b.get("name", key.replace("_", " ").title()),
                soc=b.get("soc"),
                power=b.get("power"),
                charge_positive=b.get("power_sign", "charge_positive") == "charge_positive",
                capacity_kwh=b.get("capacity_kwh"),
                reserve=b.get("reserve", 10.0),
                soh=b.get("soh"),
                cycles=b.get("cycles"),
                temperature=b.get("temperature"),
                cells=b.get("cells"),
                cell_temperatures=b.get("cell_temperatures"),
                cells_per_module=b.get("cells_per_module"),
            )
            for key, b in data[CONF_BATTERIES].items()
        ],
        ignore=set(data[CONF_IGNORE]),
        consumers=[
            ConsumerConfig(
                key=key,
                name=c.get("name", key.replace("_", " ").capitalize()),
                power=c.get("power"),
                energy=c.get("energy"),
                kind=c.get("kind", "other"),
                import_price=c.get("import_price"),
                separate_meter=c.get("separate_meter", False),
            )
            for key, c in data[CONF_CONSUMERS].items()
        ],
        forecast=list(data[CONF_FORECAST]),
        panels=[UnitConfig(**u) for u in data[CONF_PANELS]],
        strings=[UnitConfig(**u) for u in data[CONF_STRINGS]],
        import_price=tariff["import"],
        export_price=tariff["export"],
        currency=tariff["currency"],
        contract=tariff.get("contract"),
        kva=tariff.get("kva"),
        offpeak=tariff.get("offpeak"),
        offers=dict(tariff.get("offers") or {}),
        weather=data.get(CONF_WEATHER),
        cost=inst.get("cost"),
        subsidy=inst["subsidy"],
        commissioned=inst.get("commissioned"),
        inverter_replacement_cost=inst["inverter_replacement_cost"],
        inverter_lifetime_years=inst["inverter_lifetime_years"],
        notify=data.get(CONF_NOTIFY),
    )
