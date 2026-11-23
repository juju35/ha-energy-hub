"""Every translation has exactly the keys and placeholders of the English one, and names every sensor."""

import json
import re
from pathlib import Path

import pytest

from custom_components.energy_hub.sensor import SENSORS

TRANSLATIONS = Path(__file__).parents[1] / "custom_components" / "energy_hub" / "translations"
PLACEHOLDER = re.compile(r"\{\w+\}")
LANGUAGES = sorted(p.stem for p in TRANSLATIONS.glob("*.json") if p.stem != "en")


def _load(lang: str) -> dict:
    return json.loads((TRANSLATIONS / f"{lang}.json").read_text(encoding="utf-8"))


def _strings(data: dict, prefix: str = "") -> dict[str, str]:
    strings = {}
    for key, value in data.items():
        if isinstance(value, dict):
            strings |= _strings(value, f"{prefix}{key}.")
        else:
            strings[prefix + key] = value
    return strings


def test_french_is_shipped():
    assert "fr" in LANGUAGES


@pytest.mark.parametrize("lang", LANGUAGES)
def test_same_keys_and_placeholders(lang):
    english = _strings(_load("en"))
    other = _strings(_load(lang))
    assert set(other) == set(english)
    for key, text in english.items():
        assert set(PLACEHOLDER.findall(other[key])) == set(PLACEHOLDER.findall(text)), key


def test_every_sensor_has_a_name():
    names = _load("en")["entity"]["sensor"]
    assert {d.translation_key for d in SENSORS} == set(names)
