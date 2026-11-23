// Energy Hub's sidebar badge, loaded on every page: the number of alerts (clipping, a lagging string, recurring
// shading, soiling, a drifting cell, a source not updating…) on the panel's sidebar item, red when one of them is an
// error and amber otherwise. The count is the state of the integration's alerts sensor, which Home Assistant keeps up
// to date; the badge follows it. The last value is kept by the browser, so the sidebar shows it at once.
var ENERGY_HUB_COUNT_KEY = 'energy-hub-count';
var ENERGY_HUB_EVERY_MS = 15000;
// Red when one alert is an error (clipping, a source not updating…), amber for warnings only; the text is white.
var ENERGY_HUB_ERROR_COLOR = 'var(--error-color, #db4437)';
var ENERGY_HUB_WARNING_COLOR = 'var(--warning-color, #ffa600)';
var ENERGY_HUB_LEVEL_KEY = 'energy-hub-level';

function energyHubBadgeSaved() {
  try {
    var n = parseInt(localStorage.getItem(ENERGY_HUB_COUNT_KEY), 10);
    return Number.isFinite(n) && n > 0 ? n : 0;
  } catch (_err) {
    return 0;
  }
}
window.__energyHubBadgeCount ??= energyHubBadgeSaved();
try {
  window.__energyHubBadgeLevel ??= localStorage.getItem(ENERGY_HUB_LEVEL_KEY) || 'warning';
} catch (_err) {
  window.__energyHubBadgeLevel ??= 'warning';
}

function energyHubColor() {
  return window.__energyHubBadgeLevel === 'error' ? ENERGY_HUB_ERROR_COLOR : ENERGY_HUB_WARNING_COLOR;
}

// The Energy Hub item in Home Assistant's sidebar, or null until the sidebar is drawn. The recent sidebar gives each
// item the id `sidebar-panel-<path>` and sets its href as a property (not an attribute), so the id is the reliable
// hook; `[href]` and `[data-panel]` catch the older sidebars (an <a> wrapping a paper-icon-item).
function energyHubSidebarItem() {
  var ha = document.querySelector('home-assistant')?.shadowRoot;
  var sidebar = ha?.querySelector('home-assistant-main')?.shadowRoot?.querySelector('ha-sidebar')?.shadowRoot;
  if (!sidebar) return null;
  return (
    sidebar.querySelector('#sidebar-panel-energy-hub') ||
    sidebar.querySelector('[href="/energy-hub"]') ||
    sidebar.querySelector('[data-panel="energy-hub"]')
  );
}

// One badge span, styled as Home Assistant's own sidebar badge (class `badge`, so the sidebar's CSS places it and
// shows or hides it by slot and expanded state) but in the accent colour instead of the default.
function energyHubBadgeSpan(text, slot, key) {
  var el = document.createElement('span');
  el.className = 'badge energy-hub-badge';
  el.slot = slot;
  el.dataset.key = key;
  el.textContent = text;
  // The start badge (shown collapsed, over the icon) is placed by Home Assistant's `ha-svg-icon + .badge` rule — but a
  // custom panel's sidebar icon is an <ha-icon>, not a bare <ha-svg-icon>, so that rule does not match and the badge
  // would sit in the start slot, beside the icon. Position it ourselves (over the icon, like Home Assistant's own: top
  // var(--ha-space-1), left 26px) so it never affects the row's layout; the end badge stays in flow at the trailing
  // edge. The host's expanded/collapsed opacity rules still show the right one by slot.
  var place = slot === 'start' ? 'position:absolute; top:var(--ha-space-1, 4px); left:26px; z-index:1; pointer-events:none; ' : '';
  el.style.cssText = `${place}display:inline-flex; justify-content:center; min-width:18px; height:18px; box-sizing:border-box; padding:0 5px; align-items:center; border-radius:9px; font-size:11px; font-weight:500; line-height:1; color:#fff; background:${energyHubColor()};`;
  return el;
}

// The badge on the sidebar item: the number of alerts, like the notifications count; none when there is
// nothing. On the recent sidebar (ha-list-item-button / ha-md-list-item) it mirrors Home Assistant's own badge — a
// span in the start slot (shown when the sidebar is collapsed, over the icon) and one in the end slot (shown when
// expanded) — so the sidebar's CSS handles the placement and the collapsed/expanded switch. On the older sidebar (an
// <a>) a single span is placed at the right. Redrawn when Home Assistant rebuilds its items; unchanged, it writes
// nothing (so the observer below does not loop).
function energyHubBadgeRedraw() {
  var item = energyHubSidebarItem();
  if (!item) return false;
  var count = window.__energyHubBadgeCount;
  var spans = item.querySelectorAll(':scope > .energy-hub-badge');
  if (!count) {
    for (var b of spans) b.remove();
    return true;
  }
  var text = count > 99 ? '99+' : String(count);
  var key = `${text}-${window.__energyHubBadgeLevel}`;
  if (item.localName === 'a') {
    var badge = spans[0];
    if (badge && badge.dataset.key === key) return true;
    if (!badge) {
      badge = document.createElement('span');
      badge.className = 'energy-hub-badge';
      item.style.position = 'relative';
      item.appendChild(badge);
    }
    badge.dataset.key = key;
    badge.textContent = text;
    badge.style.cssText = `position:absolute; right:12px; top:50%; transform:translateY(-50%); min-width:18px; height:18px; box-sizing:border-box; padding:0 5px; display:inline-flex; align-items:center; justify-content:center; border-radius:9px; font-size:11px; font-weight:500; line-height:1; pointer-events:none; z-index:1; color:#fff; background:${energyHubColor()};`;
    return true;
  }
  if (spans.length === 2 && spans[0].dataset.key === key) return true;
  for (var old of spans) old.remove();
  // The start badge goes right after the icon, so the sidebar's `ha-svg-icon + .badge` rule places it over the icon.
  var icon = item.querySelector(':scope > ha-svg-icon[slot="start"]') || item.querySelector(':scope > ha-icon[slot="start"]');
  var start = energyHubBadgeSpan(text, 'start', key);
  if (icon) item.insertBefore(start, icon.nextSibling);
  else item.appendChild(start);
  item.appendChild(energyHubBadgeSpan(text, 'end', key));
  return true;
}

// Until the sidebar has drawn the item (it may come after this module): every 250 ms for 5 seconds
function energyHubBadgeRedrawSoon(tries = 20) {
  if (energyHubBadgeRedraw() || tries <= 1) return;
  setTimeout(() => energyHubBadgeRedrawSoon(tries - 1), 250);
}

// The sidebar rebuilds its items (opened, folded, panels changed): the badge is added again when it is dropped
function energyHubBadgeObserve() {
  var item = energyHubSidebarItem();
  var sidebar = item?.getRootNode();
  if (!sidebar) {
    setTimeout(energyHubBadgeObserve, 500);
    return;
  }
  if (sidebar.__energyHubBadgeObserved) return;
  sidebar.__energyHubBadgeObserved = true;
  new MutationObserver(() => {
    if (window.__energyHubBadgeRaf) return;
    window.__energyHubBadgeRaf = requestAnimationFrame(() => {
      window.__energyHubBadgeRaf = 0;
      energyHubBadgeRedraw();
    });
  }).observe(sidebar, { childList: true, subtree: true });
}

// The count and its level: the badge drawn again when they change, kept for the next page
function energyHubSetBadge(count, level) {
  count = Math.max(0, parseInt(count, 10) || 0);
  if (window.__energyHubBadgeCount === count && window.__energyHubBadgeLevel === level) return;
  window.__energyHubBadgeCount = count;
  window.__energyHubBadgeLevel = level;
  try {
    localStorage.setItem(ENERGY_HUB_COUNT_KEY, String(count));
    localStorage.setItem(ENERGY_HUB_LEVEL_KEY, level);
  } catch (_err) {
    // drawn anyway, not kept
  }
  energyHubBadgeRedraw();
}

// The alerts: the Energy Hub alerts sensor, found by its `alerts` attribute (a list) and its platform when the
// registry is loaded. Its state is the number of alerts; the list gives their severity.
function energyHubCount(hass) {
  var states = hass?.states;
  if (!states) return [0, 'warning'];
  for (var id in states) {
    if (!id.startsWith('sensor.')) continue;
    var alerts = states[id]?.attributes?.alerts;
    if (!Array.isArray(alerts)) continue;
    if (hass.entities?.[id] && hass.entities[id].platform !== 'energy_hub') continue;
    return [alerts.length, alerts.some((a) => a?.severity === 'error') ? 'error' : 'warning'];
  }
  return [0, 'warning'];
}

// The alerts read from the sensor, reported for the sidebar badge
function energyHubFollow() {
  var hass = document.querySelector('home-assistant')?.hass;
  if (!hass?.user?.is_admin || document.hidden) return;
  energyHubSetBadge(...energyHubCount(hass));
}

if (!window.__energyHubBadge_init) {
  window.__energyHubBadge_init = true;
  energyHubBadgeRedrawSoon();
  energyHubBadgeObserve();
  // The alerts read a few seconds after the page, once Home Assistant has drawn it, then every 15 seconds
  setTimeout(energyHubFollow, 3000);
  setInterval(energyHubFollow, ENERGY_HUB_EVERY_MS);
}
