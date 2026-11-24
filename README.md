# ha-energy-hub

[![Marketplace](https://img.shields.io/badge/Marketplace-Custom-41BDF5.svg)](https://www.home-assistant.io/integrations/marketplace/)
[![HACS Validation](https://github.com/juju35/ha-energy-hub/actions/workflows/hacs.yml/badge.svg)](https://github.com/juju35/ha-energy-hub/actions/workflows/hacs.yml)
[![Validate](https://github.com/juju35/ha-energy-hub/actions/workflows/validate.yml/badge.svg)](https://github.com/juju35/ha-energy-hub/actions/workflows/validate.yml)
[![Lint](https://github.com/juju35/ha-energy-hub/actions/workflows/lint.yml/badge.svg)](https://github.com/juju35/ha-energy-hub/actions/workflows/lint.yml)
[![Release](https://img.shields.io/github/v/release/juju35/ha-energy-hub)](https://github.com/juju35/ha-energy-hub/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/juju35/ha-energy-hub/blob/main/LICENSE)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/julienstep9)

<p align="center"><img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/custom_components/energy_hub/brand/icon.png" alt="Energy Hub" width="120"></p>

Home Assistant integration and sidebar panel for **solar installations**: production, self-consumption, batteries (down to the cells), panel efficiency and **production losses** (clipping, shading, soiling, export limitation), with the payback of the installation. It reads the entities of the solar, battery, meter and forecast integrations you already have, and detects most of them by itself.

[![Open your Home Assistant instance and open a repository inside the Marketplace.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=juju35&repository=ha-energy-hub&category=integration)

<img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/light-overview.png" alt="Energy Hub overview" width="640">

> [!NOTE]
> Version 1.0 ships the detection profiles as **beta**: they were written from each integration's documentation and need to be confirmed on real installations. A **demo mode** lets you try the whole panel without any solar equipment. If you own one of the supported devices, please [validate its profile](https://github.com/juju35/ha-energy-hub/issues/new?template=profile_validation.md).

## Features

- **Energy Hub sidebar panel** (no dashboard to build): an illustrated banner that follows the sun, the battery level and the alerts, folding into a compact bar on scroll, and six tabs
  - **Overview**: live energy flow between solar, home, batteries and grid; self-consumption, self-sufficiency, savings and losses of the day with their trend; the production chart over today, 7 days, 30 days or 12 months (forecast, consumption, battery %, inverter maximum, clipping hatched); the current alerts
  - **Production**: specific yield, performance index, peak, month total; **per-panel yield on a roof drawing** (micro-inverters, optimizers) and per-string comparison; 30-day performance index with rainy days; 12 months against expected
  - **Batteries**: any number of batteries of any brand as one fleet (charge, net power, autonomy, battery-to-battery exchange), each battery drawn with its level, its health over 3 years and charge of the day with their projections, its modules, and the **cells** as a modules × cells heat map (deviation, voltage, temperature, balancing), each cell's 30-day drift and the spread projected to the threshold
  - **Losses**: from potential to produced (cascade), clipping heat map over 30 days, causes of the month, events with their status (recurring, to watch, resolved)
  - **Finances**: share paid back, gains since commissioning, break-even date with a price-rise slider, gains calendar, the bill with and without solar, gains by month and where they come from, and an **offer comparator** that replays 12 months of your real grid draw under each EDF offer
  - **Settings**: sources with what each provides or what the hub estimates, attachment suggestions, data quality of the last 24 hours; a clickable DC/AC layout and the configuration checks with their actions; tariffs; alert rules; the equivalent YAML to copy
- **Loss detection based on the PV monitoring literature** (see [How it works](#how-it-works)): clipping, recurring shading per panel, soiling, string mismatch, degradation, export limitation, unavailability
- **Automatic detection** of the installation from the Energy dashboard settings and from 27 integration profiles; YAML to override anything
- **Expected production from what Home Assistant already knows**: a measured irradiance sensor, the solar forecast, or a weather entity's cloud cover, with no network call of its own
- 12 **sensors** (self-consumption, self-sufficiency, solar energy today, specific yield, performance index, losses, clipping, fleet charge and power, autonomy, savings, alerts) for your own dashboards and automations
- `energy_hub_alert` **event** and **notifications** in Home Assistant's language (once a day per alert): through [Notify Hub](https://github.com/juju35/ha-notify-hub) when it is installed, or to the notify action or entity of your choice
- **Sidebar badge** with the number of alerts, red when one is an error
- **Demo mode**: a simulated installation (two strings, sixteen panels, three batteries, more than a year of history) to try every screen
- Diagnostics download with the detected installation only: no location, no history of values
- English, French, German, Spanish, Italian, Dutch, Portuguese, Polish, Serbian (Cyrillic and Latin), Romanian, Danish, Swedish, Bulgarian, Russian, Ukrainian, Hungarian, Slovak, Czech, Slovenian, Latvian and Greek

## Supported integrations

<p align="center">
<a href="https://www.home-assistant.io/integrations/enphase_envoy"><img src="https://brands.home-assistant.io/enphase_envoy/icon.png" alt="Enphase" height="40"></a>
<a href="https://github.com/wlcrs/huawei_solar"><img src="https://brands.home-assistant.io/huawei_solar/icon.png" alt="Huawei Solar" height="40"></a>
<a href="https://www.home-assistant.io/integrations/solaredge"><img src="https://brands.home-assistant.io/solaredge/icon.png" alt="SolarEdge" height="40"></a>
<a href="https://www.home-assistant.io/integrations/fronius"><img src="https://brands.home-assistant.io/fronius/icon.png" alt="Fronius" height="40"></a>
<a href="https://www.home-assistant.io/integrations/sma"><img src="https://brands.home-assistant.io/sma/icon.png" alt="SMA" height="40"></a>
<a href="https://www.home-assistant.io/integrations/powerwall"><img src="https://brands.home-assistant.io/powerwall/icon.png" alt="Tesla Powerwall" height="40"></a>
<a href="https://www.home-assistant.io/integrations/indevolt"><img src="https://brands.home-assistant.io/indevolt/icon.png" alt="Indevolt" height="40"></a>
<a href="https://www.home-assistant.io/integrations/victron_gx"><img src="https://brands.home-assistant.io/victron_gx/icon.png" alt="Victron" height="40"></a>
<a href="https://github.com/Phil-0805/hoymiles-home-assistant"><img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/hoymiles.png" alt="Hoymiles" height="40"></a>
<a href="https://www.home-assistant.io/integrations/forecast_solar"><img src="https://brands.home-assistant.io/forecast_solar/icon.png" alt="Forecast.Solar" height="40"></a>
</p>

Energy Hub works on top of the integrations below. Each one has a detection profile (`custom_components/energy_hub/profiles/*.yaml`) that maps its entities to roles; everything not covered can be given in YAML.

| Integration | Solar | Grid / home | Battery | Detail |
|---|---|---|---|---|
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/enphase_envoy.png" alt="" width="16"> [Enphase Envoy](https://www.home-assistant.io/integrations/enphase_envoy) | ✓ | ✓ | ✓ | micro-inverters |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/huawei_solar.png" alt="" width="16"> [Huawei Solar](https://github.com/wlcrs/huawei_solar) | ✓ | ✓ | ✓ | strings, optimizers, inverter maximum, export limit, battery modules |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/solaredge.png" alt="" width="16"> [SolarEdge](https://www.home-assistant.io/integrations/solaredge) | ✓ | ✓ | ✓ | |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/solaredge.png" alt="" width="16"> [SolarEdge Modbus Multi](https://github.com/WillCodeForCats/solaredge-modbus-multi) | ✓ | ✓ | ✓ | inverter maximum, export limit, state of health |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/fronius.png" alt="" width="16"> [Fronius](https://www.home-assistant.io/integrations/fronius) | ✓ | ✓ | ✓ | strings |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/sma.png" alt="" width="16"> [SMA Solar](https://www.home-assistant.io/integrations/sma) | ✓ | ✓ | ✓ | strings |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/solax.png" alt="" width="16"> [Solax Modbus](https://github.com/wills106/homeassistant-solax-modbus) (SolaX, Growatt, Sofar, Solis, AlphaESS, Qcells…) | ✓ | ✓ | ✓ | strings, inverter maximum, state of health |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/solarman.png" alt="" width="16"> [Solarman](https://github.com/davidrapan/ha-solarman) (Deye, Sunsynk, Sol-Ark…) | ✓ | ✓ | ✓ | strings, state of health, battery modules |
| [Victron GX](https://www.home-assistant.io/integrations/victron_gx) | ✓ | ✓ | ✓ | MPPT trackers, state of health |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/tesla.png" alt="" width="16"> [Tesla Powerwall](https://www.home-assistant.io/integrations/powerwall) | ✓ | ✓ | ✓ | |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/hoymiles.png" alt="" width="16"> [Hoymiles S-Miles Home](https://github.com/Phil-0805/hoymiles-home-assistant) (HiBattery…) | ✓ | ✓ | ✓ | micro-inverters |
| [OpenDTU / AhoyDTU](https://github.com/tbnobody/OpenDTU) (MQTT) | ✓ | | | micro-inverters, export limit |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/anker.png" alt="" width="16"> [Anker Solix](https://github.com/thomluther/ha-anker-solix) | ✓ | ✓ | ✓ | |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/ecoflow.png" alt="" width="16"> [EcoFlow Cloud](https://github.com/tolwi/hassio-ecoflow-cloud) | ✓ | ✓ | ✓ | state of health, cycles |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/zendure.png" alt="" width="16"> [Zendure](https://github.com/Zendure/Zendure-HA) | ✓ | ✓ | ✓ | state of health, battery packs |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/marstek.png" alt="" width="16"> [Marstek Local API](https://github.com/jaapp/ha-marstek-local-api) | | ✓ | ✓ | |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/beem.png" alt="" width="16"> [Beem Energy](https://github.com/CharlesP44/Beem_Energy) | ✓ | | ✓ | |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/indevolt.png" alt="" width="16"> [Indevolt](https://www.home-assistant.io/integrations/indevolt) (BK1600, PG2000…, also the [custom integration](https://github.com/INDEVOLT/homeassistant-indevolt)) | ✓ | ✓ | ✓ | strings, grid meter, cycles |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/bms_ble.png" alt="" width="16"> [BLE Battery Management](https://github.com/patman15/BMS_BLE-HA) (JK, JBD, Daly…) | | | ✓ | **cells**, cycles |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/zha.png" alt="" width="16"> [ZLinky](https://www.home-assistant.io/integrations/zha) (ZHA) | | ✓ | | Linky meter |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/teleinfo.png" alt="" width="16"> [Teleinfo](https://www.home-assistant.io/integrations/teleinfo) | | ✓ | | Linky meter |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/tasmota.png" alt="" width="16"> [Denky D4](https://github.com/hallard/Denky-D4) ([Tasmota](https://www.home-assistant.io/integrations/tasmota) Teleinfo) | | ✓ | | Linky meter |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/forecast_solar.png" alt="" width="16"> [Forecast.Solar](https://www.home-assistant.io/integrations/forecast_solar) | forecast | | | |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/solcast_solar.png" alt="" width="16"> [Solcast PV Forecast](https://github.com/BJReplay/ha-solcast-solar) | forecast | | | |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/tarif_edf.png" alt="" width="16"> [Tarif EDF](https://github.com/delphiki/hass-tarif-edf) | | tariff | | contract, power, price now, Tempo colour |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/rtetempo.png" alt="" width="16"> [RTE Tempo](https://github.com/hekmon/rtetempo) | | tariff | | Tempo colour |
| [EDF Zen Flex](https://github.com/AuroreVgn/edf-zen-flex) | | tariff | | eco / sobriety day |
| Any weather station with an irradiance sensor (<img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/ecowitt.png" alt="" width="16"> [Ecowitt](https://www.home-assistant.io/integrations/ecowitt), <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/weatherflow.png" alt="" width="16"> [WeatherFlow](https://www.home-assistant.io/integrations/weatherflow)…) | irradiance | | | detected by its `irradiance` device class |
| Any <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/images/home_assistant.png" alt="" width="16"> [weather](https://www.home-assistant.io/integrations/weather) entity (Météo-France, Met.no, OpenWeatherMap, Open-Meteo…) | cloud cover | | | |

Any other integration works through the **Energy dashboard** settings (solar production, grid import and export, battery energy are read from there) or through the `entities:` and `batteries:` YAML keys. What a source does not provide is estimated when possible (state of health from full charges, cycles from the energy discharged, kWp from the production peaks) and marked as such in the panel.

## Prerequisites

- Home Assistant 2024.12 or later
- At least a solar production power or energy sensor (or the demo mode)
- Recommended: the Energy dashboard configured, a grid meter, the panels' orientation (`planes:`) and a forecast integration

## Installation

### Via the Marketplace (recommended)

Click the button below to add the repository directly:

[![Add to the Marketplace](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=juju35&repository=ha-energy-hub&category=integration)

Then click **Install** and restart Home Assistant.

Or manually:

1. Open **Settings → Marketplace → Add from link** (top right; this needs a GitHub account connected)
2. Add `https://github.com/juju35/ha-energy-hub` — Type: **Integration**
3. Open **Energy Hub** and click **Install**
4. Restart Home Assistant

The panel and the sidebar badge are **part of the integration** and served from `/energy_hub_static/`; nothing to add to the dashboard resources (they are not in `/local/community/`). After an update, restart Home Assistant and refresh the browser.

### Manual

Copy `custom_components/energy_hub/` to `/config/custom_components/energy_hub/`, then restart Home Assistant.

## Configuration

### From the UI

**Settings → Devices & services → Add integration → Energy Hub**. There is no question to answer: the detection does the rest. The options offer the **demo mode** and hiding the sidebar panel.

### YAML

Every key is optional; what is given in YAML wins over the detection and over the options.

```yaml
energy_hub:
  demo: false                     # simulated installation, to try the panel
  show_panel: true
  planes:                         # one per roof side; drives the expected production and the losses
    - kwp: 3.28
      tilt: 30                    # degrees from horizontal
      azimuth: 190                # degrees, 180 = south
  inverter_max_kw: 4.2            # AC maximum: plateaus at this level are clipping
  export_limit_kw: 4.5            # grid feed-in limit: plateaus at this level are limitation
  entities:                       # override a detected role
    pv_power: sensor.inverter_input_power
    pv_energy: sensor.inverter_total_yield
    grid_power: sensor.linky_power          # positive when importing
    grid_import_energy: sensor.linky_index
    grid_export_energy: sensor.linky_injection
    load_power: sensor.home_power
    forecast_power: sensor.solcast_power_now
    forecast_energy_today: sensor.solcast_forecast_today
    irradiance: sensor.solar_radiation      # W/m², horizontal (detected by its device class)
  batteries:                      # one key per battery, any brand
    house:
      name: House
      soc: sensor.battery_state_of_capacity
      power: sensor.battery_charge_discharge_power
      power_sign: charge_positive # or discharge_positive
      capacity_kwh: 15
      reserve: 10                 # % kept, left out of the autonomy
      soh: sensor.battery_soh
      cycles: sensor.battery_cycles
      temperature: sensor.battery_temperature
      cells: sensor.jk_bms_cell_voltage_*   # glob of the cell voltage sensors
      cell_temperatures: sensor.jk_bms_cell_temperature_*
      cells_per_module: 16        # draws the cells as modules × cells
  ignore:                         # entities never read (a double count, for example)
    - sensor.zendure_ac_input
  tariff:
    import: 0.2016                # price per kWh bought, when no contract is known
    export: 0.04                  # price per kWh sold
    currency: EUR
    contract: tempo               # base, hphc, tempo, zen_weekend, zen_weekend_hc, zen_flex (read from Tarif EDF)
    kva: 9                        # subscribed power
    offpeak: "22:00-06:00"        # your off-peak hours (Enedis), several ranges separated by commas
    price: sensor.tarif_actuel_tempo_9kva_ttc    # price of the kWh now (detected with Tarif EDF)
    color: sensor.rte_tempo_couleur_actuelle     # Tempo colour or Zen Flex day (detected)
    offers:                       # change the embedded grid, or add an offer to compare
      zen_weekend:
        prices: {week: 0.2285, weekend: 0.1710}
      my_supplier:
        name: My supplier
        kind: hphc                # base, hphc, tempo, weekend, weekend_hphc, flex
        subscription: 190.32      # per year
        prices: {hp: 0.205, hc: 0.155}
  weather: weather.home           # cloud cover for the expected production (first weather entity by default)
  installation:                   # for the payback
    cost: 9800
    subsidy: 1140
    commissioned: 2023-04-12
    inverter_replacement_cost: 1400
    inverter_lifetime_years: 12
  notify: notify.mobile_app_phone # alerts, once a day each; default: notify.notify_hub when Notify Hub is installed
```

The **Settings** tab shows the YAML equivalent to what is detected, ready to copy.

### Sensors

| Sensor | Unit |
|---|---|
| Self-consumption, Self-sufficiency, Performance index | % |
| Solar energy today, Production losses today, Clipping today | kWh |
| Specific yield today | kWh/kWp |
| Battery fleet charge | % |
| Battery fleet power (positive when charging) | kW |
| Battery autonomy | h |
| Savings today | currency |
| Alerts (count, list in the `alerts` attribute) | |

### Events

`energy_hub_alert` is fired once per alert and per day, with `kind` (`clipping`, `string_lagging`, `shading`, `soiling`, `cell_drift`, `battery_exchange`, `stale`), `severity` and the alert's details.

The same alerts are sent as notifications, written in Home Assistant's language: to `notify:` when it is set (a notify entity through `notify.send_message`, or a legacy notify action), otherwise to `notify.notify_hub` when [Notify Hub](https://github.com/juju35/ha-notify-hub) is installed, where its routing rules decide who receives them. Nothing is sent in demo mode.

## Screenshots

| Light | Dark |
|---|---|
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/light-overview.png" alt="overview" width="480"> | <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/dark-overview.png" alt="overview dark" width="480"> |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/light-overview-30d.png" alt="overview 30 days" width="480"> | <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/dark-overview-30d.png" alt="overview 30 days dark" width="480"> |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/light-production.png" alt="production" width="480"> | <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/dark-production.png" alt="production dark" width="480"> |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/light-batteries.png" alt="batteries" width="480"> | <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/dark-batteries.png" alt="batteries dark" width="480"> |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/light-cells.png" alt="cells" width="480"> | <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/dark-cells.png" alt="cells dark" width="480"> |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/light-losses.png" alt="losses" width="480"> | <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/dark-losses.png" alt="losses dark" width="480"> |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/light-finances.png" alt="finances" width="480"> | <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/dark-finances.png" alt="finances dark" width="480"> |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/light-settings.png" alt="settings" width="480"> | <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/dark-settings.png" alt="settings dark" width="480"> |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/light-settings-installation.png" alt="settings installation" width="480"> | <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/dark-settings-installation.png" alt="settings installation dark" width="480"> |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/light-settings-alerts.png" alt="settings alerts" width="480"> | <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/dark-settings-alerts.png" alt="settings alerts dark" width="480"> |
| <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/light-settings-tariffs.png" alt="settings tariffs" width="480"> | <img src="https://raw.githubusercontent.com/juju35/ha-energy-hub/main/screenshots/dark-settings-tariffs.png" alt="settings tariffs dark" width="480"> |

## How it works

Every 30 seconds the integration reads the detected entities (powers converted to kW, energies to kWh), integrates them into 5-minute buckets, 15-minute bins and daily records kept for more than two years in Home Assistant's storage, and computes a snapshot that the panel receives over the websocket. Everything runs locally in pure Python, without any cloud service.

- **Expected production**: the clear-sky production of each plane (NOAA solar position, Haurwitz irradiance model, plane-of-array transposition), scaled by the best reference Home Assistant has: a **measured irradiance** sensor (measured over clear-sky horizontal irradiance, the closest to the pyranometer of **IEC 61724-1**), else the **forecast** integration's power, else a weather entity's **cloud cover** N with the **Kasten-Czeplak** relation 1 − 0.75 N^3.4 (the condition stands in when the entity gives no cover), else the clear sky alone. The **performance index** is the measured over expected energy, as the Energy Performance Index of IEC 61724-1.
- **Clipping**: plateaus of the production at the inverter maximum while the expected power is above it, after the geometric and threshold methods of **PVAnalytics** (Perry et al.); a plateau at the export limit is counted as **limitation** instead.
- **Soiling**: stochastic rate and recovery (**SRR**) method of **RdTools** (Deceglie et al., 2018) on the daily performance index, cleaning events detected from rain and sudden recoveries; needs 90 days.
- **Degradation**: year-on-year method (Jordan et al.) with a Theil–Sen slope; needs two years, shown as *learning* until then.
- **Recurring shading**: on clear days only, each panel's 15-minute yield against the median of its peers, kept when the same window repeats (density-based approach after the Utrecht University shading studies); needs 10 clear days.
- **Mismatch**: a string or panel whose relative yield stays under 90 % of the leave-one-out median of its peers for 3 days (after Guerriero et al.).
- **Batteries**: fleet charge weighted by capacity, autonomy above the reserves at the current load, state of health from charges covering at least 40 points of charge, equivalent cycles, round-trip efficiency over 30 days, cell spread and its Theil–Sen projection to the threshold (50 mV).
- **Offer comparator**: the grid draw is kept per half hour for a year; each offer prices every half hour (off-peak ranges, week-ends and French public holidays, the Tempo colour or Zen Flex day recorded that day, or the season's expected mix when it was not), adds its subscription and is ranked. The regulated prices change on 1 February and 1 August and the Zen offers at most twice a year: the grid is EDF's published one, embedded with its date, flagged after 7 months, updated by release, and the market offers are shown as references to check against your contract.
- **Payback**: gains are the self-consumed energy at the price of its half hour (the price entity, else the contract's grid, else the flat import price) plus the exported energy at the export price; the projection adds the yearly gain with the chosen price rise, 0.5 %/year of degradation and one inverter replacement.

## Development

The frontend source is split into ES modules under `src/energy-hub-panel/` (entry `src/energy-hub-panel/index.js`). `node scripts/build-frontend.mjs` (or `npm run build`) assembles them into `custom_components/energy_hub/frontend/energy-hub-panel.js`, not committed: build before the tests, the screenshots and the release. Modules share one scope once assembled, so top-level names stay unique; a new module must be listed in its `index.js`.

```bash
npm ci && npm run build          # assembles the panel from src/ (not committed)
pip install -r requirements_test.txt && pytest
node --test test/*.test.mjs
python scripts/screenshots.py --refresh-fixture   # after a change of the demo or the snapshot (needs Home Assistant)
pip install playwright==1.64.1 pillow && playwright install chromium
python scripts/screenshots.py   # renders every tab, light and dark, from test/fixtures/demo.json into screenshots/
```

### Releasing

1. Bump the version in `custom_components/energy_hub/manifest.json`, `VERSION` in `const.py` and `ENERGY_HUB_PANEL_VERSION` in `src/energy-hub-panel/core.js`
2. Add a `## <version>` section at the top of [CHANGELOG.md](https://github.com/juju35/ha-energy-hub/blob/main/CHANGELOG.md)
3. Merge to `main`: the **Release** workflow creates the tag and the GitHub release with the changelog section as notes

## Translations

The integration and the panel follow the language of Home Assistant. Currently supported:

| Language | Code |
|---|---|
| English | `en` |
| Français | `fr` |
| Deutsch | `de` |
| Español | `es` |
| Italiano | `it` |
| Nederlands | `nl` |
| Português (Portugal) | `pt` |
| Polski | `pl` |
| Српски | `sr` |
| Srpski (latinica) | `sr-Latn` |
| Română | `ro` |
| Dansk | `da` |
| Svenska | `sv` |
| Български | `bg` |
| Русский | `ru` |
| Українська | `uk` |
| Magyar | `hu` |
| Slovenčina | `sk` |
| Čeština | `cs` |
| Slovenščina | `sl` |
| Latviešu | `lv` |
| Ελληνικά | `el` |

Brazilian Portuguese (`pt-BR`) uses the European Portuguese texts. The panel ships English and loads the other languages from `custom_components/energy_hub/frontend/i18n/` on demand.

Contributions for additional languages are welcome!

## License

[MIT](https://github.com/juju35/ha-energy-hub/blob/main/LICENSE)

## Support

If you find this project useful, you can support its development:

<a href="https://buymeacoffee.com/julienstep9"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" height="50"></a>
