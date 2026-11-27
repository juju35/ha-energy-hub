# Changelog

## 1.9.0 - 2026-11-27

### Features
- Panels and strings declared in YAML (`panels:` / `strings:`, a power entity or a voltage and a current, an optional kWp): for template sensors or any setup no profile finds; one reading the same entity as a detected panel renames it (#28).
- Your own detection profiles in `/config/energy_hub/profiles/*.yaml`, kept across updates; one named like a built-in profile replaces it, an unreadable one is skipped with a warning (#28).

## 1.8.1 - 2026-11-27

### Fixes
- Tiles have the 10 px corner radius shared by the ha-* cards.

## 1.8.0 - 2026-11-26

### Features
- Large consumers (EV charger, heat pump, air conditioning, water heater…): detected from the Energy dashboard's individual devices (keyed by their entity, so reordering them keeps their history), or declared under `consumers:` in YAML (a power or an energy entity, a kind, a name). With an energy entity only, the power is the slope between two changes of the energy, timed by the state's last change. Overview: each one is a node under the home in the energy flow, and a slice stacked under the consumption curve of the day, or a stacked bar in the 7-day, 30-day and 12-month charts; the tooltips list them. Each kind has its MDI icon (ev-station, heat-pump-outline, air-conditioner, water-boiler, power-plug-outline) and colour. (#24)
- A second tariff per consumer: `import_price` prices the kWh it draws from the grid, and `separate_meter: true` puts it on its own meter (heat pump and EV tariffs): no solar reaches it, its energy is bought apart and added to the home's consumption, the bill and the savings use its price, and the offer comparator keeps to the main meter. Settings → Tariffs lists each consumer with its price and its meter. (#24)
- The snapshot carries the consumers (`consumers`: power now, energy, solar share and cost of the day), the curve and the period rows their powers and energies (`c`); the equivalent YAML of the Settings tab includes them.
- Demo: an EV charger on its own meter and price, and a heat pump (heating in winter, hot water every early afternoon).
- Translations: the new panel keys in the 21 other languages.

## 1.7.0 - 2026-11-25

### Features
- Settings: choose the entity behind every role (solar power and energy, grid power and import / export, home load, forecast, irradiance, tariff price and colour) from the options flow or the Sources section of the panel's Settings tab — an empty field keeps the automatic detection, and the choice wins over the YAML block.
- Alternative data source: a role accepts several entities. The solar power role adds them up (several arrays, FusionSolar and Indevolt for instance); for the other roles the first entity that answers wins (power, price, tariff colour, irradiance), so a Zigbee / Linky module can stand in for the inverter's meter; a fallback that answers keeps the installation online.
- Panel: a "Entities" box on top of the Sources tab, one row per role, the detected entity as placeholder and a Save button talking to the admin websocket `energy_hub/set_entities`.
- Snapshot: the roles payload now lists every role (`all`), the entities chosen in the options (`configured`) and the detected ones (`detected`).
- Translations: the new options step and the panel keys in all 21 languages.

## 1.6.0 - 2026-11-24

### Features
- Profile: Indevolt solar batteries (`indevolt`, GEN1 BK1600/BK2500 and GEN2 PG2000), from the core integration or the INDEVOLT custom one — PV power and total production, the DC inputs as strings, meter power, state of charge, battery power, temperature, cycles, rated capacity and total charge / discharge energy; the battery packs stay out of the battery list and the home load is derived (the AC output is what the device feeds the house).
- Profile: Denky D4 read as a Linky meter (`denky_d4`, Tasmota Teleinfo driver) — grid power from SINSTS or PAPP, imported energy from EAST, BASE or Tasmota's ENERGY total (off-peak meters included), exported energy from EAIT.

## 1.5.0 - 2026-11-24

### Features
- Profile: Hoymiles S-Miles Home (`hoymiles_home`, HiBattery and other S-Miles batteries) — PV, home load and grid power, total yield, PV1/PV2… per micro-inverter, battery state of charge, temperature and daily charge / discharge energy (#11).
- Batteries whose power is an unsigned magnitude: a profile can give `charge_power` and `discharge_power`, two positive sensors, and the hub signs the battery power from them.

## 1.4.1 - 2026-11-24

### Maintenance
- The frontend source is split into ES modules: `src/energy-hub-panel/` (entry `src/energy-hub-panel/index.js`), cut at its sections (the English strings in `strings.js`; the other languages stay `frontend/i18n/<lang>.json`, fetched on demand). `scripts/build-frontend.mjs` assembles them, in their original order, into `custom_components/energy_hub/frontend/energy-hub-panel.js`, no longer committed; the tests, the screenshots and the release build them first. The release zip is unchanged.

## 1.4.0 - 2026-11-23

### Features
- Finances: an offer comparator replays the last 12 months of grid draw, half hour by half hour, under each EDF offer (Tarif Bleu Base, Heures Creuses, Tempo; Zen Week-End, Zen Week-End Heures Creuses, Zen Flex), subscription included, and says what switching would save. The grid is EDF's, embedded and updated by release; `tariff: offers:` overrides it or adds an offer of your own.
- Tariff: the contract and power are read from Tarif EDF, the price of the kWh now from its price entity, the day's Tempo colour from Tarif EDF or RTE Tempo and the Zen Flex day from EDF Zen Flex; YAML `tariff: contract:`, `kva:`, `offpeak:`, `price:`, `color:`.
- Savings and the bill value each half hour at its price (Tempo colours, off-peak hours) instead of a flat price.
- Expected production from the best reference found: a measured irradiance sensor (W/m², weather stations such as Ecowitt or WeatherFlow), then the solar forecast, then a weather entity's cloud cover (Kasten-Czeplak), then the clear sky; Settings shows which one is used. YAML `weather:` and `entities: irradiance:`.
- Profiles: Tarif EDF, RTE Tempo, EDF Zen Flex.

## 1.3.0 - 2026-11-23

### Features
- Alerts go to Notify Hub (`notify.notify_hub`) when it is installed and no `notify:` is set; the Settings tab shows the target as detected.
- `notify:` accepts a notify entity (sent with `notify.send_message`) as well as a legacy notify action.
- Notifications are written in Home Assistant's language (22 languages; regional variants use their base language).

## 1.2.0 - 2026-11-23

### Features
- 20 more languages for the integration and the panel: German, Spanish, Italian, Dutch, Portuguese, Polish, Serbian (Cyrillic and Latin), Romanian, Danish, Swedish, Bulgarian, Russian, Ukrainian, Hungarian, Slovak, Czech, Slovenian, Latvian and Greek. The panel ships English and fetches the other languages from `frontend/i18n/` when Home Assistant uses one (regional variants such as `pt-BR` use their base language).

### Fixes
- Panel: the trend unit, the 30-day axis label and the last hour label of the charge chart are translated and no longer clipped.

## 1.1.0 - 2026-11-23

### Features
- Banner: alert bell with its count; the collapsed bar keeps a condensed status pill; on narrow screens Refresh moves to Settings.
- Overview: period selector (Today, 7 days, 30 days, 12 months) and clipping drawn hatched.
- Batteries: the selected battery drawn with its level and reserve, autonomy and capacity tiles, charge of the day with its projection, state of health over 3 years with its projection, modules, cells as a modules × cells heat map (deviation, voltage, temperature) with balancing dots and drifting cells outlined, cell detail with its 30-day curve and drift diagnosis, spread trend projected to the threshold.
- Losses: events with their status (recurring, to watch, resolved), dates, days and energy.
- Finances: gains calendar over 6 weeks and the bill with and without solar.
- Settings: sub-tabs Sources, Installation, Tariffs, Alerts and YAML; clickable DC/AC layout with each element's capabilities and entities; attachment suggestions (a BMS to its battery, with how well their charges match); data quality of the last 24 hours; configuration checks with an action each.
- YAML: `cell_temperatures` and `cells_per_module` for a battery.

## 1.0.0 - 2026-11-23

### Features
- First release: Energy Hub integration and sidebar panel for solar installations.
- Detection of the installation from the Energy dashboard settings and 21 integration profiles (beta): Enphase Envoy, Huawei Solar, SolarEdge, SolarEdge Modbus Multi, Fronius, SMA, Solax Modbus, Solarman, Victron GX, Tesla Powerwall, OpenDTU / AhoyDTU, Anker Solix, EcoFlow Cloud, Zendure, Marstek Local API, Beem Energy, BLE Battery Management, ZLinky, Teleinfo, Forecast.Solar, Solcast; YAML to override any role, battery or price.
- Panel with an illustrated banner folding into a compact bar, and six tabs: Overview (energy flow, KPIs with their trend, day curve, alerts), Production (per-panel roof, strings, performance index, 12 months), Batteries (fleet, each battery, cells heat map and spread projection), Losses (cascade, clipping heat map, causes, events), Finances (payback ring, break-even projection with a price-rise slider, gains), Settings (configuration check, sources and capabilities, entities and freshness, YAML).
- Loss detection after the PV monitoring literature: clipping (PVAnalytics), soiling (RdTools SRR), degradation (year-on-year), recurring shading per panel, string and panel mismatch, export limitation, unavailability; performance index after IEC 61724-1.
- 12 sensors, the `energy_hub_alert` event, optional daily notifications and a sidebar badge with the number of alerts.
- Demo mode with a simulated installation and more than a year of history.
- English and French.
