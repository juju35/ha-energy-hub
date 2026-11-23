"""The panel's demo fixture (test/fixtures/demo.json, used by the panel tests and the screenshots) is up to date."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_demo_fixture_is_current():
    spec = importlib.util.spec_from_file_location("screenshots", ROOT / "scripts" / "screenshots.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    current = (ROOT / "test" / "fixtures" / "demo.json").read_text(encoding="utf-8")
    assert current == module.fixture_text(), "run: python scripts/screenshots.py --refresh-fixture"
