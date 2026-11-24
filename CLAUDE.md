# Repository guide for agents

## Commits
- Write every commit message in **English**, following **Conventional Commits**:
  `type(scope): subject` — types: `feat`, `fix`, `chore`, `docs`, `style`, `refactor`,
  `perf`, `test`, `build`, `ci`, `revert`. Subject in imperative mood, lower case,
  no trailing period, ≤ 72 chars.
- Author identity must be **juju35** (`juju35 <julienstephan29@gmail.com>`), never an assistant identity.
- Messages are checked by **commitlint** (Conventional Commits) via the pre-commit
  `commit-msg` hook; run `pre-commit install` once so the hook is active locally.
- **External contributions**: add the contributor as a commit **co-author** (their GitHub
  noreply address) **only** when they supplied a patch/PR, a translation or a validated
  profile — never for a mere idea or feature issue.
- Keep history clean and linear: small, focused commits, one logical change each.
- `main` is protected by a ruleset: **squash-merge only**, the commit message is the PR
  **title + description** (not the commit list, so the screenshots bot's commits never
  reach `main`); tags follow a `v*` ruleset.

## Before opening a PR — run the checks locally
CI mirrors these; running them first avoids round-trips:
```sh
npm ci && node scripts/build-frontend.mjs   # assembles the frontend files (not committed) the checks below read
pre-commit run -a
vulture custom_components .vulture_whitelist.py --min-confidence 60
npx --yes jscpd@5.4.2 .
pytest
node --test test/*.test.mjs
```

## Releasing — how it works here
A release is **automatic**: on push to `main`, if `manifest.json` carries a version with
no matching tag, the Release workflow publishes `vX.Y.Z`. **Never create a tag by hand.**

The `Version consistency` check (validate.yml) requires the **same version in every place**,
or the release fails.

## Bumping the version
This is an **INTEGRATION** repo. A bump is complete only when **every** file below
carries the new version, updated together in one commit:
1. `CHANGELOG.md` → add a "## X.Y.Z - YYYY-MM-DD" section at the top (`### Features` | `Fixes` | `Performance` | `Maintenance`).
2. `custom_components/energy_hub/manifest.json` → `"version": "X.Y.Z"`.
3. `custom_components/energy_hub/const.py` → `VERSION: Final = "X.Y.Z"`.
4. `src/energy-hub-panel/core.js` → `ENERGY_HUB_PANEL_VERSION = 'X.Y.Z'` (assembled into `custom_components/energy_hub/frontend/energy-hub-panel.js`).
- Bump rule: `fix` → patch, `feat` → minor, breaking change → major.
- The PR/commit title carries the version in parentheses, e.g. `feat: new option (X.Y.Z)`.

## Architecture
- `analytics/`: pure Python, no Home Assistant import, no numpy — clear sky, KPIs, clipping, soiling,
  degradation, shading, mismatch, batteries, cells, finance. Each module cites the method it follows;
  `tests/test_analytics.py` checks them against synthetic series whose answer is known.
- `profiles/*.yaml`: one per integration — entity regexes per role (on the entity's object id),
  strings/units, battery fields, sign conventions, capabilities. New ones start as `status: beta` and
  become `stable` once a user validated them (issue template *Profile validation*).
- `sources.py` detects the installation (Energy dashboard prefs → profiles → YAML, YAML wins);
  `history.py` integrates readings into buckets, bins and daily records; `engine.py` builds the
  snapshot the panel and the sensors read; `demo.py` simulates an installation.
- The panel (`frontend/energy-hub-panel.js`, assembled from `src/energy-hub-panel/`) is one vanilla custom element, MDI paths inlined,
  en/fr strings inside; it only renders the snapshot (no computation beyond the payback slider).
- After a change of the demo or of the snapshot's shape: `python scripts/screenshots.py --refresh-fixture`
  (a test fails while `test/fixtures/demo.json` is stale).

## README layout
- Header order: H1, then the badge row, then the repo's **own logo** centered under the badges —
  `<p align="center"><img src=".../custom_components/energy_hub/brand/icon.png" width="120"></p>`.
- **Work in progress**: while the profiles still wait for real installations, the animated
  `images/wip.svg` banner sits right under the logo, in its own centered block
  (`<p align="center"><img src=".../images/wip.svg" alt="Work in progress…" width="720"></p>`). The showcase
  site mirrors it with `wip: true` on the project; remove both together once the project is stable.
- **Brand logos**: under `## Supported integrations`, a centered `<p align="center">` row of the
  logos of the integrations it builds on, each linking to the integration.
- Keep image `width`/`height` bounded so it doesn't render oversized (HACS/Marketplace).
- The README is consumed by the **homeassistant-projects** showcase site at build — keep its
  structure intact. Keep the **Marketplace** install section (badge/button, "Settings →
  Marketplace → Add from link") and the **Buy Me a Coffee** link; the public description must
  not mention the author's city.

## Supported integrations
This builds on other Home Assistant integrations, so keep the `## Supported integrations` section (title verbatim) listing the HA integrations it works on top of, with a link to each, in step with `profiles/`.

## Source layout
- The hand-written frontend is split into ES modules: `src/energy-hub-panel/` (entry `src/energy-hub-panel/index.js`). `scripts/build-frontend.mjs` (`scripts/bundle.mjs`)
  assembles each into `custom_components/energy_hub/frontend/energy-hub-panel.js`, the classic script Home Assistant serves: modules concatenated in
  the order of the entry file, import lines removed, `export` keywords dropped. The assembled files are **not
  committed** (`.gitignore`): build them before the tests, the screenshots and the release zip.
  Smaller frontend files (under ~40 KB) stay hand-written in `custom_components/energy_hub/frontend/`.
- Modules share one scope once assembled, so keep top-level names unique across modules; a new module must be listed
  in its `index.js`.
- Strings: English in `src/energy-hub-panel/strings.js` (`EH_I18N`); the other languages stay JSON files in `custom_components/energy_hub/frontend/i18n/<lang>.json` (committed, fetched on demand).

## Translations
- English is the source. Keep every language in sync when a user-facing string changes.
- Languages to keep in sync: en, fr, de, es, it, nl, pt, pl, sr, sr-Latn, ro, da, sv, bg, ru, uk, hu, sk, cs, sl, lv, el (no Irish or Maltese).
- Integration strings: `custom_components/energy_hub/translations/*.json`.
- Panel strings: English in `EH_I18N.en` inside the panel; every other language in
  `custom_components/energy_hub/frontend/i18n/<lang>.json`, fetched on demand (list in `EH_LANGS`).
- Tests check that every language has exactly the English keys and placeholders.

## Screenshots — do not edit or commit them by hand
The Screenshots workflow regenerates them on the PR branch and commits them as the
`juju35-screenshots[bot]` GitHub App, so the PR checks re-run on that commit by themselves.
They are English, with light/dark twins, rendered from the demo fixture (never real data).

## Conventions
- Prefer YAML over UI configuration; keep configurations minimal; test iteratively.
- Keep `ha-*` repos **independent**: no shared/factored code across repos — duplication is fine.
- English-only README and screenshots; mock/neutral data in any published screenshot.
- Call it the **Marketplace** (Home Assistant 2026.11), not HACS, in docs, issue comments
  and user replies.
- Reply to GitHub issues in the **language of the issue / reporter**, not French by default.
