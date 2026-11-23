# Changelog

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
