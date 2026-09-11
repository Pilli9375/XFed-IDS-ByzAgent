// Median/quantile matching pandas' default (numpy 'linear' interpolation)
// behavior -- the same aggregation get_headline_agreement() etc. use in
// app_lib/loaders.py, just computed client-side over the raw records
// GET /agreement serves instead of a precomputed CSV.

export function quantileSorted(sorted, q) {
  const n = sorted.length;
  if (n === 0) return NaN;
  if (n === 1) return sorted[0];
  const h = (n - 1) * q;
  const lo = Math.floor(h);
  const hi = Math.ceil(h);
  if (lo === hi) return sorted[lo];
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (h - lo);
}

export function medianSorted(sorted) {
  return quantileSorted(sorted, 0.5);
}

export function sortedNums(values) {
  return [...values].sort((a, b) => a - b);
}
