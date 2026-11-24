// ── Colours and helpers ──────────────────────────────────────────────────────
import { EH_ICONS } from "./core.js";

export const EH_AMBER = '#BA7517';
export const EH_GREEN = '#3B6D11';
export const EH_TEAL = '#1D9E75';
export const EH_BLUE = '#378ADD';
export const EH_RED = '#E24B4A';
export const EH_VIOLET = '#7F77DD';

export function ehEsc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

// Round axis ticks under ``max``: steps of 1, 2 or 5 × 10^n, about five of them
export function ehTicks(max) {
  const raw = max / 5;
  const mag = 10 ** Math.floor(Math.log10(raw || 1));
  const step = [1, 2, 5, 10].map((k) => k * mag).find((k) => k >= raw) || mag;
  const out = [];
  for (let v = 0; v <= max + 1e-9; v += step) out.push(Math.round(v * 1000) / 1000);
  return out;
}

export function ehIcon(name, size = 18) {
  const path = EH_ICONS[name] || EH_ICONS['information-outline'];
  return `<svg class="ic" width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="${path}"/></svg>`;
}
