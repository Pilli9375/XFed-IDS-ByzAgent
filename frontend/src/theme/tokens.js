/**
 * Design tokens, ported 1:1 from app_lib/theme.py. This file is the single
 * source of truth for color/spacing/font values -- theme.css turns the
 * colors into CSS custom properties, and chart code (Recharts) imports
 * these directly since SVG fill/stroke attributes need real color strings,
 * not var() lookups, to be safe across renderers.
 *
 * Keep values byte-for-byte identical to theme.py. This is a translation,
 * not a redesign.
 */

export const BG = '#0d1117';
export const SURFACE = '#151b23';
export const SURFACE_HI = '#1c232c';
export const BORDER = '#2a323d';
export const BORDER_HI = '#3a4553';

export const TEXT = '#e6edf3';
export const TEXT_MUTED = '#8b98a5';
export const TEXT_FAINT = '#6b7681';

export const ACCENT = '#4cc9f0';
export const ACCENT_DIM = '#2a7f9e';
export const ALERT = '#f2726f';
export const WARN = '#e8b339';
export const POSITIVE = '#5bc0a0';
export const VIOLET = '#a78bfa';

// Chart series palette -- colorblind-safer than a rainbow, holds up when a
// projector crushes saturation.
export const SERIES = [ACCENT, VIOLET, POSITIVE, WARN, ALERT, '#7aa2f7', '#e08fc4', '#9ca7b3'];

// Semantic color per attack family. Benign reads calm; attack families get
// distinct hues so the same family is the same color everywhere in the app.
export const FAMILY_COLORS = {
  Benign: POSITIVE,
  Bot: VIOLET,
  BruteForce: WARN,
  DDoS: ALERT,
  DoS: '#e0895f',
  Heartbleed: '#d16ba5',
  Infiltration: '#c77dff',
  PortScan: ACCENT,
  WebAttack: '#7aa2f7',
};

export function familyColor(name) {
  return FAMILY_COLORS[name] ?? TEXT_MUTED;
}

export const FONT_STACK =
  '"Segoe UI Variable Display", "Segoe UI Variable", "Segoe UI", ' +
  '-apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif';
export const MONO_STACK =
  '"Cascadia Code", "JetBrains Mono", Consolas, "SF Mono", Menlo, monospace';

// Spacing scale -- 4px base.
export const SP = { xs: '0.25rem', sm: '0.5rem', md: '1rem', lg: '1.5rem', xl: '2.25rem', '2xl': '3.5rem' };

// --- Client Trust Monitor (Contribution B / ByzAgent) -----------------------
// Decision severity: 0=trust, 1=downweight, 2=quarantine.
export const DECISION_COLORS = { 0: POSITIVE, 1: WARN, 2: ALERT };
export const DECISION_NAME_BY_SEVERITY = { 0: 'trust', 1: 'downweight', 2: 'quarantine' };

// Section nav icons -- same 20x20 viewBox path data as theme.py's NAV_ICONS.
// Rendered as real inline <svg> here (React can put HTML/SVG in a nav label;
// theme.py had to fake this with CSS mask pseudo-elements because Streamlit
// radio labels can't render markup).
export const NAV_ICONS = {
  'Federation Status': 'M3 3h6v6H3zM11 3h6v6h-6zM3 11h6v6H3zM11 11h6v6h-6z',
  Detect: 'M10 2a8 8 0 105.3 14l3.4 3.4 1.4-1.4-3.4-3.4A8 8 0 0010 2zm0 2a6 6 0 110 12 6 6 0 010-12z',
  Explain: 'M3 17h3V9H3v8zm5.5 0h3V3h-3v14zm5.5 0h3v-6h-3v6z',
  'Explanation Agreement': 'M3 15l4-5 3 3 4-6 3 4v3H3z M3 4h14v1.5H3z',
  Faithfulness:
    'M10 2l7 3v5c0 4.4-3 8.3-7 9-4-0.7-7-4.6-7-9V5l7-3zm0 2.2L5 6.3V10c0 3.3 2.1 6.3 5 7 2.9-0.7 5-3.7 5-7V6.3l-5-2.1z',
  'Methods & Limits':
    'M10 2a8 8 0 100 16 8 8 0 000-16zm0 3.2a1.2 1.2 0 110 2.4 1.2 1.2 0 010-2.4zM9 9h2v6H9V9z',
  'Client Trust Monitor':
    'M3 4h11v2H3V4zm0 5h8v2H3V9zm0 5h5v2H3v-2zm13-6l1.4 1.4L13 13.8l-2.4-2.4L12 10l1 1 3-3z',
};
