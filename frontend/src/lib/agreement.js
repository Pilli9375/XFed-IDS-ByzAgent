// Client-side port of app_lib/loaders.py's agreement aggregations
// (get_headline_agreement / get_per_seed_agreement / get_instability_floor_summary).
// GET /agreement serves the raw row-level CSVs (agreement_metrics.csv,
// centralized_instability_floor.csv, ...), never pre-aggregated -- the
// grouping/median/IQR math the Python loaders do server-side at import time
// happens here instead, over the same rows, with the same filter
// (family_eligible only) and the same quantile method.

import { medianSorted, quantileSorted, sortedNums } from './stats';

// Stated in the project's own locked headline numbers; no separate artifact
// file was found holding this value in isolation -- ported verbatim from
// loaders.py's own comment on this constant.
export const CHANCE_LEVEL_JACCARD_AT_10 = 0.065;

function groupBy(rows, keyFn) {
  const map = new Map();
  for (const row of rows) {
    const k = keyFn(row);
    if (!map.has(k)) map.set(k, []);
    map.get(k).push(row);
  }
  return map;
}

/**
 * Median jaccard@10 / weighted tau per alpha, family_eligible rows only.
 * Mirrors loaders.get_headline_agreement().
 */
export function computeHeadlineAgreement(agreementMetrics) {
  const eligible = agreementMetrics.filter((r) => r.family_eligible);
  const groups = groupBy(eligible, (r) => r.alpha);
  const out = [...groups.entries()].map(([alpha, rows]) => {
    const jac = sortedNums(rows.map((r) => r.jaccard_at_10));
    const tau = sortedNums(rows.map((r) => r.kendall_weighted_tau));
    return {
      alpha: Number(alpha),
      jaccard_at_10_median: medianSorted(jac),
      jaccard_at_10_q25: quantileSorted(jac, 0.25),
      jaccard_at_10_q75: quantileSorted(jac, 0.75),
      tau_median: medianSorted(tau),
      tau_q25: quantileSorted(tau, 0.25),
      tau_q75: quantileSorted(tau, 0.75),
      n_rows: rows.length,
    };
  });
  out.sort((a, b) => a.alpha - b.alpha);
  return out;
}

/**
 * Same headline metrics broken out per seed. Mirrors
 * loaders.get_per_seed_agreement().
 */
export function computePerSeedAgreement(agreementMetrics) {
  const eligible = agreementMetrics.filter((r) => r.family_eligible);
  const groups = groupBy(eligible, (r) => `${r.alpha}|${r.seed}`);
  const out = [...groups.values()].map((rows) => {
    const jac = sortedNums(rows.map((r) => r.jaccard_at_10));
    const tau = sortedNums(rows.map((r) => r.kendall_weighted_tau));
    return {
      alpha: Number(rows[0].alpha),
      seed: rows[0].seed,
      jaccard_at_10_median: medianSorted(jac),
      tau_median: medianSorted(tau),
      n_rows: rows.length,
    };
  });
  out.sort((a, b) => a.alpha - b.alpha || a.seed - b.seed);
  return out;
}

/**
 * Median jaccard@10 / weighted tau per (alpha, family), eligible rows only.
 * Mirrors loaders.get_per_family_agreement() -- same family_eligible filter
 * and grouping as computeHeadlineAgreement/computePerSeedAgreement above,
 * already flagged and verified in Step 2; this is the same computation
 * grouped a different way, not a new reimplementation.
 */
export function computePerFamilyAgreement(agreementMetrics) {
  const eligible = agreementMetrics.filter((r) => r.family_eligible);
  const groups = groupBy(eligible, (r) => `${r.alpha}|${r.family}`);
  const out = [...groups.values()].map((rows) => {
    const jac = sortedNums(rows.map((r) => r.jaccard_at_10));
    const tau = sortedNums(rows.map((r) => r.kendall_weighted_tau));
    return {
      alpha: Number(rows[0].alpha),
      family: rows[0].family,
      jaccard_at_10_median: medianSorted(jac),
      tau_median: medianSorted(tau),
      n_rows: rows.length,
    };
  });
  out.sort((a, b) => a.alpha - b.alpha || a.family.localeCompare(b.family));
  return out;
}

/**
 * Pairwise SHAP agreement between the 3 centralized seeds -- the null
 * federated agreement gets compared against. Mirrors
 * loaders.get_instability_floor_summary(). Returns null when the artifact
 * has no rows (mirrors the Python loader returning None).
 */
export function computeInstabilityFloorSummary(floorRows) {
  if (!floorRows || floorRows.length === 0) return null;
  const jac = sortedNums(floorRows.map((r) => r.jaccard_at_10));
  const tau = sortedNums(floorRows.map((r) => r.kendall_weighted_tau));
  return {
    jaccard_at_10_median: medianSorted(jac),
    jaccard_at_10_q25: quantileSorted(jac, 0.25),
    jaccard_at_10_q75: quantileSorted(jac, 0.75),
    tau_median: medianSorted(tau),
    tau_q25: quantileSorted(tau, 0.25),
    tau_q75: quantileSorted(tau, 0.75),
    n_rows: floorRows.length,
  };
}

/**
 * Reshapes headline + per-seed rows into what AgreementVsAlphaChart needs:
 * chartData (one point per alpha, x = its index for the line/ribbon) and
 * scatterData (one point per (alpha, seed), x = that alpha's index so every
 * seed's dot sits at the same x as the line -- mirrors plots.py's
 * `xa = alphas.index(a)`). `prefix` is 'jaccard_at_10' or 'tau', matching
 * the field-name prefix headline/per-seed rows already use.
 */
export function shapeAgreementSeries(headline, perSeed, prefix) {
  const chartData = headline.map((h, i) => {
    const q25 = h[`${prefix}_q25`];
    const q75 = h[`${prefix}_q75`];
    return {
      x: i,
      median: h[`${prefix}_median`],
      q25,
      q75,
      iqrRange: q75 - q25,
    };
  });
  const alphaIndex = new Map(headline.map((h, i) => [h.alpha, i]));
  const scatterData = perSeed
    .filter((p) => alphaIndex.has(p.alpha))
    .map((p) => ({
      x: alphaIndex.get(p.alpha),
      y: p[`${prefix}_median`],
      seed: p.seed,
    }));
  return { chartData, scatterData };
}

// Matches Python's f"{a:g}" for the alpha values this project uses
// (0.1, 0.5, 5.0) -- JS Number#toString() already drops the trailing
// ".0" the same way %g does.
export function formatAlpha(alpha) {
  return `α=${alpha}`;
}

export function fmt3(value) {
  return value.toFixed(3);
}
