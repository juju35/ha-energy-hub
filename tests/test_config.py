"""The entity substitution and the declared installation: options win over YAML, kWp aggregation."""

from __future__ import annotations

from custom_components.energy_hub.config import HubConfig, UnitConfig, parse
from custom_components.energy_hub.const import CONF_ENTITIES, CONF_PANELS, CONF_PLANES, CONF_STRINGS
from custom_components.energy_hub.sources import Installation, UnitSource, _apply_yaml, role_entities

YAML = {
    "energy_hub": {
        "demo": True,
        "entities": {"grid_power": "sensor.indevolt_grid_power"},
    }
}


def test_options_replace_the_yaml_entities() -> None:
    cfg = parse(YAML["energy_hub"], {CONF_ENTITIES: {"grid_power": ["sensor.linky_zigbee_power"]}})
    assert cfg.entities["grid_power"] == ["sensor.linky_zigbee_power"]


def test_yaml_entities_are_kept_without_options() -> None:
    cfg = parse(YAML["energy_hub"], {})
    assert cfg.entities["grid_power"] == ["sensor.indevolt_grid_power"]


def test_a_role_accepts_several_entities() -> None:
    cfg = parse(
        YAML["energy_hub"],
        {CONF_ENTITIES: {"pv_power": ["sensor.fusionsolar_power", "sensor.indevolt_pv_power"]}},
    )
    assert cfg.entities["pv_power"] == ["sensor.fusionsolar_power", "sensor.indevolt_pv_power"]


def test_the_first_entity_present_here_drives_the_role() -> None:
    cfg = parse(
        YAML["energy_hub"],
        {CONF_ENTITIES: {"grid_power": ["sensor.indevolt_grid_power", "sensor.linky_zigbee_power"]}},
    )
    inst = Installation()
    # Only the Zigbee module exists in this Home Assistant: it becomes the primary, the other one stays a fallback.
    _apply_yaml(cfg, inst, ["sensor.linky_zigbee_power"])
    assert inst.roles["grid_power"] == "sensor.linky_zigbee_power"
    assert inst.alternatives["grid_power"] == ["sensor.indevolt_grid_power"]
    assert role_entities(inst, "grid_power") == ["sensor.linky_zigbee_power", "sensor.indevolt_grid_power"]


def test_options_entities_are_normalised() -> None:
    cfg: HubConfig = parse(YAML["energy_hub"], {CONF_ENTITIES: {"grid_power": "sensor.linky_zigbee_power"}})
    assert cfg.entities["grid_power"] == ["sensor.linky_zigbee_power"]


DECLARED_YAML = {
    "energy_hub": {
        "planes": [{"kwp": 3.28, "tilt": 30, "azimuth": 180}],
        "strings": [{"name": "Toit sud", "power": "sensor.pv_sud", "kwp": 1.5}],
        "panels": [{"name": "Garage", "power": "sensor.pv_garage", "kwp": 0.4}],
    }
}


def test_a_unit_configured_without_orientation_stays_valid() -> None:
    unit = UnitConfig("Toit", "sensor.pv_toit", None, None, 2.0)
    assert (unit.tilt, unit.azimuth, unit.count_in_total) == (None, None, None)


def test_yaml_installation_is_kept_without_options() -> None:
    cfg = parse(DECLARED_YAML["energy_hub"], {})
    assert cfg.planes[0].kwp == 3.28
    assert cfg.strings[0].name == "Toit sud"
    assert cfg.panels[0].name == "Garage"


def test_options_replace_the_yaml_installation() -> None:
    cfg = parse(
        DECLARED_YAML["energy_hub"],
        {
            CONF_PLANES: [{"kwp": 6.0, "tilt": 15, "azimuth": 90}],
            CONF_STRINGS: [],
            CONF_PANELS: [{"name": "Pergola", "power": "sensor.pv_pergola", "kwp": 1.2}],
        },
    )
    assert [p.kwp for p in cfg.planes] == [6.0]
    assert cfg.strings == []  # an empty list is a declaration too: nothing declared
    assert [u.name for u in cfg.panels] == ["Pergola"]


def test_options_orientation_reaches_the_units() -> None:
    cfg = parse(
        DECLARED_YAML["energy_hub"],
        {
            CONF_STRINGS: [
                {
                    "name": "Toit sud",
                    "power": "sensor.pv_sud",
                    "kwp": 1.5,
                    "tilt": 45,
                    "azimuth": 200,
                    "count_in_total": False,
                }
            ]
        },
    )
    unit = cfg.strings[0]
    assert (unit.tilt, unit.azimuth, unit.count_in_total) == (45, 200, False)


def test_kwp_is_the_planes_when_there_are_any() -> None:
    """The declared string and panel sit on the plane: their kWp is not added to it a second time."""
    cfg = parse(DECLARED_YAML["energy_hub"], {})
    assert cfg.kwp == 3.28


def test_kwp_falls_back_to_the_strings_without_a_plane() -> None:
    cfg = parse(
        {
            "strings": [
                {"name": "Est", "power": "sensor.pv_est", "kwp": 1.5},
                {"name": "Ouest", "power": "sensor.pv_ouest", "kwp": 2.0},
                {"name": "Abri", "power": "sensor.pv_abri", "kwp": 0.4, "count_in_total": False},
            ],
            "panels": [{"name": "Garage", "power": "sensor.pv_garage", "kwp": 0.4}],
        },
        {},
    )
    assert cfg.kwp == 3.5  # strings counted once, panels are modules of them, the left-out string stays out


def test_kwp_ignores_a_unit_without_capacity() -> None:
    cfg = parse({"strings": [{"name": "Inconnue", "power": "sensor.pv_x"}]}, {})
    assert cfg.kwp == 0.0


def test_a_declared_unit_renames_the_detected_one() -> None:
    cfg = parse(
        {"strings": [{"name": "Toit sud", "power": "sensor.inverter_string_1", "kwp": 2.0}]},
        {},
    )
    inst = Installation()
    inst.strings = [UnitSource("PV1", "sensor.inverter_string_1", kwp=1.9, tilt=45, azimuth=90)]
    _apply_yaml(cfg, inst, [])
    assert len(inst.strings) == 1
    unit = inst.strings[0]
    assert unit.name == "Toit sud"  # the declaration renames, it does not duplicate
    assert unit.declared is True
    assert unit.tilt == 45 and unit.azimuth == 90  # the detection's orientation is kept
    assert unit.kwp == 2.0
    assert unit.standalone is False  # a renamed detected unit is already inside the meter's total


def test_a_declared_unit_of_its_own_is_standalone() -> None:
    cfg = parse({"strings": [{"name": "Garage", "power": "sensor.pv_garage"}]}, {})
    inst = Installation()
    inst.strings = [UnitSource("PV1", "sensor.inverter_string_1")]
    _apply_yaml(cfg, inst, [])
    assert [u.standalone for u in inst.strings] == [False, True]


def test_a_declared_orientation_overrides_the_detected_one() -> None:
    cfg = parse(
        {
            "panels": [
                {"name": "Garage", "power": "sensor.pv_garage", "tilt": 15, "azimuth": 270, "count_in_total": False}
            ]
        },
        {},
    )
    inst = Installation()
    inst.units = [UnitSource("Panneau 1", "sensor.pv_garage", kwp=0.4, tilt=45, azimuth=180)]
    _apply_yaml(cfg, inst, [])
    unit = inst.units[0]
    assert (unit.tilt, unit.azimuth) == (15, 270)
    assert unit.count_in_total is False
    assert unit.declared is True
