"""Constants for the Energy Hub integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "energy_hub"
VERSION: Final = "1.8.1"

# Options of the entry (set in the UI or in YAML; YAML wins).
CONF_DEMO: Final = "demo"
CONF_SHOW_PANEL: Final = "show_panel"

# YAML keys
CONF_PLANES: Final = "planes"
CONF_KWP: Final = "kwp"
CONF_TILT: Final = "tilt"
CONF_AZIMUTH: Final = "azimuth"
CONF_INVERTER_MAX_KW: Final = "inverter_max_kw"
CONF_EXPORT_LIMIT_KW: Final = "export_limit_kw"
CONF_BATTERIES: Final = "batteries"
CONF_ENTITIES: Final = "entities"
CONF_IGNORE: Final = "ignore"
CONF_CONSUMERS: Final = "consumers"
CONF_TARIFF: Final = "tariff"
CONF_INSTALLATION: Final = "installation"
CONF_NOTIFY: Final = "notify"
CONF_FORECAST: Final = "forecast"
CONF_WEATHER: Final = "weather"

# Seconds between two readings of the source entities; samples are averaged into 5-minute buckets.
UPDATE_SECONDS: Final = 30
BUCKET_SECONDS: Final = 300
# 5-minute buckets kept (3 days) and daily records kept (enough for the year-on-year degradation).
BUCKETS_KEPT: Final = 3 * 24 * 12
DAYS_KEPT: Final = 800
# A source whose last update is older than this is stale.
STALE_SECONDS: Final = 600

STORAGE_KEY: Final = f"{DOMAIN}.history"
STORAGE_VERSION: Final = 1

FRONTEND_URL: Final = "/energy_hub_static"
PANEL_FILENAME: Final = "energy-hub-panel.js"
BADGE_FILENAME: Final = "energy-hub-badge.js"
PANEL_URL_PATH: Final = "energy-hub"
PANEL_ICON: Final = "mdi:solar-power-variant"
PANEL_TITLE: Final = "Energy"

EVENT_ALERT: Final = f"{DOMAIN}_alert"

# Notify Hub (juju35/ha-notify-hub): its single notify entity, used for the alerts when no `notify:` is set.
NOTIFY_HUB: Final = "notify.notify_hub"
