"""Panels and strings declared in YAML, and the user's own profiles (issue #28)."""

from __future__ import annotations

from pathlib import Path

import pytest
import voluptuous as vol

from custom_components.energy_hub.config import parse
from custom_components.energy_hub.sources import PROFILES_DIR, Installation, UnitSource, _apply_yaml, load_profiles


def test_yaml_panels_are_added_to_the_detected_ones() -> None:
    inst = Installation(units=[UnitSource("Panel 1", "sensor.zendure_pv1_power")])
    cfg = parse(
        {
            "panels": [
                {"name": "TM 1", "power": "sensor.solar_tm_l2000m_pv1_power"},
                {"name": "TM 2", "voltage": "sensor.tm_pv2_voltage", "current": "sensor.tm_pv2_current", "kwp": 0.5},
            ]
        }
    )
    _apply_yaml(cfg, inst, [])
    assert [(u.name, u.power, u.voltage, u.kwp) for u in inst.units] == [
        ("Panel 1", "sensor.zendure_pv1_power", None, None),
        ("TM 1", "sensor.solar_tm_l2000m_pv1_power", None, None),
        ("TM 2", None, "sensor.tm_pv2_voltage", 0.5),
    ]


def test_a_yaml_panel_renames_the_detected_one_on_the_same_entity() -> None:
    inst = Installation(units=[UnitSource("Panel pv1", "sensor.tm_pv1_power")])
    _apply_yaml(parse({"panels": [{"name": "Roof east", "power": "sensor.tm_pv1_power"}]}), inst, [])
    assert [(u.name, u.power) for u in inst.units] == [("Roof east", "sensor.tm_pv1_power")]


def test_yaml_strings_and_ignore() -> None:
    inst = Installation()
    cfg = parse(
        {
            "strings": [{"name": "MPPT 1", "power": "sensor.mppt1_power"}, {"name": "MPPT 2", "power": "sensor.m2"}],
            "ignore": ["sensor.m2"],
        }
    )
    _apply_yaml(cfg, inst, [])
    assert [u.name for u in inst.strings] == ["MPPT 1"]


def test_a_yaml_panel_needs_a_power_or_voltage_and_current() -> None:
    with pytest.raises(vol.Invalid):
        parse({"panels": [{"name": "TM 1", "voltage": "sensor.tm_pv1_voltage"}]})
    with pytest.raises(vol.Invalid):
        parse({"panels": [{"power": "sensor.tm_pv1_power"}]})


def test_user_profiles_are_loaded_and_replace_a_builtin(tmp_path: Path) -> None:
    builtin = load_profiles()
    a_key = builtin[0].key
    (tmp_path / "tm_l2000m.yaml").write_text(
        "name: TM-L2000M\nplatform: template\nunits:\n  power: ['^solar_tm_l2000m_(pv\\d)_power$']\n",
        encoding="utf-8",
    )
    (tmp_path / f"{a_key}.yaml").write_text("name: Mine\nplatform: mine\n", encoding="utf-8")
    (tmp_path / "broken.yaml").write_text("name: [unclosed\n", encoding="utf-8")
    (tmp_path / "no_platform.yaml").write_text("name: Nothing\n", encoding="utf-8")
    profiles = {p.key: p for p in load_profiles(PROFILES_DIR, tmp_path)}
    assert len(profiles) == len(builtin) + 1
    assert profiles["tm_l2000m"].platform == "template"
    assert profiles["tm_l2000m"].units["power"][0].search("solar_tm_l2000m_pv3_power").group(1) == "pv3"
    assert profiles[a_key].name == "Mine"
    assert "broken" not in profiles and "no_platform" not in profiles


def test_a_missing_user_profile_folder_is_fine(tmp_path: Path) -> None:
    assert len(load_profiles(PROFILES_DIR, tmp_path / "missing")) == len(load_profiles())
