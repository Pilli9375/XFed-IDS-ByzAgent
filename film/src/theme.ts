// Tokens from site/src/styles.css :root (see docs/style_guide.md §1). No other colours.
export const C = {
  cream: '#F6F0E4',
  sand: '#ECE3D1',
  line: '#DCD0BA',
  cocoa: '#2B211C',
  cocoa2: '#1F1814',
  inkSoft: '#4A3D35',
  muted: '#6E6157',
  plum: '#3A285C',
  terracotta: '#A85F3F',
  terracottaText: '#8F4E31',
  terracottaLight: '#D98A68',
  brass: '#C19A52',
  olive: '#8E9A4F',
  blush: '#F3D9CC',
  darkLine: '#45382F',
  darkMuted: '#ADA192',
  darkFaint: '#7D7064',
  darkText: '#D9CFBF',
  darkWell: '#3A2E27',
} as const;

export const F = {
  disp: "'Brygada 1918'",
  body: "'Schibsted Grotesk'",
  mono: "'Atkinson Hyperlegible Mono'",
  note: "'Alegreya'",
  greek: "'Alegreya Greek'",
} as const;

// Pie order and colours from StoryDiagram.jsx: Benign, DoS, DDoS, PortScan, other attacks.
export const PIE = [C.line, C.plum, C.terracotta, C.brass, C.olive];
// Trust grid states (site .cell.v0/.v1/.v2): trust, downweight, quarantine.
export const STATE = [C.olive, C.brass, C.terracottaLight];
