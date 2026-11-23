// Unit tests for the panel: the panel file is evaluated with stubs and each tab is rendered to a string from the demo
// snapshot (test/fixtures/demo.json, written by the integration's demo plant), no browser needed.
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

process.env.TZ = 'Europe/Paris';

const source = readFileSync(new URL('../custom_components/energy_hub/frontend/energy-hub-panel.js', import.meta.url), 'utf8');
const { snapshot, settings } = JSON.parse(readFileSync(new URL('./fixtures/demo.json', import.meta.url), 'utf8'));

class FakeElement {
  attachShadow() {
    this.shadowRoot = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    return this.shadowRoot;
  }
}

const context = {
  HTMLElement: FakeElement,
  customElements: { get: () => true, define() {} },
  location: { search: '', href: 'http://ha.local/energy-hub' },
  history: { replaceState() {} },
  URL,
  URLSearchParams,
  console,
  Date,
  Intl,
};
vm.createContext(context);
vm.runInContext(`${source}\nthis.e = { ehEsc, ehIcon, EH_I18N, EH_ICONS, EH_LANGS, EH_TABS, EnergyHubPanel, ENERGY_HUB_PANEL_VERSION };`, context);
const E = context.e;
// The language files the panel fetches, loaded up front
const I18N_DIR = new URL('../custom_components/energy_hub/frontend/i18n/', import.meta.url);
const FILES = readdirSync(I18N_DIR).filter((f) => f.endsWith('.json'));
for (const f of FILES) E.EH_I18N[f.slice(0, -5)] = JSON.parse(readFileSync(new URL(f, I18N_DIR), 'utf8'));

function panel(lang = 'en', data = snapshot) {
  const p = new E.EnergyHubPanel();
  p._hass = { locale: { language: lang }, themes: { darkMode: false } };
  p._data = structuredClone(data);
  p._settings = settings;
  return p;
}

test('the version matches the manifest', () => {
  const manifest = JSON.parse(readFileSync(new URL('../custom_components/energy_hub/manifest.json', import.meta.url), 'utf8'));
  assert.equal(E.ENERGY_HUB_PANEL_VERSION, manifest.version);
});

test('ehEsc escapes HTML', () => {
  assert.equal(E.ehEsc('<b a="1">\'&'), '&lt;b a=&quot;1&quot;&gt;&#39;&amp;');
  assert.equal(E.ehEsc(null), '');
});

test('every icon used is embedded', () => {
  const used = new Set([...source.matchAll(/ehIcon\('([a-z0-9-]+)'/g)].map((m) => m[1]));
  for (const [, icon] of E.EH_TABS) used.add(icon);
  for (const name of used) assert.ok(E.EH_ICONS[name], name);
});

function flat(o, prefix = '') {
  return Object.entries(o).flatMap(([k, v]) => (v && typeof v === 'object' && !Array.isArray(v) ? flat(v, `${prefix}${k}.`) : [[`${prefix}${k}`, v]]));
}

test('every language file has the English keys and placeholders', () => {
  assert.deepEqual(FILES.map((f) => f.slice(0, -5)).sort(), [...E.EH_LANGS].sort());
  const en = Object.fromEntries(flat(E.EH_I18N.en));
  const ph = (v) => (Array.isArray(v) ? v.join(' ') : String(v)).match(/\{\w+\}/g)?.sort() ?? [];
  for (const lang of E.EH_LANGS) {
    const other = Object.fromEntries(flat(E.EH_I18N[lang]));
    assert.deepEqual(Object.keys(other).sort(), Object.keys(en).sort(), lang);
    for (const k of Object.keys(en)) {
      assert.deepEqual(ph(other[k]), ph(en[k]), `${lang}.${k}`);
      if (Array.isArray(en[k])) assert.equal(other[k].length, en[k].length, `${lang}.${k}`);
    }
  }
});

test('language of Home Assistant: regional and script variants', () => {
  const p = new E.EnergyHubPanel();
  for (const [ha, lang] of [['fr-FR', 'fr'], ['pt-BR', 'pt'], ['sr-Latn', 'sr-Latn'], ['sr', 'sr'], ['xx', 'en']]) {
    p._hass = { locale: { language: ha } };
    assert.equal(p._lang, lang, ha);
  }
});

test('every tab renders the demo snapshot, in both languages', () => {
  for (const lang of ['en', ...E.EH_LANGS]) {
    const p = panel(lang);
    for (const [tab] of E.EH_TABS) {
      p._tab = tab;
      const html = p._header() + { overview: p._overview, production: p._production, batteries: p._batteries, losses: p._losses, finances: p._finances, settings: p._settingsTab }[tab].call(p);
      assert.ok(html.length > 1000, `${lang}/${tab}`);
      assert.ok(!/undefined|NaN/.test(html), `${lang}/${tab}: ${html.match(/.{40}(undefined|NaN).{40}/)?.[0]}`);
    }
  }
});

test('the alerts of the demo are worded', () => {
  const html = panel('en')._alertTiles();
  assert.match(html, /Clipping \d+:\d\d – \d+:\d\d/);
  assert.match(html, /String 2 lagging/);
  assert.match(html, /Shading P15/);
});

test('a battery and its cells', () => {
  const p = panel('en');
  p._battery = 'maison';
  const html = p._batteries();
  assert.match(html, /Cells · 48/);
  assert.match(html, /3 modules × 16 cells/);
  assert.match(html, /threshold 50 mV in \d+ days/);
  assert.match(html, /State of health · 3 years/);
  assert.match(html, /baldot/);
  p._cell = 23;
  assert.match(p._batteries(), /Drifts -?\d/);
  p._battery = 'garage';
  assert.match(p._batteries(), /does not report its cells/);
});

test('periods, events, calendar, bill and settings sub-tabs', () => {
  const p = panel('en');
  for (const period of ['7d', '30d', '12m']) {
    p._period = period;
    assert.ok(!/undefined|NaN/.test(p._curve()), period);
  }
  assert.match(p._events(), /Recurring/);
  assert.match(p._events(), /Resolved/);
  assert.match(p._finances(), /Gains calendar/);
  assert.match(p._finances(), /Without solar/);
  for (const sub of ['sources', 'installation', 'tariffs', 'alerts', 'yaml']) {
    p._sub = sub;
    const html = p._settingsTab();
    assert.ok(!/undefined|NaN/.test(html), `${sub}: ${html.match(/.{40}(undefined|NaN).{40}/)?.[0]}`);
  }
  p._sub = 'installation';
  p._node = 'battery:garage';
  assert.match(p._settingsTab(), /AC-coupled/);
  p._sub = 'sources';
  assert.match(p._settingsTab(), /Attach Balcon BMS to the Balcon battery/);
  assert.match(p._settingsTab(), /Data quality · 24 h/);
});

test('break-even moves with the price rise', () => {
  const p = panel('en');
  const slow = p._breakEven(0);
  const fast = p._breakEven(8);
  assert.ok(fast.gain20 > slow.gain20);
  assert.match(slow.sub, /in [\d.]+ years/);
});

test('without batteries nor cost the panel still renders', () => {
  const data = structuredClone(snapshot);
  data.batteries = { items: [], fleet: null, autonomy_h: null };
  data.finances = { ...data.finances, net_cost: null, share_paid: null };
  data.alerts = [];
  const p = panel('en', data);
  assert.ok(p._overview().includes('Solar'));
  assert.ok(p._batteries().includes('none'));
  assert.ok(p._finances().includes('installation: cost:'));
});
