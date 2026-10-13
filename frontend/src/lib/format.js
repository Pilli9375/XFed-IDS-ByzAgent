// Display formatting only. Every value passed in comes from an endpoint.
const MINUS = '−';

export function fixed(v, d = 3) {
  if (v == null || Number.isNaN(v)) return '—';
  const s = Math.abs(v).toFixed(d);
  return v < 0 && Number(s) !== 0 ? MINUS + s : s;
}

export function signed(v, d = 3) {
  if (v == null || Number.isNaN(v)) return '—';
  const s = Math.abs(v).toFixed(d);
  if (Number(s) === 0) return s;
  return (v < 0 ? MINUS : '+') + s;
}

export function pct(v, d = 1) {
  return `${fixed(v * 100, d)}%`;
}

export function int(v) {
  return Math.round(v).toLocaleString('en-US');
}

export function meanSd(m, s, d = 3) {
  return `${fixed(m, d)} ± ${fixed(s, d)}`;
}

export function timeOf(iso) {
  return new Date(iso).toLocaleTimeString('en-GB', { hour12: false });
}

export const ALPHAS = ['0.1', '0.5', '5.0'];
