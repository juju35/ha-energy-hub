"""Render the panel with the demo snapshot and save one screenshot per tab, light and dark (for the README).

The snapshot is test/fixtures/demo.json: what the integration's demo plant gives at a fixed time (a summer afternoon
with clipping, a lagging string and recurring shading). The panel is loaded in headless Chromium with a mock `hass`
that answers the websocket commands with it. Only Playwright and Pillow are needed.

    python scripts/screenshots.py [--chrome /usr/bin/google-chrome] [--out screenshots] [--lang en]
    python scripts/screenshots.py --refresh-fixture   # rewrite the fixture from the demo plant (needs Home Assistant)
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PANEL = ROOT / "custom_components/energy_hub/frontend/energy-hub-panel.js"
FIXTURE = ROOT / "test/fixtures/demo.json"
TABS = ("overview", "production", "batteries", "losses", "finances", "settings")
NOW = datetime(2026, 7, 17, 15, 2, tzinfo=timezone(timedelta(hours=2)))
LAT, LON = 48.11, -1.68

DEMO_YAML = {
    "demo": True,
    "planes": [{"kwp": 3.28, "tilt": 30, "azimuth": 190}, {"kwp": 3.28, "tilt": 30, "azimuth": 190}],
    "inverter_max_kw": 4.2,
    "export_limit_kw": 4.5,
    "installation": {"cost": 9800, "subsidy": 1140, "commissioned": "2023-04-12"},
}

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;height:100%%;font-family:Roboto,Arial,sans-serif}
body.light{--primary-background-color:#fafafa;--card-background-color:#fff;--secondary-background-color:#f1f1ef;
--primary-text-color:#212121;--secondary-text-color:#727272;--divider-color:#e0e0e0}
body.dark{--primary-background-color:#111111;--card-background-color:#1c1c1c;--secondary-background-color:#262626;
--primary-text-color:#e1e1e1;--secondary-text-color:#9b9b9b;--divider-color:#333}
</style></head><body class="%(theme)s"><script>
const SNAP = %(snap)s; const SETTINGS = %(settings)s;
</script><script>%(panel)s</script><script>
const p = document.createElement('energy-hub-panel');
p.style.height = '100%%';
p.narrow = false;
document.body.appendChild(p);
p.hass = {
  language: '%(lang)s', locale: {language: '%(lang)s'}, themes: {darkMode: %(dark)s},
  connection: {subscribeMessage: (cb) => { setTimeout(() => cb(SNAP)); return Promise.resolve(() => {}); }},
  callWS: (msg) => Promise.resolve(msg.type === 'energy_hub/settings' ? SETTINGS : SNAP),
};
</script></body></html>"""


def snapshot() -> tuple[dict, dict]:
    """The demo snapshot and settings payloads, computed by the integration (Home Assistant must be installed)."""
    from custom_components.energy_hub import demo, settings_payload
    from custom_components.energy_hub.config import parse
    from custom_components.energy_hub.engine import build_snapshot
    from custom_components.energy_hub.history import History

    history = History()
    plant = demo.backfill(history, NOW, LAT, LON)
    reading = plant.step(NOW, 30)
    cfg = parse(DEMO_YAML)
    inst = demo.installation()
    snap = build_snapshot(history, inst, cfg, reading, NOW, demo=True)
    snap = json.loads(json.dumps(snap, default=str))
    return snap, settings_payload(cfg, inst, yaml_configured=True, show_panel=True)


def fixture_text() -> str:
    """The fixture file's content for the current demo plant."""
    snap, settings = snapshot()
    return json.dumps({"snapshot": snap, "settings": settings}, separators=(",", ":"), sort_keys=True) + "\n"


def _save(page, path: Path) -> None:
    """Screenshot to `path`, kept as is when the pixels are the same (so an identical render commits nothing)."""
    from PIL import Image, ImageChops

    data = page.screenshot()
    if path.exists():
        old = Image.open(path).convert("RGB")
        new = Image.open(io.BytesIO(data)).convert("RGB")
        if old.size == new.size and ImageChops.difference(old, new).getbbox() is None:
            return
    path.write_bytes(data)


def _serve(html: str):
    """Return a route handler answering with `html`, and with the panel's language files."""

    def handler(route) -> None:
        url = route.request.url
        if "/energy_hub_static/i18n/" in url:
            name = url.split("/i18n/")[1].split("?")[0]
            route.fulfill(path=str(PANEL.parent / "i18n" / name), content_type="application/json")
            return
        route.fulfill(body=html, content_type="text/html")

    return handler


def main() -> None:
    """Write screenshots/<lang>-<theme>-<tab>.png."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome", default=os.environ.get("CHROME_PATH"))
    parser.add_argument("--out", default=str(ROOT / "screenshots"))
    parser.add_argument("--lang", default="en")
    parser.add_argument("--refresh-fixture", action="store_true")
    args = parser.parse_args()
    if args.refresh_fixture:
        FIXTURE.write_text(fixture_text(), encoding="utf-8")
        return
    from playwright.sync_api import sync_playwright

    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    snap, settings = data["snapshot"], data["settings"]
    out = Path(args.out)
    out.mkdir(exist_ok=True)
    panel = PANEL.read_text(encoding="utf-8")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=args.chrome) if args.chrome else pw.chromium.launch()
        # The demo is a summer afternoon in western France: render it in its own time zone, whatever the runner's.
        page = browser.new_page(
            viewport={"width": 1100, "height": 900}, device_scale_factor=2, timezone_id="Europe/Paris"
        )
        page.clock.set_fixed_time(NOW)
        page.on("pageerror", lambda err: print("page error:", err, file=sys.stderr))
        for theme in ("light", "dark"):
            for tab in TABS:
                html = PAGE % {
                    "theme": theme,
                    "dark": "true" if theme == "dark" else "false",
                    "lang": args.lang,
                    "snap": json.dumps(snap),
                    "settings": json.dumps(settings),
                    "panel": panel,
                }
                page.route("http://panel.test/**", _serve(html))
                page.goto(f"http://panel.test/?tab={tab}")
                page.unroute("http://panel.test/**")
                page.wait_for_timeout(400)
                height = page.evaluate(
                    "() => document.querySelector('energy-hub-panel').shadowRoot.querySelector('.scroll').scrollHeight"
                )
                page.set_viewport_size({"width": 1100, "height": min(max(height, 400), 2400)})
                page.wait_for_timeout(150)
                _save(page, out / f"{theme}-{tab}.png")
                extra = {
                    "overview": [("overview-30d", ["[data-period='30d']"])],
                    "settings": [
                        ("settings-installation", ["[data-sub=installation]", "[data-node='battery:maison']"]),
                        ("settings-alerts", ["[data-sub=alerts]"]),
                        ("settings-tariffs", ["[data-sub=tariffs]"]),
                    ],
                }.get(tab, [])
                for name, clicks in extra:
                    for selector in clicks:
                        page.evaluate(
                            "(s) => document.querySelector('energy-hub-panel').shadowRoot.querySelector(s).dispatchEvent("
                            "new MouseEvent('click', {bubbles: true}))",
                            selector,
                        )
                        page.wait_for_timeout(120)
                    height = page.evaluate(
                        "() => document.querySelector('energy-hub-panel').shadowRoot.querySelector('.scroll').scrollHeight"
                    )
                    page.set_viewport_size({"width": 1100, "height": min(max(height, 400), 2400)})
                    page.wait_for_timeout(120)
                    _save(page, out / f"{theme}-{name}.png")
                if tab == "batteries":
                    page.evaluate(
                        "() => document.querySelector('energy-hub-panel').shadowRoot"
                        ".querySelector('[data-battery=maison]').click()"
                    )
                    page.wait_for_timeout(150)
                    page.evaluate(
                        "() => document.querySelector('energy-hub-panel').shadowRoot"
                        ".querySelector('[data-cell=\"23\"]').click()"
                    )
                    page.wait_for_timeout(150)
                    height = page.evaluate(
                        "() => document.querySelector('energy-hub-panel').shadowRoot.querySelector('.scroll').scrollHeight"
                    )
                    page.set_viewport_size({"width": 1100, "height": min(max(height, 400), 3200)})
                    page.wait_for_timeout(150)
                    _save(page, out / f"{theme}-cells.png")
                page.set_viewport_size({"width": 1100, "height": 900})
        browser.close()


if __name__ == "__main__":
    main()
