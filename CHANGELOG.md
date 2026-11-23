# Changelog

## 1.0.0 - 2026-11-23

### Features
- First release: Energy Hub integration and sidebar panel for solar installations.
- Detection of the installation from the Energy dashboard settings and 21 integration profiles (beta): Enphase Envoy, Huawei Solar, SolarEdge, SolarEdge Modbus Multi, Fronius, SMA, Solax Modbus, Solarman, Victron GX, Tesla Powerwall, OpenDTU / AhoyDTU, Anker Solix, EcoFlow Cloud, Zendure, Marstek Local API, Beem Energy, BLE Battery Management, ZLinky, Teleinfo, Forecast.Solar, Solcast; YAML to override any role, battery or price.
- Panel with an illustrated banner folding into a compact bar, and six tabs: Overview (energy flow, KPIs with their trend, day curve, alerts), Production (per-panel roof, strings, performance index, 12 months), Batteries (fleet, each battery, cells heat map and spread projection), Losses (cascade, clipping heat map, causes, events), Finances (payback ring, break-even projection with a price-rise slider, gains), Settings (configuration check, sources and capabilities, entities and freshness, YAML).
- Loss detection after the PV monitoring literature: clipping (PVAnalytics), soiling (RdTools SRR), degradation (year-on-year), recurring shading per panel, string and panel mismatch, export limitation, unavailability; performance index after IEC 61724-1.
- 12 sensors, the `energy_hub_alert` event, optional daily notifications and a sidebar badge with the number of alerts.
- Demo mode with a simulated installation and more than a year of history.
- English and French.
