// Every number the film shows is built here from site/public/data/*.json and formatted with the
// site's own format.js, so the film rounds exactly like the site. Each value is registered with
// its file + key path + raw value; scripts/check-numbers.mjs writes that registry to
// out/numbers.json for the critique rounds. Scenes read strings from `N`, never from literals.
//
// build() takes the parsed JSON objects so it runs both in the Remotion bundle (JSON imports)
// and in Node (fs reads).
import { f2, f3, pct1, pctWhole, conf4, int } from '../../site/src/format.js';

const WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];
const word = (n) => {
  if (!Number.isInteger(n) || n < 0 || n >= WORDS.length) throw new Error(`no word for ${n}`);
  return WORDS[n];
};
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const OTHER = ['Bot', 'BruteForce', 'Heartbleed', 'Infiltration', 'WebAttack'];
const STATE_ORDER = ['trust', 'downweight', 'quarantine'];

export function build({ story, headline, agreement, ci, baselines, byz, replay }) {
  const reg = [];
  const N = {};
  const put = (id, text, file, key, raw) => {
    if (N[id] !== undefined) throw new Error(`duplicate number id ${id}`);
    N[id] = text;
    reg.push({ id, text, file, key, raw });
    return text;
  };

  // ---- dataset / hook
  const nOrgs = headline.dataset.n_organizations;
  put('nOrgsWord', cap(word(nOrgs)), 'headline.json', 'dataset.n_organizations', nOrgs);

  // ---- story partition (seed 1337, alpha 0.5)
  const seed = story.seed;
  const alpha = story.alpha;
  put('storySeed', String(seed), 'story.json', 'seed', seed);
  put('storyAlpha', String(alpha), 'story.json', 'alpha', alpha);
  const rows = story.composition.rows;
  if (rows.length !== nOrgs) throw new Error('composition rows != n_organizations');
  const comp = rows.map((r) => ({
    total: r.TOTAL,
    slices: [r.Benign, r.DoS, r.DDoS, r.PortScan, OTHER.reduce((s, k) => s + r[k], 0)],
  }));
  comp.forEach((c, i) => {
    const sum = c.slices.reduce((a, b) => a + b, 0);
    if (sum !== c.total) throw new Error(`org ${i}: slices ${sum} != TOTAL ${c.total}`);
  });
  put('org0Benign', `${pct1(rows[0].Benign / rows[0].TOTAL)}%`, 'story.json', 'composition.rows[0].Benign / composition.rows[0].TOTAL', [rows[0].Benign, rows[0].TOTAL]);
  if (rows[4].Benign !== 0) throw new Error('S3 copy says org 4 has no Benign rows');
  put('org4Benign', int(rows[4].Benign), 'story.json', 'composition.rows[4].Benign', rows[4].Benign);
  put('org4Total', int(rows[4].TOTAL), 'story.json', 'composition.rows[4].TOTAL', rows[4].TOTAL);

  // ---- first alert (served model)
  const served = headline.served_demo_model;
  const alert = replay.alerts.find((a) => a.seq === story.pointers.alert.seq);
  put('alertSeq', String(alert.seq), 'replay_alerts.json', `alerts[seq=${alert.seq}].seq`, alert.seq);
  put('alertFamily', alert.predicted_family, 'replay_alerts.json', `alerts[seq=${alert.seq}].predicted_family`, alert.predicted_family);
  put('alertConf', conf4(alert.confidence), 'replay_alerts.json', `alerts[seq=${alert.seq}].confidence`, alert.confidence);
  put('alertCorrect', alert.correct ? 'correct' : 'missed', 'replay_alerts.json', `alerts[seq=${alert.seq}].correct`, alert.correct);
  put('servedSeed', String(served.seed), 'headline.json', 'served_demo_model.seed', served.seed);
  put('servedRound', String(served.best_round), 'headline.json', 'served_demo_model.best_round', served.best_round);
  put('servedAlpha', String(served.alpha), 'headline.json', 'served_demo_model.alpha', served.alpha);

  // ---- macro-F1 at the story alpha
  const pf = story.pointers.macro_f1;
  const f1 = headline[pf.key][pf.alpha];
  put('f1Alpha', pf.alpha, 'story.json', 'pointers.macro_f1.alpha', pf.alpha);
  put('f1', f3(f1[pf.stat]), 'headline.json', `${pf.key}["${pf.alpha}"].${pf.stat}`, f1[pf.stat]);
  put('f1Std', f3(f1.std), 'headline.json', `${pf.key}["${pf.alpha}"].std`, f1.std);
  put('f1nWord', word(f1.n), 'headline.json', `${pf.key}["${pf.alpha}"].n`, f1.n);
  put('f1n', String(f1.n), 'headline.json', `${pf.key}["${pf.alpha}"].n`, f1.n);
  const f1Raw = f1[pf.stat];

  // ---- per-org agreement (seed 1337, alpha 0.5)
  const pa = story.per_silo_agreement;
  if (pa.filter.seed !== seed || pa.filter.alpha !== alpha) throw new Error('per-silo agreement filter != story seed/alpha');
  const jac = pa.rows.map((r) => r.jaccard_at_10);
  jac.forEach((j, i) => put(`jac${i}`, f3(j), 'story.json', `per_silo_agreement.rows[${i}].jaccard_at_10`, j));
  const sorted = jac.slice().sort((a, b) => a - b);
  const m = sorted.length / 2;
  const jacMedian = sorted.length % 2 ? sorted[(sorted.length - 1) / 2] : (sorted[m - 1] + sorted[m]) / 2;
  put('jacMedian', f3(jacMedian), 'story.json', 'median of per_silo_agreement.rows[*].jaccard_at_10', jacMedian);
  const LOW_JACCARD = 0.4; // site design constant (site/src/data.js), a styling cutoff, never printed
  const lows = jac.map((j, silo) => ({ j, silo })).filter((p) => p.j < LOW_JACCARD);
  if (lows.length !== 2 || lows[0].silo !== 4 || lows[1].silo !== 7 || lows[0].j !== lows[1].j) {
    throw new Error('S5 copy names orgs 4 and 7 sharing one low value');
  }
  put('jacLow', f3(lows[0].j), 'story.json', 'per_silo_agreement.rows[4|7].jaccard_at_10', lows[0].j);

  // ---- agreement by alpha (all seeds)
  const ALPHAS = ['5.0', '0.5', '0.1'];
  const agree = {};
  for (const a of ALPHAS) {
    const v = agreement.by_alpha[a].median.jaccard_at_10;
    agree[a] = v;
    put(`agree_${a}`, f3(v), 'agreement_by_alpha.json', `by_alpha["${a}"].median.jaccard_at_10`, v);
  }
  const floor = agreement.instability_floor.jaccard_at_10_range;
  put('floorLo', f3(floor[0]), 'agreement_by_alpha.json', 'instability_floor.jaccard_at_10_range[0]', floor[0]);
  put('floorHi', f3(floor[1]), 'agreement_by_alpha.json', 'instability_floor.jaccard_at_10_range[1]', floor[1]);
  const chance = agreement.chance_jaccard_at_10;
  put('chance', f3(chance), 'agreement_by_alpha.json', 'chance_jaccard_at_10', chance);
  if (String(ci.alpha) !== '0.1') throw new Error('ci.json is not the alpha 0.1 slice');
  const ciJ = ci.by_metric.jaccard_at_10;
  put('ciLo', f3(ciJ.ci95_low), 'ci.json', 'by_metric.jaccard_at_10.ci95_low', ciJ.ci95_low);
  put('ciHi', f3(ciJ.ci95_high), 'ci.json', 'by_metric.jaccard_at_10.ci95_high', ciJ.ci95_high);
  put('ciAlpha', String(ci.alpha), 'ci.json', 'alpha', ci.alpha);
  const agreeSeeds = Object.keys(agreement.by_alpha['0.5'].per_seed);
  put('agreeSeeds', agreeSeeds.join(', '), 'agreement_by_alpha.json', 'by_alpha["0.5"].per_seed (keys)', agreeSeeds);

  // ---- trust check (seed 1337, f3 sudden)
  const pb = story.pointers.byzagent;
  const runs = byz.by_seed[pb.seed];
  const clean = runs.clean;
  const atk = runs[pb.condition];
  const mal = atk.true_malicious_silos;
  put('trustSeed', String(pb.seed), 'story.json', 'pointers.byzagent.seed', pb.seed);
  put('byzAlpha', String(byz.alpha), 'byzagent_decisions.json', 'alpha', byz.alpha);
  put('mal', `${mal.slice(0, -1).join(', ')} and ${mal[mal.length - 1]}`, 'byzagent_decisions.json', `by_seed["${pb.seed}"].${pb.condition}.true_malicious_silos`, mal);
  put('flip', pctWhole(atk.attack.sudden.flip_fraction), 'byzagent_decisions.json', `by_seed["${pb.seed}"].${pb.condition}.attack.sudden.flip_fraction`, atk.attack.sudden.flip_fraction);
  put('attackF', String(atk.attack.f), 'byzagent_decisions.json', `by_seed["${pb.seed}"].${pb.condition}.attack.f`, atk.attack.f);
  put('nSilos', String(byz.n_silos), 'byzagent_decisions.json', 'n_silos', byz.n_silos);
  const nR = byz.n_rounds;
  const grid = (run) => {
    const g = Array.from({ length: byz.n_silos }, () => Array(nR).fill(null));
    for (const x of run.decisions) g[x.silo][x.round - 1] = STATE_ORDER.indexOf(x.decision);
    g.forEach((row, s) => row.forEach((v, r) => { if (v === null || v < 0) throw new Error(`missing decision silo ${s} round ${r + 1}`); }));
    return g;
  };
  const gA = grid(clean);
  const gB = grid(atk);
  const flagged = (g, pred) => {
    let k = 0; let n = 0;
    g.forEach((row, s) => { if (pred(s)) row.forEach((v) => { n += 1; if (v > 0) k += 1; }); });
    return [k, n];
  };
  const [ka, na] = flagged(gA, () => true);
  const [km, nm] = flagged(gB, (s) => mal.includes(s));
  const [kh, nh] = flagged(gB, (s) => !mal.includes(s));
  const dcm = atk.decision_counts.malicious;
  const dch = atk.decision_counts.honest;
  if (km !== dcm.n - dcm.trust || nm !== dcm.n || kh !== dch.n - dch.trust || nh !== dch.n) throw new Error('flag counts disagree with decision_counts');
  const runKey = `by_seed["${pb.seed}"]`;
  put('sumClean', `${ka} of ${na} calls flagged, nobody attacking`, 'byzagent_decisions.json', `${runKey}.clean.decisions[] (count decision != trust)`, [ka, na]);
  put('sumAttack', `poisoned ${km}/${nm} flagged · honest ${kh}/${nh}`, 'byzagent_decisions.json', `${runKey}.${pb.condition}.decisions[] (count decision != trust; = decision_counts)`, [km, nm, kh, nh]);
  const rate = (g, s) => g[s].filter((v) => v > 0).length / nR;
  const fs = pb.featured_silo;
  put('org5RateA', f2(rate(gA, fs)), 'byzagent_decisions.json', `${runKey}.clean.decisions[silo=${fs}] flagged / ${nR}`, rate(gA, fs));
  put('org5RateB', f2(rate(gB, fs)), 'byzagent_decisions.json', `${runKey}.${pb.condition}.decisions[silo=${fs}] flagged / ${nR}`, rate(gB, fs));
  put('org0RateA', f2(rate(gA, 0)), 'byzagent_decisions.json', `${runKey}.clean.decisions[silo=0] flagged / ${nR}`, rate(gA, 0));
  put('org0RateB', f2(rate(gB, 0)), 'byzagent_decisions.json', `${runKey}.${pb.condition}.decisions[silo=0] flagged / ${nR}`, rate(gB, 0));
  const call = atk.decisions.find((x) => x.silo === fs && x.round === pb.featured_round);
  put('featSilo', String(fs), 'story.json', 'pointers.byzagent.featured_silo', fs);
  put('featRound', String(call.round), 'story.json', 'pointers.byzagent.featured_round', call.round);
  put('featDecision', cap(call.decision), 'byzagent_decisions.json', `${runKey}.${pb.condition}.decisions[silo=${fs},round=${call.round}].decision`, call.decision);
  put('featReason', call.explanation, 'byzagent_decisions.json', `${runKey}.${pb.condition}.decisions[silo=${fs},round=${call.round}].explanation`, call.explanation);
  put('nRounds', String(nR), 'byzagent_decisions.json', 'n_rounds', nR);
  const tr = byz.trend_claim_error_range_pct;
  put('trendLo', String(tr.low), 'byzagent_decisions.json', 'trend_claim_error_range_pct.low', tr.low);
  put('trendHi', String(tr.high), 'byzagent_decisions.json', 'trend_claim_error_range_pct.high', tr.high);

  // ---- Multi-Krum (seed 42 baselines)
  const mk = baselines.strategies.find((s) => s.strategy === 'multikrum');
  const mkx = mk.conditions.f3.mechanism.malicious_exclusion_rate;
  put('mkExcl', pctWhole(mkx), 'baselines.json', 'strategies[multikrum].conditions.f3.mechanism.malicious_exclusion_rate', mkx);
  put('mkSeed', String(baselines.seed), 'baselines.json', 'seed', baselines.seed);
  put('mkAlpha', String(baselines.alpha), 'baselines.json', 'alpha', baselines.alpha);
  if (!mk.oracle_defense || mk.conditions.f3.num_malicious_nodes_oracle !== atk.attack.f) throw new Error('stamp says Multi-Krum was given the true attacker count');

  // ---- replay miss
  const miss = replay.alerts.find((a) => !a.correct);
  put('missSeq', String(miss.seq).padStart(3, '0'), 'replay_alerts.json', 'alerts[first correct == false].seq', miss.seq);
  put('missTrue', miss.true_family, 'replay_alerts.json', `alerts[seq=${miss.seq}].true_family`, miss.true_family);
  put('missPred', miss.predicted_family, 'replay_alerts.json', `alerts[seq=${miss.seq}].predicted_family`, miss.predicted_family);
  put('nAlerts', String(replay.n_alerts), 'replay_alerts.json', 'n_alerts', replay.n_alerts);
  if (replay.tag !== served.tag) throw new Error('replay alerts are not from the served model');

  return {
    N,
    registry: reg,
    raw: { comp, jac, lows: lows.map((p) => p.silo), mal, gA, gB, featSilo: fs, featRound: call.round, nRounds: nR, nSilos: byz.n_silos, agree, floor, chance, ci: [ciJ.ci95_low, ciJ.ci95_high], f1: f1Raw, mkx },
  };
}
