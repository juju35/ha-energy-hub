"""Declared strings and panels: their capacity, their orientation, and their own losses.

A string (``strings:``) or a panel / MPPT input (``panels:``) declared in YAML may carry its own kWp, its own tilt
and its own azimuth. Such a unit is then weighed on its own: its expectation comes from the clear sky of *its*
orientation, so a steep array that produces less in June is not flagged as a fault while a string under a chimney
keeps its shading on its own line. The installation's figures keep counting every unit whose ``count_in_total`` is
true, and a unit the ``pv_power`` role already meters is never added twice — the coordinator adds it to the total
before the history integrates it, so the history's ``pv`` is used as it is.

Neither Home Assistant nor the engine: everything here works on the history records and on the configuration.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from typing import Any

from .clearsky import Plane, clearsky_power
from .degradation import degradation_yoy
from .mismatch import score_units
from .soiling import MIN_DAYS as SOILING_DAYS
from .soiling import soiling_srr

# A unit declared without an orientation sits on the usual 30° roof facing south.
DEFAULT_TILT = 30.0
DEFAULT_AZIMUTH = 180.0
# Two units closer than that share an orientation: they see the same sky and can be compared with each other.
ORIENTATION_STEP = 15.0
# The daily clear-sky energy is integrated on the hour: the estimate is a ratio against a measured day.
STEP_MINUTES = 60
STEPS = range(0, 24 * 60, STEP_MINUTES)
# Mismatch compares the latest month of clear days: the same window as the strings' relative yield.
MISMATCH_DAYS = 30


@dataclass(frozen=True, slots=True)
class DeclaredUnit:
    """A string or a panel as declared: capacity, orientation, and whether it counts in the PV total."""

    name: str
    kind: str = "strings"
    kwp: float | None = None
    tilt: float | None = None
    azimuth: float | None = None
    # None: counted as in 1.9.0, True: added on top of a pv_power meter, False: left out of the total.
    count_in_total: bool | None = None

    @property
    def orientation(self) -> tuple[float, float]:
        return (
            DEFAULT_TILT if self.tilt is None else float(self.tilt),
            DEFAULT_AZIMUTH if self.azimuth is None else float(self.azimuth),
        )

    @property
    def bucket(self) -> str:
        """The orientation group: units of the same group are compared with each other for mismatch."""
        tilt, azimuth = self.orientation
        return f"{round(tilt / ORIENTATION_STEP)}/{round(azimuth / ORIENTATION_STEP)}"

    def plane(self, kwp: float) -> Plane:
        tilt, azimuth = self.orientation
        return Plane(kwp, tilt, azimuth)


@dataclass(frozen=True, slots=True)
class UnitLoss:
    """What one unit produced, what its own orientation promised, and where the difference went."""

    name: str
    kind: str = "strings"
    kwp: float | None = None
    tilt: float | None = None
    azimuth: float | None = None
    count_in_total: bool | None = None
    production_kwh: float = 0.0
    expected_kwh: float | None = None
    performance: float | None = None
    yield_kwh_per_kwp: float | None = None
    soiling: float | None = None
    shading_kwh: float | None = None
    mismatch: float | None = None
    clipping_kwh: float | None = None
    degradation_pct: float | None = None


def _num(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _pick(declared: Any, field: str, fallback: Any) -> Any:
    """The declared value when YAML gives one, else what the profile detected."""
    value = getattr(declared, field, None) if declared is not None else None
    return fallback if value is None else value


def declared_units(cfg: Any, inst: Any) -> list[DeclaredUnit]:
    """The strings and panels of the installation, with what YAML declares for each of them.

    The configuration holds the declarations (``strings`` and ``panels``); the installation holds the units that
    end up in the readings. They are matched by name, and the profile's own fields are the fallback.
    """
    declared: dict[str, Any] = {}
    for item in list(getattr(cfg, "strings", None) or []):
        declared[item.name] = item
    for item in list(getattr(cfg, "panels", None) or []):
        declared[item.name] = item
    units: list[DeclaredUnit] = []
    for kind, sources in (
        ("strings", getattr(inst, "strings", None) or []),
        ("units", getattr(inst, "units", None) or []),
    ):
        for source in sources:
            cfg_unit = declared.get(source.name)
            units.append(
                DeclaredUnit(
                    name=source.name,
                    kind=kind,
                    kwp=_num(_pick(cfg_unit, "kwp", getattr(source, "kwp", None))),
                    tilt=_num(_pick(cfg_unit, "tilt", getattr(source, "tilt", None))),
                    azimuth=_num(_pick(cfg_unit, "azimuth", getattr(source, "azimuth", None))),
                    count_in_total=_pick(cfg_unit, "count_in_total", getattr(source, "count_in_total", None)),
                )
            )
    return units


def capacity_shares(units: Iterable[DeclaredUnit], installed: float) -> dict[str, float]:
    """kWp of each unit: as declared, else an equal share of what the declared ones leave (profile-found units)."""
    units = list(units)
    known = sum(u.kwp or 0.0 for u in units)
    unknown = [u for u in units if not u.kwp]
    share = max(installed - known, 0.0) / len(unknown) if unknown else 0.0
    return {u.name: (u.kwp or share) for u in units}


@lru_cache(maxsize=8192)
def _clear_kwh(
    day: date,
    kwp: float,
    tilt: float,
    azimuth: float,
    latitude: float,
    longitude: float,
    tz: Any,
) -> float:
    """Clear-sky energy of one plane on one day (kWh), in its own orientation — cached: a past day never changes."""
    plane = Plane(kwp, tilt, azimuth)
    total = 0.0
    for minute in STEPS:
        when = datetime(day.year, day.month, day.day, minute // 60, tzinfo=tz)
        total += clearsky_power(when, latitude, longitude, [plane])
    return round(total * STEP_MINUTES / 60, 4)


def unit_expected(
    day: date,
    unit: DeclaredUnit,
    kwp: float,
    installed: float,
    record: dict[str, Any] | None,
    latitude: float | None = None,
    longitude: float | None = None,
    tz: Any = None,
) -> float:
    """Clear-sky energy (kWh) of one unit on ``day``: its own tilt and azimuth, else its share of the site's sky."""
    if kwp <= 0:
        return 0.0
    if latitude is not None and longitude is not None and tz is not None:
        tilt, azimuth = unit.orientation
        return _clear_kwh(day, round(kwp, 4), tilt, azimuth, float(latitude), float(longitude), tz)
    clearsky = _num((record or {}).get("clearsky")) or 0.0
    if installed <= 0 or clearsky <= 0:
        return 0.0
    return clearsky * kwp / installed


def _peer_scores(
    series: dict[str, list[tuple[date, float, float, float]]], units: list[DeclaredUnit]
) -> dict[str, float]:
    """Mismatch: each unit's yield against the median of the units sharing its orientation, in the same sky.

    The comparison is made on production over each unit's own clear-sky expectation, so a string on another roof
    pitch is not mistaken for a faulty one; a unit alone in its orientation group has no peer and no score.
    """
    buckets: dict[str, dict[date, dict[str, tuple[float, float]]]] = {}
    bucket_of = {u.name: u.bucket for u in units}
    for name, rows in series.items():
        per_day = buckets.setdefault(bucket_of.get(name, ""), {})
        for day, actual, expected, _rain in rows:
            per_day.setdefault(day, {})[name] = (actual, expected)
    scores: dict[str, float] = {}
    for per_day in buckets.values():
        latest = [per_day[key] for key in sorted(per_day)[-MISMATCH_DAYS:]]
        for score in score_units(latest):
            scores[score.name] = score.relative
    return scores


def unit_losses(
    days: dict[str, dict[str, Any]],
    clear: list[tuple[date, float, float]],
    units: list[DeclaredUnit],
    installed: float,
    *,
    today: date,
    shares: dict[str, float] | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    tz: Any = None,
    shading: list[tuple[str | None, Any]] | None = None,
    today_clipping: float = 0.0,
    soiling_days: int = SOILING_DAYS,
    degradation_days: int = 730,
) -> dict[str, UnitLoss]:
    """Each declared unit's own losses, from its own clear-sky expectation.

    Soiling, degradation and performance index come from the unit's own series; mismatch from its peers of the same
    orientation; shading from the windows found on its own line; clipping from its share of what the array lost.
    Everything that needs more history than available stays ``None`` so the panel shows "learning".
    """
    if not units:
        return {}
    shares = shares or capacity_shares(units, installed)
    series: dict[str, list[tuple[date, float, float, float]]] = {}
    for unit in units:
        rows = []
        for day, _pi, rain in clear:
            record = days.get(day.isoformat())
            if record is None:
                continue
            actual = _num(record.get(unit.kind, {}).get(unit.name)) or 0.0
            if actual <= 0:
                continue
            expected = unit_expected(day, unit, shares.get(unit.name, 0.0), installed, record, latitude, longitude, tz)
            if expected > 0:
                rows.append((day, actual, expected, rain))
        series[unit.name] = rows
    scores = _peer_scores(series, units)
    record = days.get(today.isoformat())
    expected_today = {
        u.name: (
            unit_expected(today, u, shares.get(u.name, 0.0), installed, record, latitude, longitude, tz)
            if record
            else 0.0
        )
        for u in units
    }
    expected_total = sum(expected_today.values())
    out: dict[str, UnitLoss] = {}
    for unit in units:
        rows = series[unit.name]
        kwp = shares.get(unit.name, 0.0)
        produced = (_num((record or {}).get(unit.kind, {}).get(unit.name)) or 0.0) if record else 0.0
        modelled = sum(r[2] for r in rows)
        soiling = (
            soiling_srr([r[1] / r[2] for r in rows], rain=[r[3] for r in rows])
            if len(rows) >= soiling_days and modelled > 0
            else None
        )
        degr = degradation_yoy({r[0].toordinal(): r[1] / r[2] for r in rows}) if len(rows) >= degradation_days else None
        shaded = sum(w.kwh_per_day for name, w in shading or [] if name == unit.name)
        out[unit.name] = UnitLoss(
            name=unit.name,
            kind=unit.kind,
            kwp=unit.kwp,
            tilt=unit.tilt if unit.tilt is not None else DEFAULT_TILT,
            azimuth=unit.azimuth if unit.azimuth is not None else DEFAULT_AZIMUTH,
            count_in_total=unit.count_in_total,
            production_kwh=produced,
            expected_kwh=expected_today[unit.name] or None,
            performance=sum(r[1] for r in rows) / modelled if modelled > 0 else None,
            yield_kwh_per_kwp=produced / kwp if kwp > 0 else None,
            soiling=soiling.loss if soiling else None,
            shading_kwh=shaded if shading else None,
            mismatch=scores.get(unit.name),
            clipping_kwh=today_clipping * expected_today[unit.name] / expected_total
            if today_clipping and expected_total
            else 0.0,
            degradation_pct=degr.rate_pct_per_year if degr else None,
        )
    return out
