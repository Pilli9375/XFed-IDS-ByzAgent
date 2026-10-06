// Display-only formatting. Precision follows the docs: 3 decimals for metrics,
// 2 for flag rates, 1 for percentage points. Nothing here changes a stored value.

const MINUS = '−';

export const f3 = (x) => x.toFixed(3);
export const f2 = (x) => x.toFixed(2);
export const pct1 = (x) => (x * 100).toFixed(1);

// Signed percentage points, e.g. -22.7266 -> "−22.7pp".
export const pp = (x) => (x < 0 ? MINUS : '+') + Math.abs(x).toFixed(1) + 'pp';

// A rate shown as a whole percent only when it is exactly whole (0 -> "0%", 0.4 -> "40%");
// otherwise one decimal, so nothing is silently rounded to a cleaner figure.
export const pctWhole = (x) => {
  const v = x * 100;
  return (Math.abs(v - Math.round(v)) < 1e-9 ? String(Math.round(v)) : v.toFixed(1)) + '%';
};

// Model confidence: truncated (never rounded up) to 4 decimals, as in the design reference,
// so 0.99999964 reads 0.9999 and not 1.0000.
export const conf4 = (x) => (Math.floor(x * 10000) / 10000).toFixed(4);

export const signed2 = (x) => (x >= 0 ? '+' : MINUS) + Math.abs(x).toFixed(2);

export const int = (n) => n.toLocaleString('en-US');
export const pad3 = (n) => String(n).padStart(3, '0');

// "0, 3 and 5"
export const andList = (xs) => (xs.length < 2 ? xs.join('') : xs.slice(0, -1).join(', ') + ' and ' + xs[xs.length - 1]);

export const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
