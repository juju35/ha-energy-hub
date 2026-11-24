// ── energy-hub-panel ─────────────────────────────────────────────────────────
import { EH_ICONS, EH_TABS, ENERGY_HUB_PANEL_VERSION } from "./core.js";
import { EH_I18N, EH_LANGS } from "./strings.js";
import { EH_AMBER, EH_BLUE, EH_GREEN, EH_RED, EH_TEAL, EH_VIOLET, ehEsc, ehIcon, ehTicks } from "./colours-helpers.js";
import { EH_CSS } from "./styles.js";

export class EnergyHubPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._data = null;
    this._settings = null;
    this._tab = new URLSearchParams(location.search).get('tab') || 'overview';
    this._battery = 'all';
    this._cellMetric = 'deviation';
    this._cell = null;
    this._rate = 3;
    this._period = 'today';
    this._sub = 'sources';
    this._node = null;
    this._snips = [];
    this._collapsed = false;
    this._error = null;
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    this._loadLang();
    if (first) this._connect();
  }

  get hass() {
    return this._hass;
  }

  set narrow(v) {
    this._narrow = v;
  }

  connectedCallback() {
    if (!this.shadowRoot.innerHTML) this._render();
  }

  disconnectedCallback() {
    this._unsub?.then((u) => u()).catch(() => {});
    this._unsub = null;
  }

  async _connect() {
    try {
      this._unsub = this._hass.connection.subscribeMessage(
        (data) => {
          this._data = data;
          this._render();
        },
        { type: 'energy_hub/subscribe' },
      );
      await this._unsub;
      this._settings = await this._hass.callWS({ type: 'energy_hub/settings' });
      this._render();
    } catch (err) {
      this._error = err?.message || String(err);
      this._render();
    }
  }

  // ---------- helpers
  get _lang() {
    const full = this._hass?.locale?.language || this._hass?.language || 'en';
    if (EH_LANGS.includes(full)) return full;
    const base = full.split('-')[0];
    return EH_LANGS.includes(base) ? base : 'en';
  }

  async _loadLang() {
    const lang = this._lang;
    if (lang === 'en' || EH_I18N[lang] || this._loading === lang) return;
    this._loading = lang;
    try {
      const res = await fetch(`/energy_hub_static/i18n/${lang}.json?v=${ENERGY_HUB_PANEL_VERSION}`);
      if (res.ok) {
        EH_I18N[lang] = await res.json();
        this._render();
      }
    } catch (_err) {
      // English stays
    }
    this._loading = null;
  }

  get _locale() {
    return this._hass?.locale?.language || this._hass?.language || 'en';
  }

  _t(path, params = {}, fallback = null) {
    const get = (dict) => path.split('.').reduce((o, k) => (o == null ? o : o[k]), dict);
    let s = get(EH_I18N[this._lang]) ?? get(EH_I18N.en) ?? fallback ?? path;
    if (typeof s !== 'string') return s;
    for (const [k, v] of Object.entries(params)) s = s.replaceAll(`{${k}}`, v);
    return s;
  }

  _num(v, d = 1) {
    if (v == null || Number.isNaN(v)) return '–';
    return new Intl.NumberFormat(this._hass?.locale?.language || 'en', { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
  }

  _kw(v) {
    return v == null ? '–' : `${this._num(Math.abs(v), Math.abs(v) < 10 ? 1 : 0)} kW`;
  }

  _kwh(v) {
    return v == null ? '–' : `${this._num(v, v < 10 ? 1 : 0)} kWh`;
  }

  _pct(v, d = 0) {
    return v == null ? '–' : `${this._num(v * 100, d)} %`;
  }

  _eur(v, d = 2) {
    if (v == null) return '–';
    return new Intl.NumberFormat(this._hass?.locale?.language || 'en', { style: 'currency', currency: this._data?.currency || 'EUR', minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
  }

  _hm(minute) {
    const h = Math.floor(minute / 60);
    const m = Math.round(minute % 60);
    return this._lang === 'fr' ? `${h} h ${String(m).padStart(2, '0')}` : `${h}:${String(m).padStart(2, '0')}`;
  }

  _time(ts) {
    const d = new Date(ts * 1000);
    return this._hm(d.getHours() * 60 + d.getMinutes());
  }

  get _dark() {
    return !!this._hass?.themes?.darkMode;
  }

  _setTab(tab) {
    this._tab = tab;
    const url = new URL(location.href);
    url.searchParams.set('tab', tab);
    history.replaceState(history.state, '', url);
    this._render();
    this.shadowRoot.querySelector('.scroll')?.scrollTo({ top: 0 });
  }

  // ---------- status
  _status() {
    const d = this._data;
    const night = !d.live.pv_kw || d.live.pv_kw < 0.02;
    const alerts = d.alerts.filter((a) => a.severity === 'error').length;
    const fleet = d.batteries.fleet;
    if (alerts) return { kind: 'alert', short: `! ${d.alerts.length}`, pill: this._t('alert_pill', { n: d.alerts.length }), bg: '#F7C1C1', fg: '#791F1F', icBg: '#F7C1C1', icFg: '#791F1F' };
    if (night && fleet?.soc != null) return { kind: 'night', short: this._pct(fleet.soc / 100), pill: this._t('battery_pill', { v: this._pct(fleet.soc / 100) }), bg: '#9FE1CB', fg: '#085041', icBg: '#9FE1CB', icFg: '#085041' };
    if (night) return { kind: 'night', short: '☾', pill: this._t('night'), bg: '#D3D1C7', fg: '#444441', icBg: '#D3D1C7', icFg: '#444441' };
    return { kind: 'day', short: this._kw(d.live.pv_kw), pill: this._t('producing', { v: this._kw(d.live.pv_kw) }), bg: '#C0DD97', fg: '#27500A', icBg: '#FAC775', icFg: '#633806' };
  }

  // ---------- banner
  _scene(st) {
    const d = this._data;
    const night = this._dark;
    const { sky, ground, cloudy } = this._sky();
    const now = new Date(d.generated);
    const minutes = now.getHours() * 60 + now.getMinutes();
    const frac = Math.min(Math.max((minutes - 360) / (22 * 60 - 360), 0), 1);
    const sx = 330 + frac * 350;
    const sy = 92 - Math.sin(frac * Math.PI) * 74;
    const fleet = d.batteries.fleet;
    const soc = fleet?.soc ?? 0;
    const pv = d.live.pv_kw || 0;
    const grid = d.live.grid_kw || 0;
    const batt = d.live.battery_kw || 0;
    const pylon = night ? '#6E7896' : '#8D8A80';
    const dots = (path, color, n, dur, r) => {
      let o = '';
      for (let i = 0; i < n; i++) o += `<circle r="${r}" fill="${color}"><animateMotion dur="${dur}s" begin="-${((i * dur) / n).toFixed(2)}s" repeatCount="indefinite" path="${path}"/></circle>`;
      return o;
    };
    let o = `<svg class="scene" viewBox="0 0 680 90" preserveAspectRatio="xMaxYMax meet" aria-hidden="true"><rect width="680" height="90" fill="${sky}"/>`;
    if (night) {
      for (let i = 0; i < 20; i++) o += `<circle cx="${360 + ((i * 97) % 310)}" cy="${6 + ((i * 53) % 40)}" r="${i % 3 ? 0.8 : 1.2}" fill="#F1EFE8" opacity=".7"><animate attributeName="opacity" values=".2;.9;.2" dur="${2 + (i % 3)}s" repeatCount="indefinite"/></circle>`;
      o += `<circle cx="585" cy="22" r="10" fill="#F1EFE8"/><circle cx="590" cy="19" r="9" fill="${sky}"/>`;
    } else {
      o += `<path d="M330 92 Q505 -40 680 92" fill="none" stroke="#E2C489" stroke-dasharray="2 4"/>`;
      if (pv > 0.02) o += `<g transform="translate(${sx.toFixed(0)} ${sy.toFixed(0)})"><circle r="22" fill="#F5B84A" fill-opacity=".18"/><circle r="11" fill="#F5B84A"/></g>`;
      if (cloudy) for (let c = 0; c < 3; c++) o += `<g fill="#fff" fill-opacity=".92"><animateTransform attributeName="transform" type="translate" values="0 0;14 0;0 0" dur="${9 + c * 3}s" repeatCount="indefinite"/><ellipse cx="${430 + c * 70}" cy="${20 + (c % 2) * 10}" rx="26" ry="8"/><ellipse cx="${442 + c * 70}" cy="${14 + (c % 2) * 10}" rx="15" ry="9"/></g>`;
    }
    o += `<path d="M300 84 C380 66 430 70 470 76 C520 62 600 66 680 74 L680 84 Z" fill="${night ? '#26324F' : cloudy ? '#D3D9D2' : '#EDD9AE'}"/>`;
    o += `<polygon points="456,52 516,26 576,52" fill="${night ? '#5A3328' : '#B4553A'}"/><polygon points="474,46 510,30 528,38 492,54" fill="${night ? '#1B2A45' : '#2F4A70'}"/>`;
    o += `<g stroke="${night ? '#33456A' : '#FBEFD6'}" stroke-width="1.1"><line x1="486" y1="40" x2="504" y2="48"/><line x1="498" y1="35" x2="516" y2="43"/><line x1="483" y1="50" x2="519" y2="34"/></g>`;
    if (pv > 0.3 && !night) o += `<clipPath id="ehcp"><polygon points="474,46 510,30 528,38 492,54"/></clipPath><g clip-path="url(#ehcp)"><rect x="440" y="20" width="8" height="50" fill="#fff" fill-opacity=".55" transform="rotate(25 480 40)"><animate attributeName="x" values="440;560" dur="3.2s" repeatCount="indefinite"/></rect></g>`;
    if (st.kind === 'alert') o += `<circle cx="530" cy="30" r="7" fill="${EH_RED}"/><text x="530" y="33.5" text-anchor="middle" font-size="10" font-weight="500" fill="#fff">!</text>`;
    const win = night ? '#F5C451' : '#F7D98F';
    o += `<rect x="464" y="52" width="104" height="32" fill="${night ? '#3A4560' : '#EFE5CF'}"/><rect x="506" y="62" width="16" height="22" fill="${night ? '#2A3350' : '#A88F64'}"/><rect x="476" y="60" width="18" height="12" rx="1" fill="${win}"/><rect x="536" y="60" width="18" height="12" rx="1" fill="${win}"/>`;
    if (fleet) {
      const bh = Math.round((16 * soc) / 100);
      o += `<rect x="575" y="58" width="16" height="24" rx="3" fill="#5F5E5A"/><rect x="579" y="${80 - bh}" width="8" height="${bh}" rx="1" fill="${EH_TEAL}"/><rect x="580" y="55" width="6" height="3" rx="1" fill="#5F5E5A"/>`;
      if (Math.abs(batt) > 0.05) o += `<rect x="579" y="61" width="8" height="2" rx="1" fill="${EH_TEAL}"><animate attributeName="opacity" values="1;.2;1" dur="1.4s" repeatCount="indefinite"/></rect>`;
    }
    o += `<g stroke="${pylon}" stroke-width="1.5" fill="none" stroke-linejoin="round"><path d="M632 84 L642 34 L652 84"/><line x1="635" y1="68" x2="649" y2="68"/><line x1="638" y1="52" x2="646" y2="52"/><line x1="628" y1="40" x2="656" y2="40"/></g>`;
    const wire = 'M568 64 Q600 46 628 40';
    o += `<path d="${wire}" fill="none" stroke="${pylon}" stroke-width=".9"/>`;
    if (grid < -0.05) o += dots(wire, EH_BLUE, 3, 1.8, 2.2);
    if (grid > 0.05) o += dots('M628 40 Q600 46 568 64', '#888780', 3, 2, 2.2);
    if (pv > 0.05 && batt > 0.05) o += dots('M520 46 L583 58', '#EF9F27', 2, 1.4, 1.8);
    if (batt < -0.05) o += dots('M583 70 L568 70', '#5DCAA5', 2, 1.2, 1.8);
    o += `<rect x="0" y="84" width="680" height="6" fill="${ground}"/></svg>`;
    return o;
  }

  _sky() {
    const L = this._data.live;
    if (this._dark) return { sky: '#1C2740', ground: '#2E3A55', cloudy: false };
    const cloudy = L.expected_kw != null && L.pv_kw != null && L.expected_kw > 0.3 && L.pv_kw / L.expected_kw < 0.5;
    return cloudy ? { sky: '#E8ECEF', ground: '#B8B6A8', cloudy } : { sky: '#FBEFD6', ground: '#C9B28A', cloudy };
  }

  _header() {
    const d = this._data;
    const st = this._status();
    const fleet = d.batteries.fleet;
    const night = !d.live.pv_kw || d.live.pv_kw < 0.02;
    const sub = night
      ? this._t('subline_night', { load: this._kw(d.live.load_kw), aut: d.batteries.autonomy_h != null ? `${this._num(d.batteries.autonomy_h, 0)} h` : '–' })
      : this._t('subline_day', { sc: this._pct(d.today.self_consumption), soc: fleet?.soc != null ? this._pct(fleet.soc / 100) : '–' });
    const textColor = this._dark ? '#F1EFE8' : '#412402';
    const subColor = this._dark ? '#B4B2A9' : '#854F0B';
    const tabs = EH_TABS.map(([key, icon]) => {
      const dot = key === 'losses' && d.alerts.length && this._tab !== 'losses' ? '<span class="dot"></span>' : '';
      return `<button class="tabpill ${this._tab === key ? 'on' : ''}" data-tab="${key}" title="${ehEsc(this._t(`tabs.${key}`))}" aria-label="${ehEsc(this._t(`tabs.${key}`))}">${ehIcon(icon, 17)}${dot}</button>`;
    }).join('');
    return `
      <header class="banner ${this._collapsed ? 'collapsed' : ''}" style="--txt:${textColor};--sub:${subColor};--sky:${this._sky().sky};--ground:${this._sky().ground};--btn:${this._dark ? 'rgba(255,255,255,.14)' : 'rgba(255,255,255,.6)'}">
        ${this._scene(st)}
        <div class="bar">
          <button class="round menu" data-action="menu" aria-label="Menu">${ehIcon('menu', 20)}</button>
          <div class="badge" style="background:${st.icBg};color:${st.icFg}">${ehIcon('solar-power-variant', 22)}</div>
          <div class="titles">
            <div class="title"><span class="tname">${ehEsc(this._t('title'))}</span><span class="pill" style="background:${st.bg};color:${st.fg}"><span class="long">${ehEsc(st.pill)}</span><span class="short">${ehEsc(st.short)}</span></span>${d.demo ? `<span class="pill demo">${ehEsc(this._t('demo'))}</span>` : ''}</div>
            <div class="sub">${ehEsc(sub)} · ${ehEsc(this._t('kwp', { v: this._num(d.kwp, 1) }))}</div>
          </div>
          <div class="tabpills">${tabs}</div>
          <button class="round bell" data-tab="losses" aria-label="${ehEsc(this._t('alerts_label'))}">${ehIcon('bell-outline', 18)}${d.alerts.length ? `<span class="count">${d.alerts.length}</span>` : ''}</button>
          <button class="round refresh" data-action="refresh" aria-label="Refresh">${ehIcon('refresh', 18)}</button>
        </div>
      </header>
      <nav class="tabs">${EH_TABS.map(([key]) => `<button class="tab ${this._tab === key ? 'on' : ''}" data-tab="${key}">${ehEsc(this._t(`tabs.${key}`))}${key === 'losses' && d.alerts.length ? '<span class="dot inline"></span>' : ''}</button>`).join('')}</nav>`;
  }

  // ---------- shared bits
  _tile(icon, bg, fg, label, value, sub, subColor) {
    return `<div class="tile"><div class="pa" style="background:${bg};color:${fg}">${ehIcon(icon, 18)}</div><div class="tt"><div class="t1">${ehEsc(label)}</div><div class="t2">${value}</div><div class="t3" style="color:${subColor || 'var(--secondary-text-color)'}">${sub}</div></div></div>`;
  }

  _box(title, hint, body) {
    return `<section class="box"><div class="hd"><h3>${ehEsc(title)}</h3>${hint ? `<span class="hint">${ehEsc(hint)}</span>` : ''}</div>${body}</section>`;
  }

  _alertTiles() {
    const d = this._data;
    if (!d.alerts.length) return '';
    const tiles = d.alerts.map((a) => {
      const tpl = this._t(`alerts.${a.kind}`);
      if (!Array.isArray(tpl)) return '';
      const p = {
        kwh: this._kwh(a.kwh),
        days: a.days ?? a.days_week ?? '',
        name: a.name ?? '',
        pct: a.relative != null ? `−${this._num((1 - a.relative) * 100, 0)} %` : '',
        unit: a.unit ?? '',
        from: a.periods?.length ? this._time(a.periods[0][0]) : a.start != null ? this._hm(a.start) : '',
        to: a.periods?.length ? this._time(a.periods[a.periods.length - 1][1]) : a.end != null ? this._hm(a.end) : '',
        battery: a.battery ?? '',
        cell: a.cell ?? '',
        kw: this._kw(a.kw),
        entities: (a.entities || []).join(', '),
      };
      if (a.kind === 'soiling') p.pct = this._pct(a.loss, 1);
      const color = a.severity === 'error' ? ['#FCEBEB', '#A32D2D'] : a.severity === 'info' ? ['#E6F1FB', '#185FA5'] : ['#FAEEDA', '#854F0B'];
      const icon = { clipping: 'alert-outline', string_lagging: 'solar-panel', shading: 'weather-cloudy-alert', soiling: 'water-off', cell_drift: 'scale-balance', battery_exchange: 'arrow-left-right', stale: 'power-plug-off-outline' }[a.kind];
      const fill = (s) => Object.entries(p).reduce((acc, [k, v]) => acc.replaceAll(`{${k}}`, v), s);
      return `<button class="alert" data-tab="losses"><div class="pa" style="background:${color[0]};color:${color[1]}">${ehIcon(icon, 18)}</div><div class="tt"><div class="a1">${ehEsc(fill(tpl[0]))}</div><div class="a2" style="color:${color[1]}">${ehEsc(fill(tpl[1]))}</div></div>${ehIcon('chevron-right', 18)}</button>`;
    });
    return `<div class="grid-auto">${tiles.join('')}</div>`;
  }

  // ---------- Overview
  _flow() {
    const d = this._data;
    const L = d.live;
    const fleet = d.batteries.fleet;
    const items = d.batteries.items;
    const pv = L.pv_kw || 0;
    const load = L.load_kw || 0;
    const grid = L.grid_kw || 0;
    const batt = L.battery_kw || 0;
    const w = (kw) => Math.max(2, Math.min(8, 2 + Math.abs(kw) * 1.4));
    const speed = (kw) => Math.max(1.2, 3 - Math.abs(kw) * 0.4).toFixed(2);
    const flowPath = (path, kw, color, reverse) => {
      if (Math.abs(kw) < 0.02) return `<path d="${path}" fill="none" stroke="var(--divider-color)" stroke-width="6" stroke-linecap="round"/>`;
      let dots = '';
      const n = Math.min(5, 2 + Math.round(Math.abs(kw)));
      const dur = speed(kw);
      for (let i = 0; i < n; i++) dots += `<circle r="${(w(kw) / 2).toFixed(1)}" fill="${color}"><animateMotion dur="${dur}s" begin="-${((i * dur) / n).toFixed(2)}s" repeatCount="indefinite" path="${path}" keyPoints="${reverse ? '1;0' : '0;1'}" keyTimes="0;1" calcMode="linear"/></circle>`;
      return `<path d="${path}" fill="none" stroke="var(--divider-color)" stroke-width="${w(kw) + 3}" stroke-linecap="round"/>${dots}`;
    };
    const pvHome = Math.min(pv, load);
    const node = (x, y, icon, bg, fg, label, value, sub, extra = '') =>
      `<foreignObject x="${x}" y="${y}" width="180" height="62"><div xmlns="http://www.w3.org/1999/xhtml" class="node"><div class="pa" style="background:${bg};color:${fg}">${ehIcon(icon, 18)}</div><div class="tt"><div class="t1">${label}</div><div class="t2">${value}</div>${sub ? `<div class="t3" style="color:${fg}">${sub}</div>` : ''}${extra}</div></div></foreignObject>`;
    const label = (x, y, kw) => (Math.abs(kw) < 0.02 ? '' : `<g><rect x="${x - 30}" y="${y - 11}" width="60" height="20" rx="10" fill="var(--card-background-color)" stroke="var(--divider-color)"/><text x="${x}" y="${y + 3}" text-anchor="middle" class="svgt">${this._kw(kw)}</text></g>`);
    const battName = items.length > 1 ? this._t('batteries_n', { n: items.length }) : this._t('battery');
    const battState = batt > 0.05 ? this._t('charging') : batt < -0.05 ? this._t('discharging') : fleet?.soc >= 99 ? this._t('full') : this._t('idle');
    const full = items.length === 1 && items[0].hours_to_full != null ? this._t('full_at', { v: this._time(Date.now() / 1000 + items[0].hours_to_full * 3600) }) : '';
    const socBar = fleet?.soc != null ? `<div class="soc"><div style="width:${fleet.soc}%"></div></div>` : '';
    let o = '<svg class="flow" viewBox="0 0 680 228" role="img" aria-label="Energy flow">';
    o += flowPath('M340 72 L340 156', pvHome, EH_GREEN);
    if (fleet) o += flowPath('M285 46 C185 46 120 84 120 156', batt, EH_TEAL, batt < 0);
    o += flowPath('M395 46 C495 46 560 84 560 156', grid, grid < 0 ? EH_BLUE : '#888780', grid > 0);
    o += label(378, 112, pvHome) + (fleet ? label(178, 74, batt) : '') + label(502, 74, grid);
    o += node(250, 12, 'white-balance-sunny', '#FAEEDA', '#854F0B', this._t('solar'), this._kw(pv), L.peak_share != null ? this._t('of_peak', { v: this._pct(L.peak_share) }) : '');
    if (fleet) o += node(30, 156, 'battery-charging', '#E1F5EE', '#0F6E56', `${battName} · ${battState}`, this._pct(fleet.soc / 100), full, socBar);
    o += node(250, 156, 'home-lightning-bolt-outline', '#EAF3DE', '#3B6D11', this._t('home'), this._kw(load), load > 0 ? this._t('solar_share', { v: this._pct(Math.min(pvHome / load, 1)) }) : '');
    o += node(470, 156, 'transmission-tower', '#E6F1FB', '#185FA5', `${this._t('grid')} · ${grid < -0.02 ? this._t('exporting') : grid > 0.02 ? this._t('importing') : this._t('idle')}`, this._kw(grid), '');
    return `${o}</svg>`;
  }

  _kpis() {
    const d = this._data;
    const T = d.today;
    const Y = d.yesterday;
    const trend = (a, b) => {
      if (a == null || b == null) return '';
      const pts = Math.round((a - b) * 100);
      return `<span style="color:${pts >= 0 ? 'var(--success-color,#43a047)' : 'var(--error-color,#db4437)'}">${pts >= 0 ? '▲' : '▼'} ${this._t('vs_yesterday', { v: `${Math.abs(pts)} ${this._t('pts')}` })}</span>`;
    };
    const losses = Object.entries(d.losses.today).filter(([k]) => !['potential', 'produced'].includes(k)).reduce((a, [, v]) => a + (v || 0), 0);
    const kp = (label, value, sub, color) => `<div class="kpi"><div class="k1">${ehEsc(label)}</div><div class="k2" ${color ? `style="color:${color}"` : ''}>${value}</div><div class="k3">${sub}</div></div>`;
    return `<div class="kpis">
      ${kp(this._t('self_consumption'), this._pct(T.self_consumption), trend(T.self_consumption, Y.self_consumption))}
      ${kp(this._t('self_sufficiency'), this._pct(T.self_sufficiency), trend(T.self_sufficiency, Y.self_sufficiency))}
      ${kp(this._t('saved'), this._eur(T.savings), ehEsc(this._t('resale', { v: this._eur(T.export_savings) })))}
      ${kp(this._t('losses'), this._kwh(losses), ehEsc(this._t('of_day', { v: this._eur(losses * (d.finances.import_price || 0)), p: d.losses.today.potential ? this._pct(losses / d.losses.today.potential) : '–' })), losses > 0.3 ? 'var(--error-color,#db4437)' : '')}
    </div>`;
  }

  _curve() {
    const d = this._data;
    const period = this._period;
    const seg = `<div class="seg">${['today', '7d', '30d', '12m'].map((p) => `<button class="${period === p ? 'on' : ''}" data-period="${p}">${ehEsc(this._t(`periods.${p}`))}</button>`).join('')}</div>`;
    const chip = (c, label, dash) => `<span class="chip"><span style="width:14px;border-top:2px ${dash ? 'dashed' : 'solid'} ${c}"></span>${ehEsc(label)}</span>`;
    const hatchChip = `<span class="chip"><svg width="14" height="10" aria-hidden="true"><rect width="14" height="10" fill="url(#ehhatch)" stroke="${EH_RED}" stroke-width=".6"/></svg>${ehEsc(this._t('clipping'))}</span>`;
    const hatchDef = `<defs><pattern id="ehhatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="5" height="5" fill="${EH_RED}" fill-opacity=".08"/><line x1="0" y1="0" x2="0" y2="5" stroke="${EH_RED}" stroke-width="1.6" stroke-opacity=".7"/></pattern></defs>`;
    if (period !== 'today') {
      const rows = d.periods?.[period] || [];
      const W = 680;
      const x0 = 50;
      const x1 = 640;
      const max = Math.max(1, ...rows.map((r) => Math.max((r.pv || 0) + (r.clipped || 0), r.exp || 0, r.load || 0))) * 1.1;
      const Y = (v) => 190 - (v / max) * 160;
      const step = (x1 - x0) / Math.max(rows.length, 1);
      const bw = Math.max(Math.min(step * 0.62, 30), 3);
      let o = `<svg class="curve" viewBox="0 0 ${W} 214" role="img" aria-label="${ehEsc(this._t(`periods.${period}`))}">${hatchDef}`;
      for (const v of ehTicks(max)) {
        o += `<line x1="${x0}" x2="${x1}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--divider-color)" stroke-width=".5"/><text class="svgt" x="${x0 - 8}" y="${Y(v) + 4}" text-anchor="end">${this._num(v, v % 1 ? 1 : 0)}</text>`;
      }
      o += '<text class="svgt" x="16" y="18">kWh</text>';
      const loadPts = [];
      rows.forEach((r, i) => {
        const cx = x0 + step * (i + 0.5);
        const pvTop = Y(r.pv || 0);
        const label = period === '12m' ? new Date(`${r.d}-01T12:00`).toLocaleString(this._locale, { month: 'short' }) : new Date(`${r.d}T12:00`).toLocaleString(this._locale, period === '7d' ? { weekday: 'short' } : { day: 'numeric' });
        o += `<g><title>${ehEsc(label)} · ${ehEsc(this._t('production'))} ${this._kwh(r.pv)} · ${ehEsc(this._t('forecast'))} ${this._kwh(r.exp)} · ${ehEsc(this._t('consumption'))} ${this._kwh(r.load)}${r.clipped ? ` · ${ehEsc(this._t('clipped', { v: this._kwh(r.clipped) }))}` : ''}</title>`;
        o += `<rect x="${(cx - bw / 2).toFixed(1)}" y="${pvTop.toFixed(1)}" width="${bw.toFixed(1)}" height="${(190 - pvTop).toFixed(1)}" rx="2" fill="#FAC775" stroke="${EH_AMBER}" stroke-width=".6"/>`;
        if (r.clipped > 0.01) o += `<rect x="${(cx - bw / 2).toFixed(1)}" y="${Y((r.pv || 0) + r.clipped).toFixed(1)}" width="${bw.toFixed(1)}" height="${(pvTop - Y((r.pv || 0) + r.clipped)).toFixed(1)}" fill="url(#ehhatch)" stroke="${EH_RED}" stroke-width=".6"/>`;
        if (r.exp) o += `<line x1="${(cx - bw / 2 - 2).toFixed(1)}" x2="${(cx + bw / 2 + 2).toFixed(1)}" y1="${Y(r.exp).toFixed(1)}" y2="${Y(r.exp).toFixed(1)}" stroke="var(--secondary-text-color)" stroke-width="1.4" stroke-dasharray="3 2"/>`;
        o += '</g>';
        if (r.load != null) loadPts.push(`${cx.toFixed(1)} ${Y(r.load).toFixed(1)}`);
        const every = period === '30d' ? 5 : 1;
        if (i % every === 0 || i === rows.length - 1) o += `<text class="svgt" x="${cx.toFixed(1)}" y="208" text-anchor="middle">${ehEsc(label)}</text>`;
      });
      if (loadPts.length > 1) o += `<path d="M${loadPts.join(' L')}" fill="none" stroke="${EH_VIOLET}" stroke-width="1.8"/>${loadPts.map((p) => `<circle cx="${p.split(' ')[0]}" cy="${p.split(' ')[1]}" r="2.2" fill="${EH_VIOLET}"/>`).join('')}`;
      o += '</svg>';
      const total = rows.reduce((a, r) => a + (r.pv || 0), 0);
      const totalExp = rows.reduce((a, r) => a + (r.exp || 0), 0);
      const legend = `${chip(EH_AMBER, this._t('production'))}${chip('var(--secondary-text-color)', this._t('forecast'), true)}${chip(EH_VIOLET, this._t('consumption'))}${rows.some((r) => r.clipped > 0.01) ? hatchChip : ''}`;
      this._curveMeta = null;
      return this._box(this._t('production'), '', `<div class="hd sub">${seg}<span class="hint">${ehEsc(this._t('produced_of', { a: this._kwh(total), b: this._kwh(totalExp) }))}</span></div><div class="legend">${legend}</div>${o}`);
    }
    const rows = d.curve;
    if (!rows.length) return '';
    const W = 680;
    const H = 214;
    const x0 = 50;
    const x1 = 630;
    const start = new Date(d.generated);
    start.setHours(5, 0, 0, 0);
    const t0 = start.getTime() / 1000;
    const t1 = t0 + 17 * 3600;
    const max = Math.max(1, ...rows.map((r) => Math.max(r.pv || 0, r.exp || 0, r.load || 0)), d.inverter_max_kw || 0) * 1.1;
    const X = (t) => x0 + ((t - t0) / (t1 - t0)) * (x1 - x0);
    const Y = (v) => 190 - (Math.min(v, max) / max) * 160;
    const YS = (s) => 190 - (s / 100) * 160;
    const inRange = rows.filter((r) => r.t >= t0 && r.t <= t1);
    const line = (key, f = Y) => inRange.filter((r) => r[key] != null).map((r, i) => `${i ? 'L' : 'M'}${X(r.t).toFixed(1)} ${f(r[key]).toFixed(1)}`).join(' ');
    let o = `<svg class="curve" viewBox="0 0 ${W} ${H}" role="img" aria-label="${ehEsc(this._t('periods.today'))}">${hatchDef}`;
    for (const v of ehTicks(max)) {
      o += `<line x1="${x0}" x2="${x1}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--divider-color)" stroke-width=".5"/><text class="svgt" x="${x0 - 8}" y="${Y(v) + 4}" text-anchor="end">${this._num(v, v % 1 ? 1 : 0)}</text>`;
    }
    o += `<text class="svgt" x="16" y="18">kW</text><text class="svgt" x="${x1 + 6}" y="34">100</text><text class="svgt" x="${x1 + 6}" y="194">0 %</text>`;
    const pv = line('pv');
    if (pv && inRange.length) o += `<path d="${pv} L${X(inRange[inRange.length - 1].t).toFixed(1)} 190 L${X(inRange[0].t).toFixed(1)} 190 Z" fill="#FAC775" fill-opacity=".5"/>`;
    // Clipping: the energy between the forecast and the plateau, hatched
    const clipped = d.losses.clipping_periods || [];
    for (const [a, b] of clipped) {
      const seg2 = inRange.filter((r) => r.t >= a && r.t <= b && r.exp != null && r.pv != null);
      if (seg2.length < 2) continue;
      const top = seg2.map((r) => `${X(r.t).toFixed(1)} ${Y(Math.max(r.exp, r.pv)).toFixed(1)}`);
      const bottom = seg2.map((r) => `${X(r.t).toFixed(1)} ${Y(r.pv).toFixed(1)}`).reverse();
      o += `<path d="M${top.join(' L')} L${bottom.join(' L')} Z" fill="url(#ehhatch)" stroke="${EH_RED}" stroke-width=".8"/>`;
    }
    if (pv) o += `<path d="${pv}" fill="none" stroke="${EH_AMBER}" stroke-width="2"/>`;
    const exp = line('exp');
    if (exp) o += `<path d="${exp}" fill="none" stroke="var(--secondary-text-color)" stroke-width="1.3" stroke-dasharray="4 4"/>`;
    const load = line('load');
    if (load) o += `<path d="${load}" fill="none" stroke="${EH_VIOLET}" stroke-width="1.8"/>`;
    const soc = line('soc', YS);
    if (soc) o += `<path d="${soc}" fill="none" stroke="${EH_TEAL}" stroke-width="1.5"/>`;
    if (d.inverter_max_kw) o += `<line x1="${x0}" x2="${x1}" y1="${Y(d.inverter_max_kw)}" y2="${Y(d.inverter_max_kw)}" stroke="${EH_RED}" stroke-dasharray="2 3"/><text class="svgt" x="${x1 - 4}" y="${Y(d.inverter_max_kw) - 6}" text-anchor="end" style="fill:${EH_RED}">${ehEsc(this._t('inverter_max', { v: this._kw(d.inverter_max_kw) }))}</text>`;
    const last = inRange[inRange.length - 1];
    if (last) o += `<line x1="${X(last.t)}" x2="${X(last.t)}" y1="30" y2="190" stroke="var(--secondary-text-color)" stroke-width=".5" stroke-dasharray="3 3"/><circle cx="${X(last.t)}" cy="${Y(last.pv || 0)}" r="4.5" fill="${EH_AMBER}" stroke="var(--card-background-color)" stroke-width="2"/>`;
    for (let h = 6; h <= 21; h += 3) {
      const t = t0 + (h - 5) * 3600;
      o += `<text class="svgt" x="${X(t)}" y="208" text-anchor="middle">${this._lang === 'fr' ? `${h} h` : `${h}:00`}</text>`;
    }
    o += `<line class="hov" x1="0" x2="0" y1="30" y2="190" stroke="var(--secondary-text-color)" stroke-width=".5" style="display:none"/><rect class="hit" x="${x0}" y="30" width="${x1 - x0}" height="160" fill="transparent"/></svg>`;
    const legend = `${chip(EH_AMBER, this._t('production'))}${chip('var(--secondary-text-color)', this._t('forecast'), true)}${chip(EH_VIOLET, this._t('consumption'))}${chip(EH_TEAL, this._t('battery_pct'))}${chip(EH_RED, 'Pmax', true)}${clipped.length ? hatchChip : ''}`;
    this._curveMeta = { t0, t1, x0, x1, max, rows: inRange };
    return this._box(this._t('production'), '', `<div class="hd sub">${seg}<span class="hint">${ehEsc(this._t('produced_of', { a: this._kwh(d.today.pv_kwh), b: this._kwh(d.today.expected_kwh) }))}</span></div><div class="legend">${legend}</div><div class="curvewrap">${o}<div class="tip"></div></div><div class="hint">${ehEsc(this._t('hover_hint'))}</div>`);
  }

  _overview() {
    return `${this._flow()}${this._kpis()}${this._curve()}${this._alertTiles()}`;
  }

  // ---------- Production
  _production() {
    const d = this._data;
    const P = d.production;
    const T = d.today;
    const prRange = `${this._num(0.8, 2)} – ${this._num(0.95, 2)}`;
    let o = `<div class="grid4">
      ${this._tile('gauge', '#FAEEDA', '#854F0B', this._t('yield'), T.specific_yield != null ? `${this._num(T.specific_yield, 2)} kWh/kWp` : '–', d.kwp_estimated ? this._t('estimated') : this._t('kwp', { v: this._num(d.kwp, 1) }))}
      ${this._tile('target', '#EAF3DE', '#3B6D11', this._t('pr'), this._pct(T.epi), this._t('pr_range', { v: prRange }), EH_GREEN)}
      ${this._tile('chart-line', '#FCEBEB', '#A32D2D', this._t('peak_day'), this._kw(T.peak_kw), d.inverter_max_kw && T.peak_kw >= 0.97 * d.inverter_max_kw ? this._t('reached_limit') : T.peak_at ? this._time(new Date(T.peak_at).getTime() / 1000) : '', d.inverter_max_kw && T.peak_kw >= 0.97 * d.inverter_max_kw ? EH_RED : '')}
      ${this._tile('calendar-month', '#FAEEDA', '#854F0B', this._t('this_month'), this._kwh(P.month_kwh), P.month_expected ? this._t('of_expected', { v: this._pct(P.month_kwh / P.month_expected) }) : '')}
    </div>`;
    if (P.units.length) {
      const per = Math.ceil(P.units.length / 2);
      let svg = '<svg viewBox="0 0 640 200" class="roof" role="img" aria-label="Roof">';
      svg += '<polygon points="60,180 580,180 520,20 120,20" fill="#B4553A" fill-opacity=".18" stroke="#B4553A" stroke-opacity=".4"/>';
      const rowsN = P.units.length > per ? 2 : 1;
      P.units.forEach((u, i) => {
        const row = Math.floor(i / per);
        const c = i % per;
        const y0 = 30 + row * (152 / rowsN);
        const y1 = y0 + 152 / rowsN - 10;
        const tf = (y) => (y - 20) / 160;
        const L0 = 120 - 60 * tf(y0);
        const R0 = 520 + 60 * tf(y0);
        const L1 = 120 - 60 * tf(y1);
        const R1 = 520 + 60 * tf(y1);
        const w0 = (R0 - L0) / per;
        const w1 = (R1 - L1) / per;
        const g = 3;
        const pct = u.pct ?? 0;
        const col = pct < 70 ? EH_RED : pct < 92 ? '#EF9F27' : EH_AMBER;
        const pts = [[L0 + c * w0 + g, y0], [L0 + (c + 1) * w0 - g, y0], [L1 + (c + 1) * w1 - g, y1], [L1 + c * w1 + g, y1]];
        const cx = pts.reduce((a, p) => a + p[0], 0) / 4;
        const cy = (y0 + y1) / 2;
        svg += `<polygon points="${pts.map((p) => p.join(',')).join(' ')}" fill="${col}" fill-opacity="${(0.3 + (0.7 * pct) / 100).toFixed(2)}" stroke="#2F4A70" stroke-opacity=".5"><title>${ehEsc(u.name)} · ${pct} % · ${this._kwh(u.kwh)}</title></polygon><text class="svgt dark" x="${cx}" y="${cy - 3}" text-anchor="middle">${ehEsc(u.name)}</text><text class="svgth dark" x="${cx}" y="${cy + 13}" text-anchor="middle">${u.pct ?? '–'}</text>`;
      });
      svg += '</svg>';
      const legend = `<span class="chip"><span class="sw" style="background:${EH_AMBER}"></span>≥ 92 %</span><span class="chip"><span class="sw" style="background:#EF9F27"></span>70 – 92 %</span><span class="chip"><span class="sw" style="background:${EH_RED}"></span>&lt; 70 %</span>`;
      o += this._box(this._t('roof'), this._t('roof_hint'), `${svg}<div class="legend">${legend}</div>`);
    }
    if (P.strings.length) {
      const best = Math.max(...P.strings.map((s) => s.kwh || 0), 0.001);
      const rows = P.strings
        .map((s) => {
          const lag = s.lagging_days >= 3;
          return `<div class="barrow"><span>${ehEsc(s.name)}</span><div class="meter"><div style="width:${((s.kwh || 0) / best) * 100}%;background:${lag ? '#EF9F27' : EH_AMBER}"></div></div><span style="color:${lag ? EH_AMBER : 'var(--secondary-text-color)'}">${this._kwh(s.kwh)}${s.relative != null ? ` · ${s.relative >= 1 ? '+' : '−'}${this._num(Math.abs(s.relative - 1) * 100, 0)} %` : ''}</span></div>`;
        })
        .join('');
      o += this._box(this._t('strings'), '', rows);
    }
    const epi = P.epi_30d;
    let prSvg = '<svg class="mini" viewBox="0 0 300 120" role="img" aria-label="PR">';
    if (epi.length > 1) {
      const vals = epi.map((e) => e.epi);
      const lo = Math.min(...vals, 0.6);
      const hi = Math.max(...vals, 1);
      const X = (i) => 10 + (i / (epi.length - 1)) * 280;
      const Y = (v) => 100 - ((v - lo) / (hi - lo)) * 84;
      prSvg += `<path d="${epi.map((e, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)} ${Y(e.epi).toFixed(1)}`).join(' ')}" fill="none" stroke="${EH_AMBER}" stroke-width="2" stroke-linejoin="round"/>`;
      epi.forEach((e, i) => {
        if (e.rain) prSvg += `<line x1="${X(i)}" x2="${X(i)}" y1="16" y2="100" stroke="${EH_BLUE}" stroke-width=".6" stroke-dasharray="2 2"/><path d="M${X(i)} 6 C${X(i) - 4} 12 ${X(i) - 4} 16 ${X(i)} 16 C${X(i) + 4} 16 ${X(i) + 4} 12 ${X(i)} 6 Z" fill="${EH_BLUE}"/>`;
      });
    }
    prSvg += '<line x1="10" x2="290" y1="100" y2="100" stroke="var(--divider-color)"/></svg>';
    const soil = d.trends.soiling;
    const soilText = soil.learning ? this._t('learning', { d: soil.days, n: soil.needed }) : `${this._t('soiling_trend')} −${this._pct(soil.loss, 1)}`;
    const deg = d.trends.degradation;
    const degText = deg.learning ? this._t('learning', { d: deg.days, n: deg.needed }) : this._t('per_year', { v: `${this._num(deg.rate, 2)} %` });
    const months = P.months;
    let mSvg = '<svg class="mini" viewBox="0 0 300 120" role="img" aria-label="Months">';
    const mmax = Math.max(1, ...months.map((m) => Math.max(m.kwh, m.expected || 0)));
    months.forEach((m, i) => {
      const x = 10 + i * 24;
      const h = (m.kwh / mmax) * 90;
      const he = ((m.expected || 0) / mmax) * 90;
      mSvg += `<rect x="${x}" y="${100 - h}" width="16" height="${h}" rx="3" fill="#FAC775" stroke="${EH_AMBER}" stroke-width=".5"><title>${m.m} · ${this._kwh(m.kwh)}</title></rect>`;
      if (he) mSvg += `<line x1="${x - 2}" x2="${x + 18}" y1="${100 - he}" y2="${100 - he}" stroke="var(--secondary-text-color)" stroke-width="1.5"/>`;
      mSvg += `<text class="svgt" x="${x + 8}" y="114" text-anchor="middle">${new Date(`${m.m}-01`).toLocaleString(this._hass?.locale?.language || 'en', { month: 'narrow' })}</text>`;
    });
    mSvg += '</svg>';
    o += `<div class="grid2">${this._box(this._t('pr_30'), this._t('rain'), `${prSvg}<div class="hint">${ehEsc(soilText)} · ${ehEsc(this._t('degradation'))} ${ehEsc(degText)}</div>`)}${this._box(this._t('months_12'), this._t('expected_line'), mSvg)}</div>`;
    return o;
  }

  // ---------- Batteries
  _batteries() {
    const d = this._data;
    const B = d.batteries;
    if (!B.items.length) return `<div class="empty">${ehEsc(this._t('none'))}</div>`;
    const fleet = B.fleet;
    let o = `<div class="grid4">
      ${this._tile('battery-70', '#E1F5EE', '#0F6E56', this._t('fleet'), this._pct(fleet.soc / 100), `${this._num(fleet.stored_kwh, 1)} / ${this._num(fleet.capacity_kwh, 1)} kWh`, '#0F6E56')}
      ${this._tile('sync', '#E1F5EE', '#0F6E56', this._t('net_power'), `${fleet.power_kw >= 0 ? '+' : '−'}${this._kw(fleet.power_kw)}`, this._t('n_charging', { c: fleet.charging, d: fleet.discharging }))}
      ${this._tile('timer-sand', '#E6F1FB', '#185FA5', this._t('autonomy'), B.autonomy_h != null ? `${this._num(B.autonomy_h, 1)} h` : '–', this._t('autonomy_sub', { v: this._kw(d.live.load_kw) }))}
      ${this._tile('arrow-left-right', '#FAEEDA', '#854F0B', this._t('exchange'), fleet.exchange_kw > 0.05 ? this._kw(fleet.exchange_kw) : this._t('none'), fleet.exchange_kw > 0.05 ? this._t('to_avoid') : '', EH_AMBER)}
    </div>`;
    if (B.items.length > 1) {
      const cards = [`<button class="bcard ${this._battery === 'all' ? 'on' : ''}" data-battery="all"><div class="pa" style="background:#E1F5EE;color:#0F6E56">${ehIcon('layers-triple-outline', 18)}</div><div class="tt"><div class="a1">${ehEsc(this._t('all'))}</div><div class="t3">${ehEsc(this._t('compare'))}</div></div></button>`];
      for (const b of B.items) cards.push(`<button class="bcard ${this._battery === b.key ? 'on' : ''}" data-battery="${ehEsc(b.key)}">${this._miniBattery(b.soc, b.state)}<div class="tt"><div class="a1">${ehEsc(b.name)} <span class="muted">${this._pct(b.soc / 100)}</span></div><div class="t3" style="color:${b.state === 'discharging' ? EH_BLUE : EH_TEAL}">${ehEsc(this._t(b.state))}${b.power_kw ? ` · ${this._kw(b.power_kw)}` : ''}</div><span class="brand">${ehEsc(b.platform)}</span></div></button>`);
      o += `<div class="grid-auto">${cards.join('')}</div>`;
    }
    const selected = B.items.length === 1 ? B.items[0] : B.items.find((b) => b.key === this._battery);
    if (!selected) {
      const metric = (get, max, fmt) => B.items.map((b) => `<div class="barrow"><span>${ehEsc(b.name)}</span><div class="meter"><div style="width:${Math.max(2, ((get(b) || 0) / max) * 100)}%;background:${EH_TEAL}"></div></div><span>${fmt(get(b))}</span></div>`).join('');
      o += `<div class="grid2">${this._box(this._t('soc'), '', metric((b) => b.soc, 100, (v) => this._pct(v / 100)))}${this._box(this._t('health'), '', metric((b) => b.soh, 100, (v) => (v == null ? '–' : `${this._num(v, 0)} %`)))}</div>`;
      o += `<div class="grid2">${this._box(this._t('rte'), '', metric((b) => b.rte, 1, (v) => this._pct(v)))}${this._box(this._t('cycles'), '', metric((b) => b.cycles, Math.max(...B.items.map((b) => b.cycles || 0), 1), (v) => (v == null ? '–' : this._num(v, 0))))}</div>`;
      const cap = B.items.map((b, i) => `<div style="flex:${b.capacity_kwh};background:${['#0F6E56', EH_TEAL, '#5DCAA5', '#9FE1CB'][i % 4]}">${ehEsc(b.name)} ${this._num(b.capacity_kwh, 1)} kWh</div>`).join('');
      o += this._box(this._t('capacity_share'), `${this._num(fleet.capacity_kwh, 1)} kWh`, `<div class="stack">${cap}</div>`);
      return o;
    }
    return o + this._batteryDetail(selected);
  }

  _miniBattery(soc, state) {
    const h = Math.round((30 * (soc || 0)) / 100);
    return `<svg width="22" height="40" viewBox="0 0 22 40" aria-hidden="true"><rect x="7" y="1" width="8" height="4" rx="1.5" fill="var(--secondary-text-color)"/><rect x="2" y="5" width="18" height="34" rx="4" fill="none" stroke="var(--secondary-text-color)" stroke-width="1.5"/><rect x="5" y="${36 - h}" width="12" height="${h}" rx="2" fill="${state === 'discharging' ? EH_BLUE : '#5DCAA5'}"/></svg>`;
  }

  // The selected battery drawn as a wall unit: its level, its state and power, its reserve
  _bigBattery(b) {
    const soc = b.soc || 0;
    const h = Math.round((150 * soc) / 100);
    const res = Math.round((150 * (b.reserve || 0)) / 100);
    const col = b.state === 'discharging' ? EH_BLUE : EH_TEAL;
    const anim = b.state === 'charging' ? `<animate attributeName="opacity" values="1;.35;1" dur="1.6s" repeatCount="indefinite"/>` : '';
    let o = `<svg class="bigbatt" viewBox="0 0 134 200" role="img" aria-label="${ehEsc(b.name)} ${this._pct(soc / 100)}">`;
    o += `<rect x="44" y="6" width="32" height="10" rx="3" fill="var(--secondary-text-color)"/><rect x="14" y="16" width="92" height="176" rx="14" fill="var(--secondary-background-color)" stroke="var(--secondary-text-color)" stroke-width="2"/>`;
    o += `<clipPath id="ehbb"><rect x="22" y="30" width="76" height="150" rx="8"/></clipPath><g clip-path="url(#ehbb)"><rect x="22" y="${180 - h}" width="76" height="${h}" fill="${col}" fill-opacity=".85">${anim}</rect><rect x="22" y="${180 - h}" width="76" height="4" fill="#fff" fill-opacity=".35"/></g>`;
    o += `<line x1="18" x2="102" y1="${180 - res}" y2="${180 - res}" stroke="${EH_RED}" stroke-dasharray="3 3"/><text class="svgt" x="104" y="${183 - res}" style="font-size:9px">${this._num(b.reserve, 0)} %</text>`;
    o += `<text x="60" y="${soc > 55 ? 100 : 70}" text-anchor="middle" class="svgth" style="font-size:22px;fill:${soc > 55 ? '#fff' : 'var(--primary-text-color)'}">${this._num(soc, 0)} %</text>`;
    if (b.state === 'charging') o += `<path d="M64 112 L52 132 H60 L56 150 L70 126 H62 Z" fill="#fff"/>`;
    if (b.state === 'discharging') o += `<path d="M60 118 V146 M50 136 L60 146 L70 136" stroke="#fff" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
    return `${o}</svg>`;
  }

  _batteryDetail(b) {
    const d = this._data;
    const stateColor = b.state === 'discharging' ? EH_BLUE : EH_TEAL;
    const head = `<div class="battrow"><div class="bbwrap">${this._bigBattery(b)}<div class="a1">${ehEsc(b.name)}</div><div class="t3" style="color:${stateColor}">${ehEsc(this._t(b.state))}${b.power_kw ? ` · ${this._kw(b.power_kw)}` : ''}</div><span class="brand">${ehEsc(b.platform)} · ${ehEsc(this._t(`coupling.${b.coupling}`))}</span></div><div class="grid3">
      ${this._tile('heart-pulse', '#E1F5EE', '#0F6E56', this._t('health'), b.soh != null ? `${this._num(b.soh, 0)} %` : '–', b.soh_estimated ? this._t('estimated') : this._t('measured', { a: this._num((b.capacity_kwh * (b.soh || 0)) / 100, 1), b: `${this._num(b.capacity_kwh, 1)} kWh` }))}
      ${this._tile('sync', '#E1F5EE', '#0F6E56', this._t('cycles'), b.cycles != null ? this._num(b.cycles, 0) : '–', b.cycles_estimated ? this._t('estimated') : '')}
      ${this._tile('arrow-left-right', '#E1F5EE', '#0F6E56', this._t('rte'), this._pct(b.rte), this._t('days_30'))}
      ${this._tile('timer-sand', '#E6F1FB', '#185FA5', this._t('autonomy'), b.autonomy_h != null ? `${this._num(b.autonomy_h, 1)} h` : '–', this._t('autonomy_sub', { v: this._kw(d.live.load_kw) }))}
      ${this._tile('thermometer', '#EAF3DE', '#3B6D11', this._t('temperature'), b.temperature != null ? `${this._num(b.temperature, 0)} °C` : '–', '')}
      ${this._tile('battery-70', '#E1F5EE', '#0F6E56', this._t('capacity'), `${this._num(b.capacity_kwh, 1)} kWh`, b.capacity_estimated ? this._t('estimated') : this._t('reserve', { v: `${this._num(b.reserve, 0)} %` }))}
    </div></div>`;
    let o = this._box(b.name, b.platform, head);
    o += `<div class="grid2">${this._box(this._t('soc_today'), b.soc_projection?.length ? this._t('projection_dashed') : '', this._socChart(b))}${this._box(this._t('soh_3y'), b.soh_trend ? this._t('per_year', { v: `${this._num(b.soh_trend.per_year, 2)} %` }) : '', this._sohChart(b))}</div>`;
    if (b.modules?.length) {
      const mods = b.modules.map((m) => `<div class="tile">${this._miniBattery(m.soc, b.state)}<div class="tt"><div class="a1">${ehEsc(m.name)}</div><div class="t3">${m.soc != null ? this._pct(m.soc / 100) : '–'}${m.voltage != null ? ` · ${this._num(m.voltage, 1)} V` : ''}${m.temperature != null ? ` · ${this._num(m.temperature, 1)} °C` : ''}</div></div></div>`).join('');
      o += this._box(this._t('modules'), `${b.modules.length}`, `<div class="grid-auto">${mods}</div>`);
    }
    return o + this._cells(b);
  }

  _socChart(b) {
    const pts = b.soc_today || [];
    if (pts.length < 2) return `<div class="hint">${ehEsc(this._t('learning_short'))}</div>`;
    const start = new Date(this._data.generated);
    start.setHours(0, 0, 0, 0);
    const t0 = start.getTime() / 1000;
    const X = (t) => 30 + ((t - t0) / 86400) * 600;
    const Y = (v) => 110 - (v / 100) * 96;
    let o = `<svg class="mini m" viewBox="0 0 640 128" role="img" aria-label="${ehEsc(this._t('soc_today'))}">`;
    for (const v of [0, 50, 100]) o += `<line x1="30" x2="630" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--divider-color)" stroke-width=".5"/><text class="svgt" x="24" y="${Y(v) + 3}" text-anchor="end">${v}</text>`;
    o += `<line x1="30" x2="630" y1="${Y(b.reserve)}" y2="${Y(b.reserve)}" stroke="${EH_RED}" stroke-width=".8" stroke-dasharray="3 3"/>`;
    const path = pts.map((p, i) => `${i ? 'L' : 'M'}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join(' ');
    o += `<path d="${path} L${X(pts[pts.length - 1][0]).toFixed(1)} 110 L${X(pts[0][0]).toFixed(1)} 110 Z" fill="${EH_TEAL}" fill-opacity=".12"/><path d="${path}" fill="none" stroke="${EH_TEAL}" stroke-width="2"/>`;
    const proj = b.soc_projection || [];
    if (proj.length > 1) o += `<path d="${proj.map((p, i) => `${i ? 'L' : 'M'}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join(' ')}" fill="none" stroke="${EH_TEAL}" stroke-width="1.6" stroke-dasharray="4 4"/>`;
    const last = pts[pts.length - 1];
    o += `<circle cx="${X(last[0])}" cy="${Y(last[1])}" r="4" fill="${EH_TEAL}" stroke="var(--card-background-color)" stroke-width="2"/>`;
    for (let h = 0; h <= 24; h += 6) o += `<text class="svgt" x="${X(t0 + h * 3600)}" y="124" text-anchor="${h === 24 ? 'end' : h === 0 ? 'start' : 'middle'}">${this._lang === 'fr' ? `${h} h` : `${h}:00`}</text>`;
    return `${o}</svg>`;
  }

  _sohChart(b) {
    const tr = b.soh_trend;
    if (!tr) return `<div class="hint">${ehEsc(this._t('learning_short'))}</div>`;
    const day = (s) => new Date(`${s}T12:00`).getTime() / 86400000;
    const all = [...tr.points, tr.projected];
    const d0 = day(all[0][0]);
    const d1 = day(tr.projected[0]);
    const lo = Math.floor(Math.min(...all.map((p) => p[1])) - 2);
    const X = (s) => 30 + ((day(s) - d0) / Math.max(d1 - d0, 1)) * 600;
    const Y = (v) => 110 - ((v - lo) / (100 - lo)) * 96;
    let o = `<svg class="mini m" viewBox="0 0 640 128" role="img" aria-label="${ehEsc(this._t('soh_3y'))}">`;
    for (const v of [lo, Math.round((lo + 100) / 2), 100]) o += `<line x1="30" x2="630" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--divider-color)" stroke-width=".5"/><text class="svgt" x="24" y="${Y(v) + 3}" text-anchor="end">${v}</text>`;
    o += `<path d="${tr.points.map((p, i) => `${i ? 'L' : 'M'}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join(' ')}" fill="none" stroke="${EH_TEAL}" stroke-width="2"/>`;
    const lastP = tr.points[tr.points.length - 1];
    o += `<path d="M${X(lastP[0]).toFixed(1)} ${Y(lastP[1]).toFixed(1)} L${X(tr.projected[0]).toFixed(1)} ${Y(tr.projected[1]).toFixed(1)}" stroke="${EH_TEAL}" stroke-width="1.6" stroke-dasharray="4 4"/>`;
    o += `<circle cx="${X(lastP[0])}" cy="${Y(lastP[1])}" r="4" fill="${EH_TEAL}" stroke="var(--card-background-color)" stroke-width="2"/><circle cx="${X(tr.projected[0])}" cy="${Y(tr.projected[1])}" r="4" fill="var(--card-background-color)" stroke="${EH_TEAL}" stroke-width="2"/><text class="svgt" x="${X(tr.projected[0]) - 6}" y="${Y(tr.projected[1]) - 8}" text-anchor="end">${this._num(tr.projected[1], 1)} %</text>`;
    const y0 = new Date(`${all[0][0]}T12:00`).getFullYear();
    const y1 = new Date(`${tr.projected[0]}T12:00`).getFullYear();
    for (let y = y0 + 1; y <= y1; y++) o += `<text class="svgt" x="${X(`${y}-01-01`)}" y="124" text-anchor="middle">${y}</text>`;
    o += `<line x1="${X(lastP[0])}" x2="${X(lastP[0])}" y1="14" y2="110" stroke="var(--secondary-text-color)" stroke-width=".5" stroke-dasharray="3 3"/>`;
    return `${o}</svg>`;
  }

  _cells(b) {
    const c = b.cells;
    if (!c) return this._box(this._t('cells'), '', `<div class="hint">${ehEsc(this._t('no_cells'))}</div>`);
    const s = c.summary;
    const n = c.voltages.length;
    const mean = c.voltages.reduce((a, v) => a + v, 0) / n;
    const metric = this._cellMetric === 'temperature' && !c.temps?.length ? 'deviation' : this._cellMetric;
    const per = c.per_module || Math.min(n, 16);
    const rows = Math.ceil(n / per);
    const tMin = c.temps?.length ? Math.min(...c.temps) : 0;
    const tMax = c.temps?.length ? Math.max(...c.temps) : 1;
    const cell = (i) => {
      const v = c.voltages[i];
      const dev = (v - mean) * 1000;
      let bg;
      let label;
      if (metric === 'voltage') {
        bg = `rgba(29,158,117,${(0.2 + Math.min(1, (v - s.min_v) / Math.max(s.max_v - s.min_v, 0.001)) * 0.65).toFixed(2)})`;
        label = this._num(v, 3);
      } else if (metric === 'temperature') {
        const k = (c.temps[i] - tMin) / Math.max(tMax - tMin, 0.1);
        bg = `rgba(${Math.round(55 + 180 * k)},${Math.round(138 - 60 * k)},${Math.round(221 - 160 * k)},.75)`;
        label = this._num(c.temps[i], 1);
      } else {
        bg = Math.abs(dev) < 4 ? 'rgba(136,135,128,.18)' : dev < 0 ? `rgba(239,159,39,${Math.min(1, 0.25 + -dev / 36).toFixed(2)})` : `rgba(55,138,221,${Math.min(1, 0.25 + dev / 14).toFixed(2)})`;
        label = `${dev >= 0 ? '+' : ''}${Math.round(dev)}`;
      }
      const bal = c.balancing?.includes(i) ? '<span class="baldot"></span>' : '';
      const drift = c.drifting?.includes(i) ? ' drift' : '';
      return `<button class="cell${this._cell === i ? ' sel' : ''}${drift}" data-cell="${i}" style="background:${bg}" title="C${(i % per) + 1} · ${this._num(v, 3)} V">${label}${bal}</button>`;
    };
    let grid = '';
    for (let r = 0; r < rows; r++) {
      const cellsRow = [];
      for (let i = r * per; i < Math.min(n, (r + 1) * per); i++) cellsRow.push(cell(i));
      grid += `<div class="cellrow"><span class="rowlab">${c.per_module ? ehEsc(b.modules?.[r]?.name || `M${r + 1}`) : ''}</span><div class="cells" style="grid-template-columns:repeat(${per},1fr)">${cellsRow.join('')}</div></div>`;
    }
    const metrics = ['deviation', 'voltage', ...(c.temps?.length ? ['temperature'] : [])];
    const seg = `<div class="seg">${metrics.map((m) => `<button class="${metric === m ? 'on' : ''}" data-cellmetric="${m}">${ehEsc(this._t(m))}</button>`).join('')}</div>`;
    const legendBits = metric === 'deviation' ? `<span class="chip"><span class="sw" style="background:rgba(239,159,39,.8)"></span>${ehEsc(this._t('low'))}</span><span class="chip"><span class="sw" style="background:rgba(136,135,128,.25)"></span>± 4 mV</span><span class="chip"><span class="sw" style="background:rgba(55,138,221,.8)"></span>${ehEsc(this._t('high'))}</span>` : '';
    const legend = `<div class="legend">${legendBits}${c.balancing?.length ? `<span class="chip"><span class="baldot static"></span>${ehEsc(this._t('balancing'))}</span>` : ''}${c.drifting?.length ? `<span class="chip"><span class="sw" style="outline:2px solid ${EH_RED};background:none"></span>${ehEsc(this._t('drifting'))}</span>` : ''}</div>`;
    const tiles = `<div class="grid4">
      ${this._tile('flash-outline', '#E1F5EE', '#0F6E56', this._t('max'), `${this._num(s.max_v, 3)} V`, this._cellName(c, s.max_index, b))}
      ${this._tile('flash-outline', '#FAEEDA', '#854F0B', this._t('min'), `${this._num(s.min_v, 3)} V`, this._cellName(c, s.min_index, b), EH_AMBER)}
      ${this._tile('scale-balance', '#FAEEDA', '#854F0B', this._t('spread'), `${this._num(s.spread_mv, 0)} mV`, this._t('of_threshold', { t: `${c.threshold_mv} mV` }), EH_AMBER)}
      ${this._tile('sync', '#EEEDFE', '#3C3489', this._t('balancing'), c.balancing?.length ? this._t('n_cells', { n: c.balancing.length }) : this._t('none'), '')}
    </div>`;
    let o = this._box(`${this._t('cells')} · ${n}`, c.per_module ? this._t('modules_x_cells', { m: rows, c: per }) : '', `${tiles}<div class="hd" style="margin-top:10px">${seg}</div>${grid}${legend}`);
    if (this._cell != null && this._cell < n) o += this._cellDetail(b, this._cell, mean);
    o += this._box(this._t('spread_trend'), c.days_to_threshold != null ? this._t('threshold_in', { t: `${c.threshold_mv} mV`, d: this._num(c.days_to_threshold, 0) }) : this._t('stable'), this._spreadChart(c));
    return o;
  }

  _cellName(c, i, b) {
    if (!c.per_module) return `C${i + 1}`;
    const m = Math.floor(i / c.per_module);
    return `${b.modules?.[m]?.name || `M${m + 1}`} · C${(i % c.per_module) + 1}`;
  }

  _cellDetail(b, i, mean) {
    const c = b.cells;
    const v = c.voltages[i];
    const dev = (v - mean) * 1000;
    const hist = c.history?.[i] || [];
    const slope = c.drift_mv_day?.[i];
    let spark = '';
    if (hist.length > 1) {
      const lo = Math.min(...hist, -5);
      const hi = Math.max(...hist, 5);
      const X = (k) => 10 + (k / (hist.length - 1)) * 580;
      const Y = (val) => 84 - ((val - lo) / (hi - lo)) * 72;
      spark = `<svg class="mini m" viewBox="0 0 600 104" role="img" aria-label="30 d"><line x1="10" x2="590" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--divider-color)"/><path d="${hist.map((val, k) => `${k ? 'L' : 'M'}${X(k).toFixed(1)} ${Y(val).toFixed(1)}`).join(' ')}" fill="none" stroke="${c.drifting?.includes(i) ? EH_RED : EH_TEAL}" stroke-width="2"/><text class="svgt" x="10" y="100">${ehEsc(this._t('days_30'))}</text><text class="svgt" x="590" y="100" text-anchor="end">mV</text></svg>`;
    }
    const diag = c.drifting?.includes(i) ? this._t('diag_drift', { v: `${slope > 0 ? '+' : ''}${this._num(slope, 1)}` }) : this._t('diag_stable');
    const tiles = `<div class="grid4">
      ${this._tile('flash-outline', '#E1F5EE', '#0F6E56', this._t('voltage'), `${this._num(v, 3)} V`, '')}
      ${this._tile('scale-balance', '#FAEEDA', '#854F0B', this._t('deviation'), `${dev >= 0 ? '+' : ''}${Math.round(dev)} mV`, slope != null ? this._t('per_day', { v: `${slope > 0 ? '+' : ''}${this._num(slope, 2)} mV` }) : '')}
      ${this._tile('thermometer', '#EAF3DE', '#3B6D11', this._t('temperature'), c.temps?.length ? `${this._num(c.temps[i], 1)} °C` : '–', '')}
      ${this._tile('sync', '#EEEDFE', '#3C3489', this._t('balancing'), c.balancing?.includes(i) ? this._t('yes') : this._t('no'), '')}
    </div>`;
    return this._box(this._cellName(c, i, b), '', `${tiles}<div class="grid2 tight"><div>${spark}</div><div class="diag ${c.drifting?.includes(i) ? 'bad' : ''}">${ehIcon(c.drifting?.includes(i) ? 'alert-outline' : 'check', 16)}<span>${ehEsc(diag)}</span></div></div>`);
  }

  _spreadChart(c) {
    const spreads = c.spread_30d || [];
    if (spreads.length < 2) return `<div class="hint">${ehEsc(this._t('learning_short'))}</div>`;
    const ahead = c.days_to_threshold != null ? Math.min(c.days_to_threshold, 60) : 0;
    const total = spreads.length - 1 + ahead;
    const maxv = Math.max(c.threshold_mv * 1.15, ...spreads);
    const X = (k) => 40 + (k / Math.max(total, 1)) * 1120;
    const Y = (v) => 110 - (v / maxv) * 96;
    let o = `<svg class="mini m" viewBox="0 0 1200 128" role="img" aria-label="${ehEsc(this._t('spread_trend'))}">`;
    o += `<line x1="40" x2="1160" y1="${Y(c.threshold_mv)}" y2="${Y(c.threshold_mv)}" stroke="${EH_RED}" stroke-dasharray="3 3"/><text class="svgt" x="44" y="${Y(c.threshold_mv) - 4}" style="fill:${EH_RED}">${ehEsc(this._t('threshold'))} ${c.threshold_mv} mV</text>`;
    o += `<path d="${spreads.map((v, k) => `${k ? 'L' : 'M'}${X(k).toFixed(1)} ${Y(v).toFixed(1)}`).join(' ')}" fill="none" stroke="#EF9F27" stroke-width="2"/>`;
    const lastK = spreads.length - 1;
    if (ahead) {
      const end = spreads[lastK] + ((c.threshold_mv - spreads[lastK]) * ahead) / c.days_to_threshold;
      o += `<path d="M${X(lastK).toFixed(1)} ${Y(spreads[lastK]).toFixed(1)} L${X(total).toFixed(1)} ${Y(end).toFixed(1)}" stroke="#EF9F27" stroke-width="1.6" stroke-dasharray="4 4"/><circle cx="${X(total)}" cy="${Y(end)}" r="4" fill="var(--card-background-color)" stroke="${EH_RED}" stroke-width="2"/>`;
      o += `<text class="svgt" x="${X(total) - 6}" y="${Y(end) + 16}" text-anchor="end">${ehEsc(this._t('in_days', { d: this._num(c.days_to_threshold, 0) }))}</text>`;
    }
    o += `<line x1="${X(lastK)}" x2="${X(lastK)}" y1="14" y2="110" stroke="var(--secondary-text-color)" stroke-width=".5" stroke-dasharray="3 3"/><line x1="40" x2="1160" y1="110" y2="110" stroke="var(--divider-color)"/>`;
    o += `<text class="svgt" x="40" y="124">−${ehEsc(this._t('days_30'))}</text><text class="svgt" x="${X(lastK)}" y="124" text-anchor="middle">${ehEsc(this._t('today'))}</text>`;
    return `${o}</svg>`;
  }

  // ---------- Losses
  _losses() {
    const d = this._data;
    const Lt = d.losses.today;
    const month = d.losses.month;
    const lostToday = Object.entries(Lt).filter(([k]) => !['potential', 'produced'].includes(k)).reduce((a, [, v]) => a + (v || 0), 0);
    const monthTotal = Object.values(month).reduce((a, v) => a + (v || 0), 0);
    const main = Object.entries(month).sort((a, b) => (b[1] || 0) - (a[1] || 0))[0];
    let o = `<div class="grid4">
      ${this._tile('flash-outline', '#FCEBEB', '#A32D2D', this._t('lost_today'), this._kwh(lostToday), Lt.potential ? this._pct(lostToday / Lt.potential) : '', EH_RED)}
      ${this._tile('calendar-month', '#FCEBEB', '#A32D2D', this._t('this_month_lost'), this._kwh(monthTotal), this._eur(d.losses.month_eur), EH_RED)}
      ${this._tile('check', '#EAF3DE', '#3B6D11', this._t('availability'), this._pct(d.losses.availability, 1), '', EH_GREEN)}
      ${this._tile('alert-outline', '#FCEBEB', '#A32D2D', this._t('main_cause'), main && main[1] > 0 ? ehEsc(this._t(`causes.${main[0]}`)) : this._t('none'), main && monthTotal ? this._pct(main[1] / monthTotal) : '', EH_RED)}
    </div>`;
    // cascade
    const steps = [['potential', Lt.potential, '#B4B2A9', true], ['clipping', -(Lt.clipping || 0), EH_RED], ['shading', -(Lt.shading || 0), '#F09595'], ['soiling', -(Lt.soiling || 0), '#F09595'], ['limitation', -(Lt.limitation || 0), '#F09595'], ['unavailability', -(Lt.unavailability || 0), '#F09595'], ['produced', Lt.produced, EH_AMBER, true]];
    const top = Lt.potential || 1;
    const floor = Math.max(0, Math.floor((Lt.produced || 0) * 0.85));
    const Y = (v) => 140 - ((v - floor) / Math.max(top - floor, 0.001)) * 120;
    let cur = 0;
    let svg = '<svg class="mini" viewBox="0 0 340 170" role="img" aria-label="Cascade">';
    steps.forEach(([key, v, col, total], i) => {
      const x = 8 + i * 47;
      let y0;
      let y1;
      if (total) {
        y0 = Y(v || 0);
        y1 = 140;
        cur = v || 0;
      } else {
        y0 = Y(cur);
        y1 = Y(cur + v);
        cur += v;
      }
      svg += `<rect x="${x}" y="${y0.toFixed(1)}" width="34" height="${Math.max(1.5, y1 - y0).toFixed(1)}" rx="3" fill="${col}"/>`;
      if (i < steps.length - 1) svg += `<line x1="${x + 34}" x2="${x + 47}" y1="${Y(cur).toFixed(1)}" y2="${Y(cur).toFixed(1)}" stroke="var(--secondary-text-color)" stroke-width=".6" stroke-dasharray="2 2"/>`;
      const label = total ? this._num(v || 0, 1) : v ? `−${this._num(-v, 1)}` : '0';
      svg += `<text class="svgt" x="${x + 17}" y="${(y0 - 5).toFixed(1)}" text-anchor="middle" ${total ? '' : `style="fill:${EH_RED}"`}>${label}</text><text class="svgt" x="${x + 17}" y="158" text-anchor="middle">${ehEsc(this._t(`causes_short.${key}`))}</text>`;
    });
    svg += '<path d="M2 136 l4 -4 l4 4 l4 -4" fill="none" stroke="var(--secondary-text-color)"/><line x1="6" x2="336" y1="140" y2="140" stroke="var(--divider-color)"/></svg>';
    // heatmap
    const hm = d.losses.heatmap;
    const hmax = Math.max(0.05, ...hm.flatMap((r) => r.h.map((v) => v || 0)));
    let heat = '<svg class="mini" viewBox="0 0 300 150" role="img" aria-label="Heatmap">';
    hm.forEach((r, di) => {
      r.h.forEach((v, k) => {
        const op = v ? Math.min(1, 0.15 + (0.85 * v) / hmax) : 0;
        heat += `<rect x="${34 + k * 36}" y="${6 + di * (128 / Math.max(hm.length, 1))}" width="34" height="${Math.max(128 / Math.max(hm.length, 1) - 0.7, 1)}" rx="1" fill="${op ? EH_RED : 'var(--divider-color)'}" ${op ? `fill-opacity="${op.toFixed(2)}"` : ''}><title>${r.d} ${10 + k}h · ${this._kwh(v)}</title></rect>`;
      });
    });
    for (let k = 0; k < 7; k++) heat += `<text class="svgt" x="${51 + k * 36}" y="146" text-anchor="middle">${10 + k}h</text>`;
    heat += '</svg>';
    o += `<div class="grid2">${this._box(this._t('cascade'), 'kWh', `${svg}<div class="hint">${ehEsc(this._t('axis_cut'))}</div>`)}${this._box(this._t('heatmap'), 'kWh', heat)}</div>`;
    // causes
    const CAUSES = ['clipping', 'shading', 'soiling', 'limitation', 'unavailability'];
    const colors = { clipping: EH_RED, shading: '#F09595', soiling: '#EF9F27', limitation: EH_VIOLET, unavailability: '#888780' };
    const stack = CAUSES.map((k) => [k, month[k] || 0]).filter(([, v]) => v > 0).map(([k, v]) => `<div style="flex:${v};background:${colors[k]}" title="${ehEsc(this._t(`causes.${k}`))}"></div>`).join('');
    const legend = CAUSES.map((k) => [k, month[k] || 0]).map(([k, v]) => `<span class="chip"><span class="sw" style="background:${colors[k]}"></span>${ehEsc(this._t(`causes.${k}`))} ${monthTotal ? this._pct(v / monthTotal) : '–'}</span>`).join('');
    o += this._box(this._t('causes_month'), this._kwh(monthTotal), `${stack ? `<div class="stack thin">${stack}</div>` : ''}<div class="legend">${legend}</div>`);
    o += this._box(this._t('events'), this._t('days_30'), this._events());
    return o;
  }

  _events() {
    const ev = this._data.losses.events || [];
    if (!ev.length) return `<div class="hint">${ehEsc(this._t('no_event'))}</div>`;
    const icon = { clipping: 'alert-outline', string_lagging: 'solar-panel', shading: 'weather-cloudy-alert', soiling: 'water-off', cell_drift: 'scale-balance', unavailability: 'power-plug-off-outline' };
    const statusColor = { recurring: ['#FCEBEB', '#A32D2D'], watch: ['#FAEEDA', '#854F0B'], resolved: ['#EAF3DE', '#3B6D11'] };
    const day = (s) => (s ? new Date(`${s}T12:00`).toLocaleDateString(this._locale, { day: 'numeric', month: 'short' }) : '');
    return ev
      .map((e) => {
        const [bg, fg] = statusColor[e.status];
        const title = this._t(`event.${e.kind}`, { unit: e.unit || '', name: e.name || '', battery: e.battery || '', cell: e.cell || '', from: e.start != null ? this._hm(e.start) : '', to: e.end != null ? this._hm(e.end) : '' });
        const bits = [];
        if (e.first && e.first !== e.last) bits.push(`${day(e.first)} → ${day(e.last)}`);
        else if (e.last) bits.push(day(e.last));
        if (e.days) bits.push(this._t(e.days === 1 ? 'one_day' : 'n_days', { n: e.days }));
        if (e.kwh != null) bits.push(this._kwh(e.kwh));
        if (e.relative != null) bits.push(`−${this._num((1 - e.relative) * 100, 0)} %`);
        if (e.loss != null) bits.push(`−${this._pct(e.loss, 1)}`);
        return `<div class="event"><div class="pa" style="background:${bg};color:${fg}">${ehIcon(icon[e.kind] || 'alert-outline', 18)}</div><div class="tt"><div class="a1">${ehEsc(title)}</div><div class="t3">${ehEsc(bits.join(' · '))}</div></div><span class="status" style="background:${bg};color:${fg}">${ehEsc(this._t(`status.${e.status}`))}</span></div>`;
      })
      .join('');
  }

  // ---------- Finances
  _calendar() {
    const cal = this._data.finances.calendar || [];
    if (!cal.length) return '';
    const max = Math.max(0.01, ...cal.map((c) => c.eur || 0));
    const first = new Date(`${cal[0].d}T12:00`);
    const heads = Array.from({ length: 7 }, (_v, i) => new Date(first.getTime() + i * 86400000).toLocaleDateString(this._locale, { weekday: 'narrow' }));
    const today = cal[cal.length - 1].d;
    const cells = cal
      .map((c) => {
        const k = c.eur != null ? c.eur / max : 0;
        const dt = new Date(`${c.d}T12:00`);
        return `<div class="cal${c.d === today ? ' today' : ''}" style="background:${c.eur != null ? `rgba(99,153,34,${(0.12 + 0.8 * k).toFixed(2)})` : 'var(--secondary-background-color)'};color:${k > 0.55 ? '#fff' : 'var(--primary-text-color)'}" title="${ehEsc(dt.toLocaleDateString(this._locale, { weekday: 'long', day: 'numeric', month: 'long' }))} · ${this._eur(c.eur)}"><span>${dt.getDate()}</span><b>${c.eur != null ? this._num(c.eur, c.eur < 10 ? 2 : 1) : ''}</b></div>`;
      })
      .join('');
    const legend = `<div class="legend"><span class="chip">${this._eur(0, 0)}</span><span class="calscale"></span><span class="chip">${this._eur(max)}</span></div>`;
    return `<div class="calgrid">${heads.map((h) => `<div class="calh">${ehEsc(h)}</div>`).join('')}${cells}</div>${legend}`;
  }

  _bill() {
    const b = this._data.finances.bill;
    if (!b) return '';
    const max = Math.max(1, b.month.without || 0, b.year.without || 0);
    const row = (label, p) => {
      const saved = (p.without || 0) - (p.with || 0);
      const scale = Math.max(p.without || 0, Math.abs(p.with || 0), 1);
      return `<div class="billrow"><div class="a1">${ehEsc(label)}</div>
        <div class="barrow"><span>${ehEsc(this._t('without_solar'))}</span><div class="meter"><div style="width:${((p.without || 0) / scale) * 100}%;background:#B4B2A9"></div></div><span>${this._eur(p.without, 0)}</span></div>
        <div class="barrow"><span>${ehEsc(this._t('with_solar'))}</span><div class="meter"><div style="width:${(Math.max(p.with || 0, 0) / scale) * 100}%;background:#639922"></div></div><span>${this._eur(p.with, 0)}</span></div>
        <div class="t3" style="color:${EH_GREEN}">${ehEsc(this._t('saved_amount', { v: this._eur(saved, 0) }))}${(p.with || 0) < 0 ? ` · ${ehEsc(this._t('credit'))}` : ''}</div></div>`;
    };
    return `${row(this._t('this_month'), b.month)}${row(this._t('months_12'), b.year)}<div class="hint">${ehEsc(this._t('bill_hint', { i: this._eur(this._data.finances.import_price, 4), e: this._eur(this._data.finances.export_price, 4) }))}</div>${max ? '' : ''}`;
  }

  _comparator() {
    const C = this._data.finances.comparator;
    if (!C) return '';
    if (!C.offers.length) return this._box(this._t('comparator'), '', `<div class="hint">${ehEsc(this._t('comparator_learning', { n: C.needed, d: C.days }))}</div>`);
    const tag = (r) => `<span class="pill small">${ehEsc(this._t(r.custom ? 'custom_offer' : r.regulated ? 'regulated' : 'market'))}</span>`;
    const rows = C.offers
      .map((r) => {
        const cur = r.key === C.current;
        const best = r.key === C.best;
        const delta = r.delta == null || cur ? '' : `<span style="color:${r.delta < 0 ? EH_GREEN : 'var(--secondary-text-color)'}">${r.delta > 0 ? '+' : ''}${this._eur(r.delta, 0)}</span>`;
        return `<tr class="${cur ? 'cur' : ''}"><td><div class="a1 oname">${best ? `<span style="color:${EH_GREEN}">${ehIcon('check', 14)}</span>` : ''}${ehEsc(r.name)}</div><div>${tag(r)}${cur ? ` <span class="pill small cur">${ehEsc(this._t('your_contract'))}</span>` : ''}</div></td><td class="num">${this._eur(r.avg_price, 4)}</td><td class="num">${this._eur(r.subscription, 0)}</td><td class="num"><b>${this._eur(r.total, 0)}</b><div class="t3">${delta}</div></td></tr>`;
      })
      .join('');
    const bestOffer = C.offers.find((r) => r.key === C.best);
    const verdict = !C.current ? this._t('no_contract') : C.best === C.current ? this._t('best_is_current') : this._t('best_saving', { name: bestOffer.name, v: this._eur(C.saving, 0) });
    const notes = [this._t('grid_info', { d: new Date(`${C.grid_date}T12:00`).toLocaleDateString(this._locale, { day: 'numeric', month: 'long', year: 'numeric' }) })];
    if (C.scale > 1.05) notes.push(this._t('scaled', { n: C.days }));
    if (C.colors < C.days) notes.push(this._t('colors_estimated', { n: C.days - C.colors }));
    const stale = C.grid_stale ? `<div class="hint" style="color:${EH_AMBER}">${ehIcon('alert-outline', 14)} ${ehEsc(this._t('grid_stale'))}</div>` : '';
    return this._box(
      this._t('comparator'),
      this._t('comparator_hint', { v: this._kwh(C.kwh) }),
      `<div class="verdict ${C.current && C.best !== C.current ? 'gain' : ''}">${ehEsc(verdict)}</div><table class="offers"><tr class="th"><td>${ehEsc(this._t('offer'))}</td><td class="num">${ehEsc(this._t('avg_price'))}</td><td class="num">${ehEsc(this._t('subscription'))}</td><td class="num">${ehEsc(this._t('total_year'))}</td></tr>${rows}</table>${stale}<div class="hint">${notes.map(ehEsc).join(' ')}</div>`,
    );
  }

  _finances() {
    const d = this._data;
    const F = d.finances;
    const share = F.share_paid ?? 0;
    const ring = `<svg width="140" height="140" viewBox="0 0 150 150" role="img" aria-label="${this._pct(share)}"><circle cx="75" cy="75" r="62" fill="none" stroke="var(--divider-color)" stroke-width="12"/><circle cx="75" cy="75" r="62" fill="none" stroke="#639922" stroke-width="12" stroke-linecap="round" transform="rotate(-90 75 75)" stroke-dasharray="${(389.6 * share).toFixed(1)} 390"/><text x="75" y="72" text-anchor="middle" class="svgth" style="font-size:22px">${this._pct(share)}</text><text x="75" y="92" text-anchor="middle" class="svgt">${ehEsc(this._t('amortised'))}</text></svg>`;
    const be = this._breakEven(this._rate);
    let o = `<div class="ringrow">${ring}<div class="grid2 tight">
      ${this._tile('piggy-bank-outline', '#EAF3DE', '#3B6D11', this._t('gained_since'), this._eur(F.since, 0), F.net_cost ? this._t('of_net_cost', { v: this._eur(F.net_cost, 0) }) : '', EH_GREEN)}
      ${this._tile('flag-outline', '#E6F1FB', '#185FA5', this._t('break_even'), be.label, be.sub, '#185FA5')}
      ${this._tile('calendar-month', '#EAF3DE', '#3B6D11', this._t('this_month'), this._eur(F.month), '')}
      ${this._tile('lightbulb-on-outline', '#EAF3DE', '#3B6D11', this._t('gain_20'), be.gain20 != null ? this._eur(be.gain20, 0) : '–', '', EH_GREEN)}
    </div></div>`;
    if (!F.net_cost) o += `<div class="hint">${ehEsc(this._t('no_cost'))}</div>`;
    else {
      o += this._box(this._t('projection'), this._t('net_cost', { v: this._eur(F.net_cost, 0) }), `<label class="slider">${ehEsc(this._t('price_rise'))}<input type="range" min="0" max="8" step="0.5" value="${this._rate}" data-rate><b>${ehEsc(this._t('per_year_short', { v: this._num(this._rate, 1) }))}</b></label>${be.svg}`);
    }
    const monthly = F.monthly;
    const mmax = Math.max(1, ...monthly.map((m) => m.eur));
    let bars = '<svg class="mini" viewBox="0 0 300 120" role="img" aria-label="Gains">';
    monthly.forEach((m, i) => {
      const h = (m.eur / mmax) * 90;
      bars += `<rect x="${10 + i * 24}" y="${100 - h}" width="16" height="${h}" rx="3" fill="#639922"><title>${m.m} · ${this._eur(m.eur)}</title></rect><text class="svgt" x="${18 + i * 24}" y="114" text-anchor="middle">${new Date(`${m.m}-01`).toLocaleString(this._hass?.locale?.language || 'en', { month: 'narrow' })}</text>`;
    });
    bars += '</svg>';
    const bd = F.breakdown;
    const total = (bd.direct || 0) + (bd.battery || 0) + (bd.export || 0);
    const row = (label, v, col) => `<div class="barrow"><span>${ehEsc(label)}</span><div class="meter"><div style="width:${total ? (v / total) * 100 : 0}%;background:${col}"></div></div><span>${this._eur(v, 0)}</span></div>`;
    o += `<div class="grid2">${this._box(this._t('gains_calendar'), this._t('weeks_6'), this._calendar())}${this._box(this._t('bill_title'), '', this._bill())}</div>`;
    o += this._comparator();
    o += `<div class="grid2">${this._box(this._t('gains_month'), '', bars)}${this._box(this._t('gains_from'), this._eur(total, 0), row(this._t('direct'), bd.direct, '#639922') + row(this._t('battery_restored'), bd.battery, EH_TEAL) + row(this._t('export'), bd.export, EH_BLUE))}</div>`;
    return o;
  }

  _breakEven(rate) {
    // The same projection as the integration (analytics/finance.py), redrawn here when the slider moves.
    const F = this._data.finances;
    if (!F.net_cost) return { label: '–', sub: '', svg: '', gain20: null };
    const age = F.age_years || 0;
    let total = F.since;
    let be = total >= F.net_cost ? 0 : null;
    const pts = [[age, total]];
    let invPaid = age >= F.inverter_lifetime_years;
    for (let m = 1; m <= Math.round((20 - age) * 12); m++) {
      const y = m / 12;
      total += (F.yearly / 12) * (1 + rate / 100) ** y * (1 - 0.005 * (age + y));
      if (!invPaid && age + y >= F.inverter_lifetime_years) {
        total -= F.inverter_replacement_cost;
        invPaid = true;
      }
      if (be == null && total >= F.net_cost) be = y;
      if (m % 3 === 0) pts.push([age + y, total]);
    }
    const ymax = Math.max(F.net_cost * 1.4, total * 1.05);
    const X = (a) => 40 + (a / 20) * 590;
    const Y = (v) => 125 - (Math.max(v, 0) / ymax) * 110;
    let svg = `<svg class="mini" viewBox="0 0 640 150" role="img" aria-label="Projection"><line x1="40" x2="630" y1="125" y2="125" stroke="var(--divider-color)"/><line x1="40" x2="630" y1="${Y(F.net_cost)}" y2="${Y(F.net_cost)}" stroke="${EH_BLUE}" stroke-dasharray="3 3"/>`;
    svg += `<path d="M${X(0)} 125 L${X(age)} ${Y(F.since)}" fill="none" stroke="#639922" stroke-width="2.2"/><path d="${pts.map((p, i) => `${i ? 'L' : 'M'}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join(' ')}" fill="none" stroke="#639922" stroke-width="1.6" stroke-dasharray="4 4"/><circle cx="${X(age)}" cy="${Y(F.since)}" r="4.5" fill="#639922" stroke="var(--card-background-color)" stroke-width="2"/>`;
    if (be != null) svg += `<circle cx="${X(age + be)}" cy="${Y(F.net_cost)}" r="5" fill="var(--card-background-color)" stroke="${EH_BLUE}" stroke-width="2"/>`;
    if (F.inverter_lifetime_years > age) svg += `<line x1="${X(F.inverter_lifetime_years)}" x2="${X(F.inverter_lifetime_years)}" y1="20" y2="125" stroke="var(--secondary-text-color)" stroke-width=".5" stroke-dasharray="2 3"/><text class="svgt" x="${X(F.inverter_lifetime_years) + 4}" y="30">${ehEsc(this._t('inverter'))}</text>`;
    for (let y = 0; y <= 20; y += 4) svg += `<text class="svgt" x="${X(y)}" y="143" text-anchor="middle">${y}</text>`;
    svg += '</svg>';
    const when = be == null ? null : new Date(Date.now() + be * 365.25 * 86400000);
    return {
      label: when ? when.toLocaleDateString(this._hass?.locale?.language || 'en', { month: 'short', year: 'numeric' }) : '–',
      sub: be != null ? this._t('in_years', { v: this._num(be, 1) }) : '',
      svg,
      gain20: total - F.net_cost,
    };
  }

  // ---------- Settings
  _settingsTab() {
    const subs = ['sources', 'installation', 'tariffs', 'alerts', 'yaml'];
    const sub = subs.includes(this._sub) ? this._sub : 'sources';
    const nav = `<div class="subtabs">${subs.map((k) => `<button class="${sub === k ? 'on' : ''}" data-sub="${k}">${ehEsc(this._t(`subtabs.${k}`))}</button>`).join('')}<button class="round refresh-inline" data-action="refresh" aria-label="Refresh">${ehIcon('refresh', 16)}</button></div>`;
    this._snips = [];
    const body = { sources: this._setSources, installation: this._setInstallation, tariffs: this._setTariffs, alerts: this._setAlerts, yaml: this._setYaml }[sub].call(this);
    return nav + body;
  }

  _snip(yaml) {
    this._snips.push(yaml);
    return `<button class="copy" data-snip="${this._snips.length - 1}">${ehIcon('content-copy', 14)} ${ehEsc(this._t('copy_yaml'))}</button>`;
  }

  _setSources() {
    const d = this._data;
    let o = '';
    const sugg = d.suggestions || [];
    if (sugg.length) {
      o += this._box(this._t('suggestions'), `${sugg.length}`, sugg.map((s) => `<div class="sugg"><span class="pa sm" style="background:#EEEDFE;color:#3C3489">${ehIcon('lightbulb-on-outline', 14)}</span><div class="tt"><div class="a1">${ehEsc(this._t(`suggest.${s.kind}`, { bms: s.bms || '', battery: s.battery || '' }))}</div><div class="t3">${s.correlation != null ? ehEsc(this._t('correlation', { v: this._num(s.correlation, 2) })) : ''}</div></div>${this._snip(s.yaml)}</div>`).join(''));
    }
    const capIcon = { provided: 'check', estimated: 'function-variant', absent: 'minus' };
    const roleOrder = ['pv', 'storage', 'meter', 'forecast', 'weather', 'tariff', 'prefs'];
    const sources = [...d.sources].sort((a, b) => roleOrder.indexOf(a.role) - roleOrder.indexOf(b.role));
    let lastRole = null;
    const list = sources
      .map((src) => {
        const head = src.role !== lastRole ? `<div class="rolehead">${ehEsc(this._t(`source_role.${src.role}`))}</div>` : '';
        lastRole = src.role;
        const caps = Object.entries(src.capabilities).map(([k, v]) => `<span class="cap ${v}" title="${ehEsc(this._t(`capabilities.${v}`))}">${ehIcon(capIcon[v] || 'minus', 12)}${ehEsc(this._t(`cap.${k}`))}</span>`).join('');
        return `${head}<div class="src"><div class="tt"><div class="a1">${ehEsc(src.name)} ${src.status === 'beta' ? `<span class="pill small">${ehEsc(this._t('beta'))}</span>` : ''}</div><div>${caps}</div></div></div>`;
      })
      .join('');
    o += this._box(this._t('sources'), `${d.sources.length}`, `${list}<div class="legend"><span class="cap provided">${ehIcon('check', 12)}${ehEsc(this._t('capabilities.provided'))}</span><span class="cap estimated">${ehIcon('function-variant', 12)}${ehEsc(this._t('capabilities.estimated'))}</span><span class="cap absent">${ehIcon('minus', 12)}${ehEsc(this._t('capabilities.absent'))}</span></div>`);
    o += this._box(this._t('quality_24h'), this._t('quality_hint'), this._quality());
    const excl = Object.entries(d.excluded || {}).map(([e, why]) => `<tr><td>${ehEsc(this._t('excluded'))}</td><td><code class="muted">${ehEsc(e)}</code></td><td class="age">${ehEsc(this._t(`excluded_reason.${why}`))}</td></tr>`).join('');
    if (excl) o += this._box(this._t('excluded'), '', `<table class="roles">${excl}</table>`);
    return o;
  }

  _quality() {
    const q = this._data.quality || [];
    if (!q.length) return `<div class="hint">${ehEsc(this._t('learning_short'))}</div>`;
    const rows = q
      .map((r) => {
        const slots = r.slots.map((v) => `<i style="background:${v == null ? 'var(--divider-color)' : v >= 0.99 ? '#97C459' : v >= 0.5 ? '#EF9F27' : EH_RED}"></i>`).join('');
        const gaps = (r.gaps || []).map(([a, b]) => `${this._time(a)}–${this._time(b)}`).join(', ');
        const age = this._data.ages?.[r.entity];
        return `<div class="qrow"><div class="qname"><div class="a1">${ehEsc(this._roleLabel(r.role))}</div><code class="t3">${ehEsc(r.entity)}</code></div><div class="qbar">${slots}</div><div class="qval"><b style="color:${r.share >= 0.99 ? EH_GREEN : r.share >= 0.9 ? EH_AMBER : EH_RED}">${this._pct(r.share, 1)}</b><div class="t3">${gaps ? ehEsc(this._t('gaps', { v: gaps })) : age != null ? ehEsc(this._t('last_seen', { v: `${this._num(age, 0)} s` })) : ''}</div></div></div>`;
      })
      .join('');
    return `${rows}<div class="qrow axis"><span></span><div class="qaxis"><span>−24 h</span><span>−12 h</span><span>${ehEsc(this._t('now_short'))}</span></div><span></span></div>`;
  }

  _roleLabel(role) {
    if (role.includes('.')) {
      const [key, field] = role.split('.');
      const b = this._data.batteries.items.find((x) => x.key === key);
      return `${b ? b.name : key} · ${this._t(`cap.${field === 'power' ? 'power' : 'soc'}`)}`;
    }
    return this._t(`role.${role}`, {}, role);
  }

  _setInstallation() {
    const d = this._data;
    const s = this._settings || {};
    const roles = d.roles || {};
    const checks = [
      ['pv', !!(roles.pv_power || roles.pv_energy), roles.pv_power || roles.pv_energy, null],
      ['grid', !!(roles.grid_power || roles.grid_import_energy), roles.grid_power || roles.grid_import_energy, { link: '/config/energy' }],
      ['battery', d.batteries.items.length > 0, this._t('batteries_n', { n: d.batteries.items.length }), { yaml: 'energy_hub:\n  batteries:\n    house:\n      soc: sensor.battery_soc\n      power: sensor.battery_power\n      capacity_kwh: 10\n' }],
      ['forecast', !!roles.forecast_power, roles.forecast_power, { link: '/config/integrations/dashboard/add?domain=forecast_solar' }],
      ['planes', !d.kwp_estimated, d.kwp_estimated ? this._t('kwp_estimated') : this._t('kwp', { v: this._num(d.kwp, 1) }), { yaml: 'energy_hub:\n  planes:\n    - kwp: 3.0\n      tilt: 30\n      azimuth: 180\n' }],
      ['tariff', !!d.finances.net_cost, d.finances.net_cost ? this._eur(d.finances.net_cost, 0) : this._t('no_cost'), { yaml: 'energy_hub:\n  tariff:\n    import: 0.2016\n    export: 0.04\n  installation:\n    cost: 9000\n    subsidy: 0\n    commissioned: 2024-01-01\n' }],
    ];
    const okCount = checks.filter((c) => c[1]).length;
    const action = (a) => (a?.yaml ? this._snip(a.yaml) : a?.link ? `<a class="copy" href="${a.link}" target="_top">${ehIcon('chevron-right', 14)} ${ehEsc(this._t('open'))}</a>` : '');
    let o = `<div class="ringrow"><div class="tile col"><svg width="90" height="90" viewBox="0 0 90 90" role="img" aria-label="${okCount}/${checks.length}"><circle cx="45" cy="45" r="36" fill="none" stroke="var(--divider-color)" stroke-width="8"/><circle cx="45" cy="45" r="36" fill="none" stroke="#639922" stroke-width="8" stroke-linecap="round" transform="rotate(-90 45 45)" stroke-dasharray="${((226 * okCount) / checks.length).toFixed(0)} 227"/><text x="45" y="50" text-anchor="middle" class="svgth">${okCount}/${checks.length}</text></svg><div class="t1">${ehEsc(this._t('health_title'))}</div></div><section class="box">`;
    o += checks.map(([key, ok, detail, act]) => `<div class="check"><span class="pa sm" style="background:${ok ? '#EAF3DE' : '#FAEEDA'};color:${ok ? EH_GREEN : '#854F0B'}">${ehIcon(ok ? 'check' : 'alert-outline', 14)}</span><div class="tt"><div class="a1">${ehEsc(this._t(`checks.${key}`))}</div><div class="t3">${ehEsc(detail || this._t('check_missing'))}</div></div>${ok ? '' : action(act)}</div>`).join('');
    o += '</section></div>';
    o += this._box(this._t('schematic'), this._t('schematic_hint'), `${this._schematic()}${this._nodeDetail()}`);
    const planes = (s.planes || []).map((p, i) => `<tr><td>${ehEsc(this._t('plane_n', { n: i + 1 }))}</td><td>${this._num(p.kwp, 2)} kWp</td><td>${this._num(p.tilt, 0)}°</td><td>${this._num(p.azimuth, 0)}°</td></tr>`).join('');
    o += this._box(this._t('planes'), d.kwp_estimated ? this._t('estimated') : this._t('kwp', { v: this._num(d.kwp, 2) }), `${planes ? `<table class="roles"><tr><th></th><th>${ehEsc(this._t('power'))}</th><th>${ehEsc(this._t('tilt'))}</th><th>${ehEsc(this._t('azimuth'))}</th></tr>${planes}</table>` : `<div class="hint">${ehEsc(this._t('kwp_estimated'))}</div>`}<table class="roles"><tr><td>${ehEsc(this._t('inverter_max_short'))}</td><td>${this._kw(d.inverter_max_kw)}</td></tr><tr><td>${ehEsc(this._t('export_limit'))}</td><td>${d.export_limit_kw ? this._kw(d.export_limit_kw) : '–'}</td></tr></table>`);
    o += this._reference();
    return o;
  }

  _reference() {
    const R = this._data.reference || {};
    const order = [
      ['measured', R.irradiance],
      ['forecast', R.forecast],
      ['weather', R.weather],
      ['clearsky', null],
    ];
    const used = R.source || 'clearsky';
    const rows = order
      .map(([kind, entity]) => {
        const on = kind === used;
        const avail = kind === 'clearsky' || !!entity;
        return `<div class="check"><span class="pa sm" style="background:${on ? '#EAF3DE' : 'var(--secondary-background-color)'};color:${on ? EH_GREEN : 'var(--secondary-text-color)'}">${ehIcon(on ? 'check' : avail ? 'minus' : 'close', 14)}</span><div class="tt"><div class="a1">${ehEsc(this._t(`reference_kind.${kind}`))}</div><div class="t3">${entity ? `<code>${ehEsc(entity)}</code> · ` : ''}${kind === 'clearsky' && !on ? '' : ehEsc(this._t(`reference_hint.${kind}`))}</div></div></div>`;
      })
      .join('');
    return this._box(this._t('reference'), this._t(`reference_kind.${used}`), `${rows}${R.irradiance ? '' : this._snip('energy_hub:\n  entities:\n    irradiance: sensor.solar_radiation\n  weather: weather.home\n')}`);
  }

  _schematic() {
    const d = this._data;
    const L = d.layout || {};
    const items = d.batteries.items;
    const dc = items.filter((b) => b.coupling === 'dc');
    const ac = items.filter((b) => b.coupling !== 'dc');
    const sel = this._node;
    const node = (key, x, y, w, h, title, sub, color, icon) => `<g class="node${sel === key ? ' on' : ''}" data-node="${ehEsc(key)}" tabindex="0" role="button"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="10" fill="var(--card-background-color)" stroke="${color}" stroke-width="${sel === key ? 2.5 : 1.4}"/><circle cx="${x + 20}" cy="${y + h / 2}" r="13" fill="${color}" fill-opacity=".14"/><g transform="translate(${x + 11} ${y + h / 2 - 9}) scale(.75)" style="color:${color}"><path fill="currentColor" d="${EH_ICONS[icon]}"/></g><text class="svgth" x="${x + 40}" y="${y + h / 2 - 3}" style="font-size:12px">${ehEsc(title)}</text><text class="svgt" x="${x + 40}" y="${y + h / 2 + 12}" style="font-size:10px">${ehEsc(sub)}</text></g>`;
    // DC side on the left: the panels and the DC-coupled batteries feed the inverter
    const dcBottom = 110 + Math.max(dc.length, 0) * 62;
    const busY = Math.max(dcBottom, 150) + 10;
    const H = busY + 80;
    let o = `<svg class="schema" viewBox="0 0 680 ${H}" role="img" aria-label="${ehEsc(this._t('schematic'))}">`;
    o += '<path d="M180 49 H250" stroke="#EF9F27" stroke-width="3"/>';
    for (let i = 0; i < dc.length; i++) o += `<path d="M180 ${135 + i * 62} H215 V60 H250" fill="none" stroke="#EF9F27" stroke-width="3"/>`;
    o += '<text class="svgt" x="215" y="42" text-anchor="middle" style="font-size:10px;fill:#BA7517">DC</text>';
    if (L.forecast) o += '<path d="M470 49 H420" fill="none" stroke="var(--secondary-text-color)" stroke-dasharray="3 3"/>';
    // AC side below: AC-coupled batteries, the home and the meter on one bus
    const acRow = ac.map((b) => [`battery:${b.key}`, b.name, `AC · ${this._num(b.capacity_kwh, 1)} kWh`, EH_TEAL, 'battery-charging']);
    acRow.push(['home', this._t('home'), d.roles?.load_power ? this._t('measured_short') : this._t('computed'), EH_GREEN, 'home-lightning-bolt-outline']);
    acRow.push(['meter', L.meter || this._t('grid'), d.export_limit_kw ? this._t('limit_kw', { v: this._kw(d.export_limit_kw) }) : this._t('grid'), EH_BLUE, 'transmission-tower']);
    const w = Math.min(160, (640 - 10 * (acRow.length - 1)) / acRow.length);
    const xs = acRow.map((_r, i) => 20 + i * (w + 10));
    o += `<path d="M335 78 V${busY}" stroke="#378ADD" stroke-width="3"/><path d="M${Math.min(xs[0] + w / 2, 335)} ${busY} H${Math.max(xs[xs.length - 1] + w / 2, 335)}" stroke="#378ADD" stroke-width="3"/><text class="svgt" x="343" y="${busY - 8}" style="font-size:10px;fill:#185FA5">AC</text>`;
    for (const x of xs) o += `<path d="M${x + w / 2} ${busY} V${busY + 20}" stroke="#378ADD" stroke-width="3"/>`;
    o += node('pv', 20, 24, 160, 50, this._t('solar'), `${(L.strings || []).length} strings${L.units ? ` · ${L.units} ${this._t('panels')}` : ''}`, EH_AMBER, 'solar-panel');
    o += node('inverter', 250, 24, 170, 54, L.inverter || this._t('inverter_cap'), `DC → AC · ${this._kw(d.inverter_max_kw)}`, EH_AMBER, 'flash-outline');
    if (L.forecast) o += node('forecast', 470, 24, 190, 50, this._t('forecast'), L.forecast, '#888780', 'weather-cloudy-alert');
    dc.forEach((b, i) => {
      o += node(`battery:${b.key}`, 20, 110 + i * 62, 160, 50, b.name, `DC · ${this._num(b.capacity_kwh, 1)} kWh`, EH_TEAL, 'battery-charging');
    });
    acRow.forEach(([key, t, s2, c, ic], i) => {
      o += node(key, xs[i], busY + 20, w, 50, t, s2, c, ic);
    });
    return `${o}</svg>`;
  }

  _nodeDetail() {
    const key = this._node;
    if (!key) return `<div class="hint">${ehEsc(this._t('schematic_click'))}</div>`;
    const d = this._data;
    const s = this._settings || {};
    const roles = d.roles || {};
    const capIcon = { provided: 'check', estimated: 'function-variant', absent: 'minus' };
    const capsOf = (role) => {
      const src = d.sources.find((x) => x.role === role);
      return src ? Object.entries(src.capabilities).map(([k, v]) => `<span class="cap ${v}">${ehIcon(capIcon[v] || 'minus', 12)}${ehEsc(this._t(`cap.${k}`))}</span>`).join('') : '';
    };
    const ents = (list) => `<table class="roles">${list.filter(([, e]) => e).map(([r, e]) => `<tr><td>${ehEsc(r)}</td><td><code>${ehEsc(e)}</code></td><td class="age">${d.ages?.[e] != null ? `${this._num(d.ages[e], 0)} s` : ''}</td></tr>`).join('')}</table>`;
    let title = '';
    let body = '';
    if (key === 'pv' || key === 'inverter') {
      title = key === 'pv' ? this._t('solar') : d.layout?.inverter || this._t('inverter_cap');
      body = `<div>${capsOf('pv')}</div>${ents([['pv_power', roles.pv_power], ['pv_energy', roles.pv_energy]])}${key === 'pv' ? `<div class="t3">${ehEsc((d.layout?.strings || []).join(' · '))}</div>` : ''}`;
    } else if (key === 'forecast') {
      title = d.layout?.forecast || this._t('forecast');
      body = `<div>${capsOf('forecast')}</div>${ents([['forecast_power', roles.forecast_power], ['forecast_energy_today', roles.forecast_energy_today]])}`;
    } else if (key === 'meter') {
      title = d.layout?.meter || this._t('grid');
      body = `<div>${capsOf('meter')}</div>${ents([['grid_power', roles.grid_power], ['grid_import_energy', roles.grid_import_energy], ['grid_export_energy', roles.grid_export_energy]])}`;
    } else if (key === 'home') {
      title = this._t('home');
      body = roles.load_power ? ents([['load_power', roles.load_power]]) : `<div class="hint">${ehEsc(this._t('home_computed'))}</div>`;
    } else if (key.startsWith('battery:')) {
      const b = d.batteries.items.find((x) => `battery:${x.key}` === key);
      const cfg = (s.batteries || []).find((x) => x.key === b?.key) || {};
      const src = d.sources.find((x) => x.platform === b?.platform);
      title = b ? b.name : '';
      body = `<div>${src ? Object.entries(src.capabilities).map(([k, v]) => `<span class="cap ${v}">${ehIcon(capIcon[v] || 'minus', 12)}${ehEsc(this._t(`cap.${k}`))}</span>`).join('') : ''}</div>${ents([['soc', cfg.soc], ['power', cfg.power]])}<div class="t3">${ehEsc(this._t(`coupling.${b?.coupling}`))} · ${this._num(b?.capacity_kwh, 1)} kWh · ${ehEsc(this._t('reserve', { v: `${this._num(b?.reserve, 0)} %` }))}${cfg.cells ? ` · ${this._t('n_cells', { n: cfg.cells })}` : ''}</div>`;
    }
    return `<div class="nodedetail"><div class="a1">${ehEsc(title)}</div>${body}</div>`;
  }

  _setTariffs() {
    const d = this._data;
    const s = this._settings || {};
    const t = s.tariff || {};
    const inst = s.installation || {};
    const F = d.finances;
    const row = (label, value) => `<tr><td>${ehEsc(label)}</td><td>${value}</td></tr>`;
    const C = F.comparator || {};
    const offerName = (C.offers || []).find((r) => r.key === C.contract)?.name || C.contract;
    const assumed = (flag) => (flag ? ` <span class="pill small">${ehEsc(this._t('assumed'))}</span>` : '');
    const ent = (role) => (d.roles?.[role] ? `<code>${ehEsc(d.roles[role])}</code>` : '–');
    let o = this._box(
      this._t('contract_box'),
      C.contract_source ? this._t(`contract_source.${C.contract_source}`) : '',
      `<table class="roles">${row(this._t('contract'), C.contract ? ehEsc(offerName) : ehEsc(this._t('no_contract')))}${row(this._t('subscribed_power'), `${C.kva ?? '–'} kVA${assumed(C.kva_assumed)}`)}${row(this._t('offpeak_hours'), `${ehEsc(C.offpeak || '–')}${assumed(C.offpeak_assumed)}`)}${row(this._t('price_now'), `${this._eur(F.import_price, 4)} /kWh`)}${row(this._t('price_entity'), ent('tariff_price'))}${row(this._t('color_entity'), ent('tariff_color'))}</table>${this._snip(`energy_hub:\n  tariff:\n    contract: ${C.contract || 'hphc'}\n    kva: ${C.kva || 6}\n    offpeak: "${C.offpeak || '22:00-06:00'}"\n`)}`,
    );
    o += this._box(this._t('tariff_box'), d.currency, `<table class="roles">${C.contract ? '' : row(this._t('import_price'), `${this._eur(t.import ?? F.import_price, 4)} /kWh`)}${row(this._t('export_price'), `${this._eur(t.export ?? F.export_price, 4)} /kWh`)}</table>${this._snip(`energy_hub:\n  tariff:\n    import: ${t.import ?? F.import_price}\n    export: ${t.export ?? F.export_price}\n    currency: ${d.currency}\n`)}`);
    o += this._box(this._t('installation_box'), '', `<table class="roles">${row(this._t('cost'), inst.cost != null ? this._eur(inst.cost, 0) : '–')}${row(this._t('subsidy'), inst.subsidy != null ? this._eur(inst.subsidy, 0) : '–')}${row(this._t('net_cost_label'), F.net_cost != null ? this._eur(F.net_cost, 0) : '–')}${row(this._t('commissioned'), inst.commissioned ? new Date(`${inst.commissioned}T12:00`).toLocaleDateString(this._locale, { day: 'numeric', month: 'long', year: 'numeric' }) : '–')}${row(this._t('inverter_replacement'), `${this._eur(F.inverter_replacement_cost, 0)} · ${this._t('after_years', { v: this._num(F.inverter_lifetime_years, 0) })}`)}</table>${this._snip(`energy_hub:\n  installation:\n    cost: ${inst.cost ?? 9000}\n    subsidy: ${inst.subsidy ?? 0}\n    commissioned: ${inst.commissioned ?? '2024-01-01'}\n`)}`);
    return o + `<div class="hint">${ehEsc(this._t('yaml_wins'))}</div>`;
  }

  _setAlerts() {
    const d = this._data;
    const s = this._settings || {};
    const active = new Set(d.alerts.map((a) => a.kind));
    const kinds = ['clipping', 'string_lagging', 'shading', 'soiling', 'cell_drift', 'battery_exchange', 'stale'];
    const rows = kinds.map((k) => `<div class="check"><span class="pa sm" style="background:${active.has(k) ? '#FCEBEB' : '#EAF3DE'};color:${active.has(k) ? '#A32D2D' : EH_GREEN}">${ehIcon(active.has(k) ? 'alert-outline' : 'check', 14)}</span><div class="tt"><div class="a1">${ehEsc(this._t(`alert_kind.${k}`))}</div><div class="t3">${ehEsc(this._t(`alert_rule.${k}`))}</div></div><span class="status" style="background:${active.has(k) ? '#FCEBEB' : 'var(--secondary-background-color)'};color:${active.has(k) ? '#A32D2D' : 'var(--secondary-text-color)'}">${ehEsc(this._t(active.has(k) ? 'active' : 'inactive'))}</span></div>`).join('');
    let o = this._box(this._t('alert_rules'), this._t('active_n', { n: active.size }), rows);
    o += this._box(this._t('notifications'), '', `<table class="roles"><tr><td>${ehEsc(this._t('notify_target'))}</td><td>${s.notify ? `<code>${ehEsc(s.notify)}</code>${s.notify_auto ? ` <span class="pill small">${ehEsc(this._t('detected'))}</span>` : ''}` : ehEsc(this._t('no_notify'))}</td></tr><tr><td>${ehEsc(this._t('event_name'))}</td><td><code>energy_hub_alert</code></td></tr><tr><td>${ehEsc(this._t('frequency'))}</td><td>${ehEsc(this._t('once_a_day'))}</td></tr></table>${s.notify ? '' : this._snip('energy_hub:\n  notify: notify.mobile_app_phone\n')}`);
    return o;
  }

  _setYaml() {
    const s = this._settings;
    if (!s?.yaml) return `<div class="hint">${ehEsc(this._t('loading'))}</div>`;
    return this._box(this._t('yaml'), s.yaml_configured ? this._t('yaml_in_use') : this._t('yaml_detected'), `${this._snip(s.yaml)}<pre>${ehEsc(s.yaml)}</pre>`);
  }

  // ---------- render
  _render() {
    if (!this.shadowRoot) return;
    let body;
    if (this._error) body = `<div class="empty">${ehEsc(this._t('not_loaded'))}<br><small>${ehEsc(this._error)}</small></div>`;
    else if (!this._data) body = `<div class="empty">${ehEsc(this._t('loading'))}</div>`;
    else {
      const content = { overview: this._overview, production: this._production, batteries: this._batteries, losses: this._losses, finances: this._finances, settings: this._settingsTab }[this._tab] || this._overview;
      body = `${this._header()}<main>${content.call(this)}</main>`;
    }
    const scroll = this.shadowRoot.querySelector('.scroll');
    const top = scroll?.scrollTop || 0;
    this.shadowRoot.innerHTML = `<style>${EH_CSS}</style><div class="scroll ${this._narrow ? 'narrow' : ''}">${body}</div>`;
    const sc = this.shadowRoot.querySelector('.scroll');
    sc.scrollTop = top;
    sc.addEventListener('scroll', () => {
      const c = sc.scrollTop > 24;
      if (c !== this._collapsed) {
        this._collapsed = c;
        this.shadowRoot.querySelector('.banner')?.classList.toggle('collapsed', c);
      }
    }, { passive: true });
    this._bind();
  }

  _bind() {
    const root = this.shadowRoot;
    for (const el of root.querySelectorAll('[data-tab]')) el.addEventListener('click', () => this._setTab(el.dataset.tab));
    for (const el of root.querySelectorAll('[data-battery]')) {
      el.addEventListener('click', () => {
        this._battery = el.dataset.battery;
        this._cell = null;
        this._render();
      });
    }
    for (const el of root.querySelectorAll('[data-cell]')) {
      el.addEventListener('click', () => {
        this._cell = Number(el.dataset.cell);
        this._render();
      });
    }
    for (const el of root.querySelectorAll('[data-cellmetric]')) {
      el.addEventListener('click', () => {
        this._cellMetric = el.dataset.cellmetric;
        this._render();
      });
    }
    for (const el of root.querySelectorAll('[data-period]')) {
      el.addEventListener('click', () => {
        this._period = el.dataset.period;
        this._render();
      });
    }
    for (const el of root.querySelectorAll('[data-sub]')) {
      el.addEventListener('click', () => {
        this._sub = el.dataset.sub;
        this._render();
      });
    }
    for (const el of root.querySelectorAll('[data-node]')) {
      const pick = () => {
        this._node = this._node === el.dataset.node ? null : el.dataset.node;
        this._render();
      };
      el.addEventListener('click', pick);
      el.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') pick();
      });
    }
    for (const el of root.querySelectorAll('[data-snip]')) {
      el.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(this._snips[Number(el.dataset.snip)]);
          el.textContent = this._t('copied');
        } catch (_err) {
          // clipboard unavailable (http)
        }
      });
    }
    root.querySelector('[data-rate]')?.addEventListener('input', (e) => {
      this._rate = Number(e.target.value);
      this._render();
    });
    for (const el of root.querySelectorAll('[data-action="refresh"]')) el.addEventListener('click', async () => {
      try {
        this._data = await this._hass.callWS({ type: 'energy_hub/snapshot' });
        this._render();
      } catch (_err) {
        // kept as is
      }
    });
    root.querySelector('[data-action="menu"]')?.addEventListener('click', () => this.dispatchEvent(new Event('hass-toggle-menu', { bubbles: true, composed: true })));
    this._bindCurve();
  }

  _bindCurve() {
    const svg = this.shadowRoot.querySelector('svg.curve');
    const meta = this._curveMeta;
    if (!svg || !meta) return;
    const hit = svg.querySelector('.hit');
    const hov = svg.querySelector('.hov');
    const tip = this.shadowRoot.querySelector('.tip');
    hit.addEventListener('mousemove', (ev) => {
      const r = svg.getBoundingClientRect();
      const sx = ((ev.clientX - r.left) * 680) / r.width;
      const t = meta.t0 + ((sx - meta.x0) / (meta.x1 - meta.x0)) * (meta.t1 - meta.t0);
      let best = null;
      for (const row of meta.rows) if (!best || Math.abs(row.t - t) < Math.abs(best.t - t)) best = row;
      if (!best) return;
      const x = meta.x0 + ((best.t - meta.t0) / (meta.t1 - meta.t0)) * (meta.x1 - meta.x0);
      hov.setAttribute('x1', x);
      hov.setAttribute('x2', x);
      hov.style.display = '';
      const clipped = this._data.inverter_max_kw && best.exp != null && best.pv != null && best.exp > this._data.inverter_max_kw && best.pv >= 0.97 * this._data.inverter_max_kw;
      tip.innerHTML = `<b>${this._time(best.t)}</b><br>${ehEsc(this._t('production'))} ${this._kw(best.pv)}<br>${ehEsc(this._t('forecast'))} ${this._kw(best.exp)}<br>${ehEsc(this._t('consumption'))} ${this._kw(best.load)}${best.soc != null ? `<br>${ehEsc(this._t('battery'))} ${this._num(best.soc, 0)} %` : ''}${clipped ? `<br><span style="color:${EH_RED}">${ehEsc(this._t('clipped', { v: this._kw(best.exp - best.pv) }))}</span>` : ''}`;
      tip.style.display = 'block';
      const px = (x * r.width) / 680;
      tip.style.left = `${px > r.width / 2 ? px - tip.offsetWidth - 10 : px + 10}px`;
    });
    hit.addEventListener('mouseleave', () => {
      hov.style.display = 'none';
      tip.style.display = 'none';
    });
  }
}
