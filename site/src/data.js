// Every number on the page comes from here: build-time slices of site/public/data/*.json
// (vite.config.js -> virtual:showcase-data) plus the two large files fetched at runtime
// (loadLarge). Values are selected and aggregated (sums, counts, medians) for display,
// never rounded or edited; rounding happens only in format.js at render time.

import { headline, agreement, ci, story, baselines, byzMeta, replayMeta } from 'virtual:showcase-data';
import { SRC, pick, ghUrl, filePart } from './sources.js';

const LISTS = {
  headline: headline.source,
  agreement: agreement.source,
  ci: ci.source,
  story: story.source,
  baselines: baselines.source,
  byz: byzMeta.source,
  replay: replayMeta.source,
};

// GitHub URL for a displayed number, resolved against its JSON's own source list.
export const src = (key) => {
  const [list, match] = SRC[key];
  return ghUrl(pick(LISTS[list], match));
};
// For values whose source file is itself named in the data (run files, attack configs).
export const srcByz = (path) => ghUrl(pick(byzMeta.source, filePart(path)));
// The attack log behind is_malicious / flip_fraction for one seed's attack run. flip_log.csv is
// git-ignored, so the link goes to the tracked attack_config.json of the same attack.
export const srcAttack = (seed, attack) => {
  const hit = byzMeta.source.find((s) => s.endsWith('/attack_config.json') && s.includes(`_s${seed}_f${attack.f}_${attack.mode}_`));
  if (!hit) throw new Error(`no attack_config.json in byzagent sources for seed ${seed}`);
  return ghUrl(hit);
};

const ALPHAS = ['5.0', '0.5', '0.1'];
const strategy = (name) => baselines.strategies.find((s) => s.strategy === name);

// ---- story (N-00) -------------------------------------------------------------
const OTHER = ['Bot', 'BruteForce', 'Heartbleed', 'Infiltration', 'WebAttack'];
const compRows = story.composition.rows;
// [total, Benign, DoS, DDoS, PortScan, other] per org — the reference's pie order.
const comp = compRows.map((r) => [r.TOTAL, r.Benign, r.DoS, r.DDoS, r.PortScan, OTHER.reduce((s, k) => s + r[k], 0)]);
const jac = story.per_silo_agreement.rows.map((r) => r.jaccard_at_10);
const jsorted = jac.slice().sort((x, y) => x - y);
const mid = jsorted.length / 2;
const featuredCall = byzMeta.story.decisions.find((x) => x.round === byzMeta.story.featured_round);
const storyAlpha = story.pointers.macro_f1.alpha;

const LOW_JACCARD = 0.4; // design reference: orgs below this are called out in step 5 and drawn terracotta

export const d = {
  // hero / marquee / system
  flows: headline.dataset.flows_after_cleaning,
  nOrgs: headline.dataset.n_organizations,
  nClasses: headline.dataset.n_traffic_classes,
  nAttackFamilies: Object.keys(headline.dataset.family_counts_post_clean).filter((k) => k !== 'Benign').length,
  centralF1: headline.centralized_mlp_macro_f1_headline.mean,
  servedSeed: headline.served_demo_model.seed,
  served: { tag: headline.served_demo_model.tag, round: headline.served_demo_model.best_round },

  // explanation check (N-02)
  alphas: ALPHAS,
  fedF1: Object.fromEntries(ALPHAS.map((a) => [a, headline.fedavg_macro_f1_headline_by_alpha[a].mean])),
  agreement: Object.fromEntries(ALPHAS.map((a) => [a, {
    j: agreement.by_alpha[a].median.jaccard_at_10,
    t: agreement.by_alpha[a].median.kendall_weighted_tau,
  }])),
  floor: agreement.instability_floor.jaccard_at_10_range,
  chance: agreement.chance_jaccard_at_10,
  ci: { alpha: ci.alpha, low: ci.by_metric.jaccard_at_10.ci95_low, high: ci.by_metric.jaccard_at_10.ci95_high },

  // trust check (N-03)
  baselineSeed: baselines.seed,
  multiKrumExclusion: strategy('multikrum').conditions.f3.malicious_exclusion_rate,
  krumCleanCost: strategy('krumclassical').conditions.clean.clean_control_cost_pp,
  nRounds: byzMeta.n_rounds,
  nSilos: byzMeta.n_silos,
  seeds: byzMeta.seeds,
  lockedClaim: byzMeta.locked_claim,
  trend: byzMeta.trend_claim_error_range_pct,

  // replay (N-04)
  nAlerts: replayMeta.n_alerts,

  story: {
    seed: story.seed,
    alpha: storyAlpha,
    compFile: story.composition.source.split('/').pop(),
    comp,
    share: (silo, col) => compRows[silo][col] / compRows[silo].TOTAL,
    jac,
    lowJaccard: LOW_JACCARD,
    jacMedian: jsorted.length % 2 ? jsorted[(jsorted.length - 1) / 2] : (jsorted[mid - 1] + jsorted[mid]) / 2,
    lows: jac.map((j, silo) => ({ j, silo })).filter((p) => p.j < LOW_JACCARD),
    f1: headline.fedavg_macro_f1_headline_by_alpha[storyAlpha][story.pointers.macro_f1.stat],
    mal: byzMeta.story.true_malicious_silos,
    flip: byzMeta.story.flip_fraction,
    featuredSilo: byzMeta.story.featured_silo,
    featuredFlagged: byzMeta.story.decisions.filter((x) => x.decision !== 'trust').length,
    featuredCall,
    runFile: byzMeta.story.run_file,
    attack: byzMeta.story.attack,
    alert: replayMeta.story_alert,
  },
};

// Consistency checks for copy that names orgs by id (dev console only).
if (import.meta.env.DEV) {
  const warn = (ok, msg) => { if (!ok) console.warn('[copy/data mismatch]', msg); };
  warn(compRows[4].Benign === 0, 'story step 3 says org 4 has no Benign traffic');
  warn(new Set(d.story.lows.map((p) => p.j)).size === 1, 'story step 5 quotes one Jaccard value for all low orgs');
  warn(d.multiKrumExclusion === 0, 'trust headline says the standard defense caught zero attackers');
  warn(d.story.mal.length === 3 && d.nSilos === 10, 'trust copy says three of ten organizations were poisoned');
  warn(featuredCall !== undefined, 'story step 6 featured round missing');
}

// ---- large files, fetched once when their section approaches -----------------
const cache = {};
export function loadLarge(name) {
  if (!cache[name]) {
    cache[name] = fetch(`${import.meta.env.BASE_URL}data/${name}.json`).then((r) => {
      if (!r.ok) throw new Error(`${name}.json: HTTP ${r.status}`);
      return r.json();
    });
    cache[name].catch(() => { delete cache[name]; });
  }
  return cache[name];
}
