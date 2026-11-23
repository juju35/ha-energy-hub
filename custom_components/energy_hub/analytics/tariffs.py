"""Electricity offers: the price of each half hour, and what a year of real grid draw would cost under each offer.

The regulated offers (Tarif Bleu Base, Heures Creuses, Tempo) are set by the State twice a year (1 February,
1 August) from the CRE's proposal; the Zen offers are EDF market offers it may revise at most twice a year with a
month's notice. Neither has a free feed covering every offer, so the grid below is the one EDF publishes, embedded
and updated by release (``GRID_DATE``), and any part of it can be overridden in YAML (``tariff: offers:``).

Day kinds:
- Tempo: a colour per day (blue, white, red), from 6:00 to 6:00 the next day; off-peak 22:00-6:00.
- Zen Flex: an "eco" or "sobriety" day; peak 8:00-13:00 and 18:00-20:00 (17 off-peak hours).
- Zen Week-End: Saturdays, Sundays and French public holidays at the week-end price.
Past days whose colour was not recorded are priced with the expected mix of the season (``expected_mix``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from typing import Any

GRID_DATE = "2026-11-04"
GRID_SOURCES = {
    "regulated": "https://particulier.edf.fr/fr/accueil/electricite-gaz/tarif-bleu.html",
    "zen": "https://particulier.edf.fr/fr/accueil/electricite-gaz/offres-electricite/offres-marche/electricite-weekend/zen-week-end.html",
}
# Months after which the embedded grid is flagged as possibly outdated (one revision is due every six months).
GRID_STALE_MONTHS = 7

# Yearly subscription (EUR incl. VAT) per kVA, shared by Base, Heures Creuses and the Zen offers (1 August 2026).
SUBSCRIPTION = {3: 145.56, 6: 190.32, 9: 238.56, 12: 285.12, 15: 328.80, 18: 373.68, 24: 469.68, 30: 557.64, 36: 646.56}
TEMPO_SUBSCRIPTION = {6: 189.60, 9: 236.40, 12: 282.00, 15: 324.12, 18: 368.28, 30: 549.84, 36: 645.12}

# kind: how the price of a half hour is found. prices: by "from kVA" threshold, the price of each slot (EUR/kWh).
OFFERS: dict[str, dict[str, Any]] = {
    "base": {
        "name": "Tarif Bleu · Base",
        "regulated": True,
        "kind": "base",
        "subscription": SUBSCRIPTION,
        "prices": {3: {"base": 0.2001}, 9: {"base": 0.1985}},
    },
    "hphc": {
        "name": "Tarif Bleu · Heures Creuses",
        "regulated": True,
        "kind": "hphc",
        "subscription": SUBSCRIPTION,
        "prices": {3: {"hp": 0.2142, "hc": 0.1589}},
    },
    "tempo": {
        "name": "Tarif Bleu · Tempo",
        "regulated": True,
        "kind": "tempo",
        "subscription": TEMPO_SUBSCRIPTION,
        "prices": {
            6: {
                "blue_hc": 0.1356,
                "blue_hp": 0.1654,
                "white_hc": 0.1536,
                "white_hp": 0.1921,
                "red_hc": 0.1615,
                "red_hp": 0.7295,
            }
        },
    },
    "zen_weekend": {
        "name": "Zen Week-End",
        "regulated": False,
        "kind": "weekend",
        "subscription": SUBSCRIPTION,
        "prices": {3: {"week": 0.2285, "weekend": 0.1710}},
    },
    "zen_weekend_hc": {
        "name": "Zen Week-End · Heures Creuses",
        "regulated": False,
        "kind": "weekend_hphc",
        "subscription": SUBSCRIPTION,
        "prices": {6: {"hp": 0.2359, "hc": 0.1762, "weekend": 0.1762}},
    },
    "zen_flex": {
        "name": "Zen Week-End · Flex",
        "regulated": False,
        "kind": "flex",
        "subscription": SUBSCRIPTION,
        "prices": {6: {"eco_hp": 0.2142, "eco_hc": 0.1595, "sobriety_hp": 0.7467, "sobriety_hc": 0.2142}},
    },
}
CONTRACTS = tuple(OFFERS)

TEMPO_OFFPEAK = ((22 * 60, 6 * 60),)
FLEX_PEAK = ((8 * 60, 13 * 60), (18 * 60, 20 * 60))
DEFAULT_OFFPEAK = ((22 * 60, 6 * 60),)

# Day kinds read from the colour entities of Tarif EDF, RTE Tempo and EDF Zen Flex, in any case.
COLOR_NAMES = {
    "bleu": "blue",
    "blue": "blue",
    "blanc": "white",
    "white": "white",
    "rouge": "red",
    "red": "red",
    "eco": "eco",
    "éco": "eco",
    "sobriete": "sobriety",
    "sobriété": "sobriety",
    "sobriety": "sobriety",
}


DAY_KINDS = {"tempo": ("blue", "white", "red"), "flex": ("eco", "sobriety")}


def normalize_color(value: str | None) -> str | None:
    return COLOR_NAMES.get((value or "").strip().lower())


def parse_ranges(text: str | None) -> tuple[tuple[int, int], ...]:
    """``"22:00-06:00,12:30-14:30"`` as ``((1320, 360), (750, 870))`` minutes (a range may cross midnight)."""
    out = []
    for part in (text or "").split(","):
        start, sep, end = part.strip().partition("-")
        if not sep:
            continue
        try:
            sh, sm = (int(x) for x in start.split(":"))
            eh, em = (int(x) for x in end.split(":"))
        except ValueError:
            continue
        out.append((sh * 60 + sm, eh * 60 + em))
    return tuple(out)


def in_ranges(minute: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    for start, end in ranges:
        if start <= end:
            if start <= minute < end:
                return True
        elif minute >= start or minute < end:
            return True
    return False


def easter(year: int) -> date:
    """Gregorian Easter Sunday (anonymous Gregorian algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month, day = divmod(h + ell - 7 * m + 114, 31)
    return date(year, month, day + 1)


@lru_cache(maxsize=8)
def french_holidays(year: int) -> frozenset[date]:
    e = easter(year)
    fixed = [(1, 1), (5, 1), (5, 8), (7, 14), (8, 15), (11, 1), (11, 11), (12, 25)]
    return frozenset({date(year, m, d) for m, d in fixed} | {e + timedelta(days=d) for d in (1, 39, 50)})


def is_weekend(day: date) -> bool:
    return day.weekday() >= 5 or day in french_holidays(day.year)


def expected_mix(day: date, kind: str) -> dict[str, float]:
    """Probabilities of the day kinds when the day's colour is unknown: Tempo's 300 blue, 43 white and 22 red days
    (red only on winter weekdays, white never on Sundays), Zen Flex's ~22 sobriety days on winter weekdays."""
    winter = day.month in (11, 12, 1, 2, 3)
    if kind == "flex":
        return {"sobriety": 0.2, "eco": 0.8} if winter and not is_weekend(day) else {"eco": 1.0}
    if day.weekday() == 6:
        return {"blue": 1.0}
    if winter and day.weekday() < 5:
        return {"red": 0.2, "white": 0.25, "blue": 0.55}
    if winter:
        return {"white": 0.2, "blue": 0.8}
    return {"white": 0.03, "blue": 0.97}


@dataclass(slots=True)
class Offer:
    key: str
    name: str
    kind: str
    regulated: bool
    subscription: float | None
    prices: dict[str, float]
    offpeak: tuple[tuple[int, int], ...] = DEFAULT_OFFPEAK
    custom: bool = False

    def slot_price(self, day: date, minute: int, colors: dict[str, str] | None = None) -> float:
        """Price of the half hour starting ``minute`` after midnight on ``day`` (expected price if the colour of a
        Tempo / Flex day is unknown)."""
        p = self.prices
        kind = self.kind
        if kind == "base":
            return p["base"]
        if kind == "hphc":
            return p["hc"] if in_ranges(minute, self.offpeak) else p["hp"]
        if kind == "weekend":
            return p["weekend"] if is_weekend(day) else p["week"]
        if kind == "weekend_hphc":
            if is_weekend(day):
                return p["weekend"]
            return p["hc"] if in_ranges(minute, self.offpeak) else p["hp"]
        colors = colors or {}
        if kind == "tempo":
            # The Tempo day runs from 6:00 to 6:00: the night belongs to the previous day's colour.
            color_day = day - timedelta(days=1) if minute < 6 * 60 else day
            period = "hc" if in_ranges(minute, TEMPO_OFFPEAK) else "hp"
        else:
            color_day = day
            period = "hp" if in_ranges(minute, FLEX_PEAK) else "hc"
        known = normalize_color(colors.get(color_day.isoformat()))
        # A colour of the other scheme (a Tempo colour for a Zen Flex day) says nothing: the season's mix then.
        mix = {known: 1.0} if known in DAY_KINDS[kind] else expected_mix(color_day, kind)
        return sum(share * p.get(f"{c}_{period}", 0.0) for c, share in mix.items())


def _by_kva(table: dict[int, Any], kva: int) -> Any:
    keys = sorted(k for k in table if k <= kva)
    return table[keys[-1]] if keys else None


def offers(
    kva: int, offpeak: tuple[tuple[int, int], ...] = DEFAULT_OFFPEAK, overrides: dict[str, dict] | None = None
) -> list[Offer]:
    """Every offer available at ``kva`` (an offer starting above it is left out), with the user's overrides: a key
    of ``OFFERS`` gets its subscription / prices replaced, any other key is a custom offer of one of the kinds."""
    overrides = overrides or {}
    out = []
    for key, spec in OFFERS.items():
        prices = _by_kva(spec["prices"], kva)
        sub = spec["subscription"].get(kva)
        if prices is None or sub is None:
            continue
        o = overrides.get(key, {})
        out.append(
            Offer(
                key,
                o.get("name", spec["name"]),
                spec["kind"],
                spec["regulated"],
                o.get("subscription", sub),
                {**prices, **o.get("prices", {})},
                offpeak,
                custom=bool(o),
            )
        )
    for key, o in overrides.items():
        if key in OFFERS or o.get("kind") not in {s["kind"] for s in OFFERS.values()}:
            continue
        out.append(
            Offer(
                key,
                o.get("name", key),
                o["kind"],
                False,
                o.get("subscription"),
                dict(o.get("prices", {})),
                offpeak,
                True,
            )
        )
    return out


@dataclass(slots=True)
class Comparison:
    key: str
    name: str
    regulated: bool
    custom: bool
    energy_eur: float
    subscription_eur: float | None
    total_eur: float


def compare(
    days: list[tuple[date, list[float]]], offer_list: list[Offer], colors: dict[str, str] | None = None
) -> tuple[list[Comparison], float]:
    """Yearly cost of the recorded grid draw (48 half-hour kWh per day) under each offer, cheapest first.

    Fewer than 365 days are scaled to a year by the days recorded; the factor is returned with the result."""
    if not days:
        return [], 0.0
    scale = 365 / len(days)
    out = []
    for offer in offer_list:
        energy = 0.0
        for day, slots in days:
            for i, kwh in enumerate(slots):
                if kwh:
                    energy += kwh * offer.slot_price(day, i * 30, colors)
        energy *= scale
        sub = offer.subscription
        out.append(Comparison(offer.key, offer.name, offer.regulated, offer.custom, energy, sub, energy + (sub or 0.0)))
    out.sort(key=lambda c: c.total_eur)
    return out, scale
