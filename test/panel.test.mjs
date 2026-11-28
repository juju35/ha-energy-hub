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

test('the entities form: detected entity as placeholder, chosen ones as value, a typed draft wins', () => {
  const p = panel();
  p._sub = 'sources';
  let html = p._settingsTab();
  assert.match(html, /data-erole="pv_power"/);
  assert.match(html, /placeholder="sensor\.demo_inverter_input_power"/);
  assert.match(html, /added up/);
  p._data.entities.configured = { grid_power: ['sensor.zlinky_power', 'sensor.meter_power'] };
  html = p._settingsTab();
  assert.match(html, /data-erole="grid_power"[^>]*value="sensor\.zlinky_power, sensor\.meter_power"/);
  p._entDraft = { grid_power: 'sensor.typed' };
  assert.match(p._settingsTab(), /data-erole="grid_power"[^>]*value="sensor\.typed"/);
  assert.deepEqual([...p._unknownEntities('sensor.a, sensor.b')], ['sensor.a', 'sensor.b']);
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

test('offer comparator, contract and production reference', () => {
  const p = panel('en');
  const html = p._comparator();
  assert.match(html, /Offer comparator/);
  assert.match(html, /Switching to Tarif Bleu · Heures Creuses would save about/);
  assert.match(html, /your contract/);
  assert.ok(!/undefined|NaN/.test(html));
  p._sub = 'tariffs';
  assert.match(p._settingsTab(), /Tarif Bleu · Tempo/);
  assert.match(p._settingsTab(), /sensor\.demo_tarif_actuel_tempo_9kva_ttc/);
  assert.match(p._reference(), /Solar forecast/);
  assert.match(panel('fr')._comparator(), /Comparateur d&#39;offres/);

  const data = structuredClone(snapshot);
  data.finances.comparator = { ...data.finances.comparator, offers: [], days: 3 };
  assert.match(panel('en', data)._comparator(), /needs 14 days of grid readings \(3 so far\)/);
  data.finances.comparator = { ...snapshot.finances.comparator, current: null, grid_stale: true, scale: 2, colors: 100 };
  const unknown = panel('en', data)._comparator();
  assert.match(unknown, /Contract unknown/);
  assert.match(unknown, /more than 7 months old/);
  assert.match(unknown, /scaled to a year/);
});

test('large consumers: nodes under the home, stacked in the curves, their tariffs', () => {
  const p = panel('en');
  const flow = p._flow();
  assert.match(flow, /viewBox="0 0 680 296"/);
  assert.match(flow, /class="node cnode" title="EV charger"/);
  assert.match(flow, /class="node cnode" title="Heat pump"/);
  p._period = 'today';
  const today = p._curve();
  assert.match(today, /<path d="M[^"]+Z" fill="#D4537E" fill-opacity="\.45"\/>/, 'the EV charger is stacked in the day');
  assert.match(today, /<span class="chip"><span style="width:12px;height:10px;border-radius:2px;background:#D4537E;opacity:\.7"><\/span>EV charger<\/span>/);
  p._period = '7d';
  assert.match(p._curve(), /fill="#D4537E" fill-opacity="\.75"/);
  p._sub = 'tariffs';
  const tariffs = p._settingsTab();
  assert.match(tariffs, /Large consumers/);
  assert.match(tariffs, /EV charger<\/td><td>€0\.1848 \/kWh<\/td><td>own meter/);
  assert.match(tariffs, /Heat pump<\/td><td>contract price<\/td><td>main meter/);
  // Without consumers: the flow keeps its height, no node, no box
  const bare = panel('en', { ...snapshot, consumers: [] });
  assert.match(bare._flow(), /viewBox="0 0 680 228"/);
  assert.doesNotMatch(bare._flow(), /cnode/);
  bare._sub = 'tariffs';
  assert.doesNotMatch(bare._settingsTab(), /Large consumers/);
});

test('the production tab lists every declared string, with its friendly name', () => {
  const names = ['Toit sud', 'Toit nord', 'Garage', 'Balcon', 'Pergola', 'Abri bois'];
  const data = structuredClone(snapshot);
  data.production.strings = names.map((name, i) => ({
    name,
    kw: 2.5 - i * 0.2,
    kwh: 12 - i,
    relative: i === 0 ? 1.19 : 0.9,
    lagging_days: i === 1 ? 6 : 0,
    kwp: 3.2,
    tilt: 30,
    azimuth: 180,
    count_in_total: true,
  }));
  const html = panel('en', data)._production();
  for (const name of names) assert.match(html, new RegExp(`<b>${name}</b>`), `${name} is shown`);
  assert.equal(html.match(/class="barrow srow"/g).length, names.length, 'no cap on the number of strings');
  assert.match(html, /3\.20 kWp/);
  assert.match(html, /30° \/ 180°/);
  assert.match(html, /6 d behind its peers/);
  // An engine that does not send kwp/tilt/azimuth yet still renders, with no meta line
  data.production.strings = [{ name: 'String 1', kw: 1.2, kwh: 3.4 }];
  const legacy = panel('en', data)._production();
  assert.match(legacy, /<b>String 1<\/b>/);
  assert.equal(legacy.match(/<b>String 1<\/b>.*?<\/div>/)[0].includes('kWp'), false);
});

test('without declared strings the box keeps a clean empty state', () => {
  const data = structuredClone(snapshot);
  data.production.strings = [];
  const html = panel('en', data)._production();
  assert.match(html, /No string declared/);
  assert.doesNotMatch(html, /class="barrow srow"/);
});

// Objects built inside the panel come from the vm realm: compare plain JSON copies.
const plain = (v) => JSON.parse(JSON.stringify(v));


test('the install payload: numbers, optional fields, nameless rows dropped', () => {
  const p = panel('en');
  const payload = p._instPayload({
    planes: [{ kwp: '3.2', tilt: '', azimuth: '180' }, { kwp: '', tilt: null, azimuth: '' }],
    strings: [
      { name: ' Toit sud ', kwp: '3.2', tilt: '30', azimuth: '180', power: 'sensor.toit_sud', voltage: '', current: '', count_in_total: true },
      { name: '', kwp: '1' },
      { name: 'Garage', kwp: '', voltage: 'sensor.g_v', current: 'sensor.g_i', count_in_total: false },
    ],
  });
  assert.deepEqual(plain(payload), {
    planes: [{ kwp: 3.2, azimuth: 180 }],
    strings: [
      { name: 'Toit sud', kwp: 3.2, tilt: 30, azimuth: 180, power: 'sensor.toit_sud', count_in_total: true },
      { name: 'Garage', voltage: 'sensor.g_v', current: 'sensor.g_i', count_in_total: false },
    ],
  });
  // An empty list is sent so the backend can remove the key; absent groups are omitted.
  assert.deepEqual(plain(p._instPayload({ strings: [] })), { strings: [] });
});

test('a unit only detected by the profile is never written back as a declaration', () => {
  const p = panel('en');
  const detected = { name: 'Inverter 1', power: 'sensor.fsp_sn_current_active_power', count_in_total: true, declared: false };
  assert.deepEqual(plain(p._instPayload({ strings: [detected] })), { strings: [] });
  detected._edited = true;
  assert.deepEqual(plain(p._instPayload({ strings: [detected] })), {
    strings: [{ name: 'Inverter 1', power: 'sensor.fsp_sn_current_active_power', count_in_total: true }],
  });
});

test('an unset count_in_total stays unset and is shown as the coordinator counts it', () => {
  const p = panel('en');
  const unset = { name: 'MPPT 1', power: 'sensor.mppt_1', count_in_total: null, _edited: true };
  // Not written: the backend keeps the 1.9.0 behaviour (inside the meter, or in the units' sum without one).
  assert.deepEqual(plain(p._instPayload({ strings: [unset] })), { strings: [{ name: 'MPPT 1', power: 'sensor.mppt_1' }] });
  p._settings = { ...settings, pv_metered: true };
  assert.equal(p._countsInTotal(unset), false, 'not added on top of a pv_power meter');
  p._settings = { ...settings, pv_metered: false };
  assert.equal(p._countsInTotal(unset), true, 'the units are the total without a meter');
  assert.equal(p._countsInTotal({ count_in_total: false }), false);
  p._settings = { ...settings, pv_metered: true };
  assert.equal(p._countsInTotal({ count_in_total: true }), true);
});

test('the azimuth boxes take the 0-360° convention the backend validates', () => {
  const p = panel('en');
  p._sub = 'sources';
  p._settings = { ...settings, planes: [{ kwp: 3, tilt: 30, azimuth: 180 }], strings: [{ name: 'Est', azimuth: 90 }] };
  const html = p._settingsTab();
  assert.doesNotMatch(html, /min="-180"/);
  assert.ok(html.match(/min="0" max="360"/g).length >= 2);
});

test('saving "Panels & strings" sends energy_hub/set_installation', async () => {
  const p = panel('en');
  p._sub = 'sources';
  p._settingsTab();
  p._instRows('strings').length = 0; // the demo settings carry detected rows: start from a clean draft
  p._instRows('strings').push({ name: 'Toit sud', kwp: '3.2', tilt: '30', azimuth: '180', power: 'sensor.toit_sud', voltage: '', current: '', count_in_total: true });
  p._instRows('strings').push({ name: '  ', kwp: '9' });
  const calls = [];
  p._hass.callWS = async (msg) => {
    calls.push(msg);
  };
  p._resubscribe = async () => {};
  p._render = () => {};
  const btn = {
    disabled: false,
    textContent: '',
    title: '',
    addEventListener: (_type, fn) => {
      btn.fire = fn;
    },
  };
  p.shadowRoot = {
    activeElement: null,
    querySelector: () => null,
    querySelectorAll: (sel) => (sel === '[data-action="save-installation"]' ? [btn] : []),
  };
  p._bind();
  btn.fire({ currentTarget: btn });
  await new Promise((r) => setTimeout(r, 10));
  assert.equal(calls.length, 1);
  assert.equal(calls[0].type, 'energy_hub/set_installation');
  assert.deepEqual(plain(calls[0].strings), [{ name: 'Toit sud', kwp: 3.2, tilt: 30, azimuth: 180, power: 'sensor.toit_sud', count_in_total: true }]);
  assert.deepEqual(plain(calls[0].panels), []);
  assert.equal(calls[0].planes, undefined, 'the strings box does not resend the planes');
});

test('the settings hold editable orientation and panels/strings boxes', () => {
  const p = panel('en');
  p._sub = 'sources';
  p._settings = { ...settings, planes: [{ kwp: 3.2, tilt: 30, azimuth: 180 }], strings: [{ name: 'Toit sud', kwp: 3.2 }] };
  const html = p._settingsTab();
  assert.match(html, /data-action="save-planes"/);
  assert.match(html, /data-action="plane-add"/);
  assert.match(html, /data-action="save-installation"/);
  assert.match(html, /data-action="unit-add"/);
  assert.match(html, /data-pfield="kwp"[^>]*value="3.2"/);
  assert.match(html, /data-ufield="name"[^>]*value="Toit sud"/);
  assert.match(html, /data-ufield="count_in_total"/);
  assert.doesNotMatch(html, /energy_hub:\n/, 'the read-only YAML snippet is gone');
});

test('typed rows survive a re-render, a fresh settings payload replaces the draft', () => {
  const p = panel('en');
  p._sub = 'sources';
  p._settingsTab();
  p._instRows('strings').push({ name: 'Toit sud', kwp: '3.2', tilt: '30', azimuth: '180', power: 'sensor.x', voltage: '', current: '', count_in_total: false });
  for (let i = 0; i < 3; i += 1) {
    const html = p._settingsTab();
    assert.match(html, /data-ufield="name"[^>]*value="Toit sud"/);
    assert.match(html, /data-ufield="count_in_total"[^>]*data-ui="\d+"(?![^>]*checked)/);
  }
  // A brand new settings payload (after a reload) is the source of truth again
  p._settings = { ...settings, strings: [{ name: 'Neuf', kwp: 1 }] };
  const fresh = p._settingsTab();
  assert.match(fresh, /value="Neuf"/);
  assert.doesNotMatch(fresh, /value="Toit sud"/);
});

test('every entity input of the settings says its unit', () => {
  const p = panel('en');
  assert.equal(p._unitHint('grid_power'), 'values expressed in W');
  assert.equal(p._unitHint('pv_energy'), 'values expressed in kWh');
  assert.equal(p._unitHint('forecast_energy_today'), 'values expressed in kWh');
  assert.equal(p._unitHint('battery_home.soc'), 'values expressed in %');
  assert.equal(p._unitHint('tariff_price'), `values expressed in ${p._data.currency}/kWh`);
  assert.equal(p._unitHint('irradiance'), 'values expressed in W/m²');
  assert.equal(p._unitHint('weather'), '');
  assert.match(p._unitHint('tariff_color'), /colou?r/i);
  p._sub = 'sources';
  const html = p._settingsTab();
  const inputs = html.match(/<input[^>]*data-erole=/g) || [];
  const hints = html.match(/<i class="uhint">/g) || [];
  assert.ok(inputs.length > 8, `the demo form has ${inputs.length} entity inputs`);
  assert.ok(hints.length >= inputs.length - 1, `${hints.length} hints for ${inputs.length} inputs (the weather entity has no unit)`);
  const fr = panel('fr');
  assert.equal(fr._unitHint('grid_power'), 'valeurs exprimées en W');
});
