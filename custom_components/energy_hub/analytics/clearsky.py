"""Solar position and clear-sky production: what an array would make under a cloudless sky.

Used as the expected production when no forecast integration is configured, and to pick clear days (actual close to
clear-sky) for the trend analyses, as RdTools' clear-sky workflow does. Accuracy of a few percent is enough: the
analyses compare a day with itself over time, never with an absolute reference.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

# Share of the plane-of-array irradiance turned into AC energy at 25 °C (wiring, inverter, mismatch, soiling at rest).
SYSTEM_FACTOR = 0.86
# Power temperature coefficient of crystalline modules, per °C above 25 °C.
TEMP_COEFF = -0.004
ALBEDO = 0.2


@dataclass(frozen=True, slots=True)
class Plane:
    """One orientation of panels: peak power in kWp, tilt from horizontal and azimuth (180 = south), in degrees."""

    kwp: float
    tilt: float = 30.0
    azimuth: float = 180.0


def solar_position(when: datetime, latitude: float, longitude: float) -> tuple[float, float]:
    """Zenith and azimuth (degrees, azimuth clockwise from north) of the sun, NOAA's low-precision formulas."""
    when = when.astimezone(UTC)
    day = when.timetuple().tm_yday
    hour = when.hour + when.minute / 60 + when.second / 3600
    gamma = 2 * math.pi / 365 * (day - 1 + (hour - 12) / 24)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    true_solar_minutes = hour * 60 + eqtime + 4 * longitude
    hour_angle = math.radians(true_solar_minutes / 4 - 180)
    lat = math.radians(latitude)
    cos_zenith = math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(hour_angle)
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    zenith = math.acos(cos_zenith)
    sin_zenith = math.sin(zenith)
    if sin_zenith < 1e-9:
        return math.degrees(zenith), 180.0
    cos_az = (math.sin(decl) - math.sin(lat) * cos_zenith) / (math.cos(lat) * sin_zenith)
    azimuth = math.degrees(math.acos(max(-1.0, min(1.0, cos_az))))
    if hour_angle > 0:
        azimuth = 360 - azimuth
    return math.degrees(zenith), azimuth


def clearsky_ghi(zenith: float) -> float:
    """Global horizontal irradiance of a clear sky, W/m² (Haurwitz model)."""
    cos_z = math.cos(math.radians(zenith))
    if cos_z <= 0.01:
        return 0.0
    return 1098.0 * cos_z * math.exp(-0.057 / cos_z)


def poa_irradiance(ghi: float, zenith: float, sun_azimuth: float, plane: Plane) -> float:
    """Plane-of-array irradiance, W/m²: beam on the plane, isotropic sky diffuse and ground reflection."""
    if ghi <= 0:
        return 0.0
    cos_z = math.cos(math.radians(zenith))
    dhi = 0.12 * ghi
    dni = (ghi - dhi) / max(cos_z, 0.05)
    tilt = math.radians(plane.tilt)
    cos_aoi = cos_z * math.cos(tilt) + math.sin(math.radians(zenith)) * math.sin(tilt) * math.cos(
        math.radians(sun_azimuth - plane.azimuth)
    )
    beam = dni * max(cos_aoi, 0.0)
    sky = dhi * (1 + math.cos(tilt)) / 2
    ground = ghi * ALBEDO * (1 - math.cos(tilt)) / 2
    return beam + sky + ground


def clearsky_power(
    when: datetime, latitude: float, longitude: float, planes: list[Plane], ambient: float = 15.0
) -> float:
    """AC power (kW) the planes would deliver under a clear sky at ``when``."""
    zenith, azimuth = solar_position(when, latitude, longitude)
    ghi = clearsky_ghi(zenith)
    total = 0.0
    for plane in planes:
        poa = poa_irradiance(ghi, zenith, azimuth, plane)
        cell = ambient + poa / 800 * 25
        total += plane.kwp * poa / 1000 * SYSTEM_FACTOR * (1 + TEMP_COEFF * (cell - 25))
    return max(total, 0.0)


# Cloud cover of a weather condition, when the weather entity gives no `cloud_coverage` (0 = clear, 1 = overcast).
CONDITION_CLOUDS = {
    "sunny": 0.0,
    "clear-night": 0.0,
    "windy": 0.3,
    "partlycloudy": 0.5,
    "windy-variant": 0.6,
    "cloudy": 0.9,
    "fog": 1.0,
    "rainy": 1.0,
    "pouring": 1.0,
    "snowy": 1.0,
    "snowy-rainy": 1.0,
    "hail": 1.0,
    "lightning": 1.0,
    "lightning-rainy": 1.0,
    "exceptional": 1.0,
}


def cloud_factor(cloud_cover: float) -> float:
    """Share of the clear-sky global irradiance left under a cloud cover N (0..1): 1 - 0.75 N^3.4
    (Kasten & Czeplak, Solar Energy 24, 1980)."""
    n = min(max(cloud_cover, 0.0), 1.0)
    return 1 - 0.75 * n**3.4


def measured_factor(ghi: float, when: datetime, latitude: float, longitude: float) -> float | None:
    """Ratio of a measured horizontal irradiance (W/m²) to the clear sky's, clamped to 0..1.3 (cloud enhancement);
    None when the sun is too low for the ratio to mean anything."""
    zenith, _azimuth = solar_position(when, latitude, longitude)
    clear = clearsky_ghi(zenith)
    if clear < 50:
        return None
    return min(max(ghi / clear, 0.0), 1.3)
