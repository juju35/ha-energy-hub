# Changelog

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
