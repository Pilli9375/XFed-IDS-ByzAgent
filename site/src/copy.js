// All page copy lives here, taken from the approved design reference
// (site/design/landing_design_reference.html). Rewrite freely; keep the shapes.
//
// Rich text is an array of segments: a plain string, {em: '...'} (plum italic
// in headlines) or {note: '...'} (Alegreya italic). Copy that contains a number
// is a function of `d` (derived data, see src/data.js) so no number is typed here.
// Org/seed/step identifiers and α labels are labels, not results.

import { f2, f3, pct1, pctWhole, conf4, andList, cap } from './format.js';

export const nav = {
  brand: 'XFed-IDS-ByzAgent',
  links: [
    ['story', 'Story'],
    ['system', 'System'],
    ['explain', 'Explanations'],
    ['trust', 'Trust'],
    ['limits', 'Limits'],
  ],
  cta: 'Replay',
  label: 'Sections',
};

export const loader = {
  line1: 'Detect.',
  line2: 'Explain. Verify.',
};

export const source = 'source';
export const sources = 'Sources:';

export const hero = {
  kicker: '● FEDERATED INTRUSION DETECTION · VIT-AP 2026',
  line1: 'A federated IDS',
  line2: ['that checks ', { em: 'itself' }, '.'],
  lede: [
    'Ten organizations train one intrusion detector without sharing a single packet. Then the system asks two questions most federated systems never ask: do they agree on ',
    { note: 'why' },
    ' traffic is an attack, and is any of them poisoning the model?',
  ],
  badge: 'EVERY NUMBER · LINKS TO · ITS SOURCE · ',
  ctaReplay: 'Watch the replay',
  ctaFindings: 'Read the findings',
  // film length: public/film/xfed_film_16x9.mp4 runs 70.8 s (film/src/timeline.json, 2124 frames at 30 fps)
  ctaFilm: 'Watch the 70-second film',
  filmClose: 'Close',
  stats: {
    flows: 'flows after cleaning',
    orgs: 'organizations, no data shared',
    f1: 'macro-F1, centralized',
    classes: 'traffic classes',
  },
};

export const story = {
  kicker: 'N—00 · THE STORY IN SEVEN STEPS',
  steps: [
    {
      t: 'Ten organizations',
      d: () => 'Each one watches its own network traffic, and none of them can hand that traffic to the others.',
      m: () => 'Privacy rules, contracts, plain caution. The traffic stays home.',
    },
    {
      t: 'Learning without sharing',
      d: () => 'Each trains a detector on its own traffic and sends only the model update. The shared model averages them and sends the result back.',
      m: () => 'Updates travel. Packets don’t.',
    },
    {
      t: 'Nobody’s traffic looks alike',
      d: (d) => `Each circle is one organization’s real training mix. Org 0 is ${pct1(d.story.share(0, 'Benign'))}% Benign, org 4 has no Benign traffic at all, and org 7 is ${pct1(d.story.share(7, 'DoS'))}% DoS.`,
      m: () => 'This unevenness is what α controls. Real deployments look like this, not like neat equal splits.',
    },
    {
      t: 'It still works',
      d: (d) => `The shared model catches attacks for all ten. At this level of unevenness it scores ${f3(d.story.f1)} macro-F1 (mean of three seeds).`,
      m: () => 'Here is the first alert from the model we serve in the demo.',
    },
    {
      t: 'But do they agree on why?',
      d: (d) => `Each number is how much an organization’s own model shares the shared model’s top-10 reasons (Jaccard@10, where 1 means identical). The middle org sits at ${f3(d.story.jacMedian)}; orgs ${d.story.lows.map((p) => p.silo).join(' and ')}, with little or no Benign traffic, share only ${f3(d.story.lows[0].j)}.`,
      m: () => 'Same detector, different reasons. That gap is the explanation check.',
    },
    {
      t: 'And can they be trusted?',
      d: (d) => `Orgs ${andList(d.story.mal)} are secretly poisoned: ${pctWhole(d.story.flip)} of their attack traffic relabelled as Benign. The agent is never told. It downweighted org ${d.story.featuredSilo} in ${d.story.featuredFlagged} of ${d.nRounds} rounds. Org 0 it barely noticed; the trust check below shows all three.`,
      m: (d) => `Multi-Krum, given the true attacker count, excluded a poisoned organization ${pctWhole(d.multiKrumExclusion)} of the time (seed ${d.baselineSeed}).`,
    },
    {
      t: 'So the system checks itself',
      d: () => 'Two checks most federated systems skip: do the explanations agree, and can each participant be trusted. Here is how each part works.',
      m: (d) => `Steps 3–6 use seed ${d.story.seed} at α = ${d.story.alpha}; the alert comes from the served model.`,
    },
  ],
  hub: { shared: 'shared\nmodel', checks: 'checks\nitself' },
  org: (i) => `Org ${i}`,
  benignShare: (x) => `${pct1(x)}% Benign`,
  poisoned: 'poisoned',
  alertCard: (d) => ({
    head: `FIRST ALERT · SERVED MODEL (SEED ${d.servedSeed})`,
    title: d.story.alert.predicted_family,
    body: `confidence ${conf4(d.story.alert.confidence)} · ${d.story.alert.correct ? 'correct' : 'missed'}`,
  }),
  agentCard: (d) => ({
    head: `ORG ${d.story.featuredSilo} · ROUND ${d.story.featuredCall.round} · THE AGENT’S CALL`,
    title: cap(d.story.featuredCall.decision),
    body: `“${d.story.featuredCall.explanation}”`,
  }),
  legend: ['Benign', 'DoS', 'DDoS', 'PortScan', 'Other attacks'],
  foot: (d) => `Organizations are our ten simulated data partitions. Data: ${d.story.compFile}, per_silo_agreement.csv, byzagent_decisions.json, replay_alerts.json, headline.json.`,
  footLinks: ['composition', 'agreement', 'agent decisions', 'attack log', 'alert', 'macro-F1'],
  stepLabel: (n) => `Step ${n}`,
  diagramLabel: (n, t) => `Diagram for step ${n}: ${t}`,
};

export const marquee = {
  top: (d) => [`${d.nOrgs} organizations`, [{ em: 'zero' }, ' raw packets shared'], `${d.nClasses} traffic classes`, 'every number sourced'],
  bottom: ['DETECT', 'EXPLAIN', 'VERIFY', 'TRUST CHECK', 'EXPLANATION CHECK'],
};

export const system = {
  kicker: 'N—01 · THE SYSTEM',
  title: ['One pipeline, two ', { em: 'checks' }, ' most federated systems skip.'],
  stages: [
    { n: 'S—01', t: 'Data', d: (d) => `Corrected CICIDS2017, cleaned into ${d.nAttackFamilies} attack families plus Benign.`, tone: 'plain' },
    { n: 'S—02', t: 'Federated training', d: () => 'Ten organizations, deliberately uneven data, no traffic leaves home.', tone: 'plain' },
    { n: 'S—03', t: 'Explanation check', d: () => 'Do their models flag attacks for the same reasons?', tone: 'plum' },
    { n: 'S—04', t: 'Trust check', d: () => 'Is any organization poisoning the shared model?', tone: 'terracotta' },
    { n: 'S—05', t: 'Dashboard', d: () => 'Detections, explanations and trust decisions in one place.', tone: 'plain' },
  ],
};

export const explain = {
  kicker: 'N—02 · EXPLANATION CHECK',
  title: ['Detection can hold up while agreement on ', { em: 'why' }, ' slips.'],
  body: (d) => `Choose how different the organizations' data is. At α = 0.5 the shared model still scores ${f3(d.fedF1['0.5'])} macro-F1, yet they already share only about half of their top-10 reasons.`,
  margin: 'Margin note — at α = 0.1 detection itself drops too, so that point says less about explanations alone.',
  question: "How different is each organization's data?",
  alphas: [
    { key: '5.0', label: 'α 5.0 · similar', note: () => 'Near-identical data: organizations largely agree on the reasons, well above the seed-noise floor.' },
    { key: '0.5', label: 'α 0.5 · uneven', note: () => 'Detection still strong, but only about half of the top-10 reasons are shared.' },
    { key: '0.1', label: 'α 0.1 · very uneven', note: (d) => `At or below seed noise (95% interval ${f3(d.ci.low)}–${f3(d.ci.high)} overlaps the floor), so directional, not significant. Detection also drops here.`, ci: true },
  ],
  cards: { f1: 'Detection · macro-F1', j: 'Agreement · Jaccard@10', t: 'Ranking order · weighted τ' },
  axisZero: '0 · no shared reasons',
  floor: (d) => `seed-noise floor ${f3(d.floor[0])}–${f3(d.floor[1])}`,
  chance: (d) => `chance ${f3(d.chance)}`,
  barLabel: (d, a) => `Jaccard@10 at α ${a}: ${f3(d.agreement[a].j)}, against the seed-noise floor ${f3(d.floor[0])}–${f3(d.floor[1])} and chance ${f3(d.chance)}`,
};

export const trust = {
  kicker: 'N—03 · TRUST CHECK',
  title: ['The standard defense caught ', { em: 'zero' }, ' attackers.'],
  body: "We poisoned three of ten organizations by relabeling attack traffic as Benign, then tested Multi-Krum fairly, even telling it how many attackers there were. It never excluded one. Our agent reads each organization's training behaviour and decides trust, downweight or quarantine every round.",
  cards: {
    multiKrum: 'Multi-Krum · poisoned orgs excluded',
    krumCost: 'Cost of classical Krum, no attack',
    signal: 'Only strong attack signal',
    signalValue: 'training loss',
  },
  gridTitle: ['Every call the agent made, ', { em: 'side by side' }, '.'],
  gridBody: (d) => `Each row is one organization, each square one training round. Left, nobody is attacking. Right, organizations ${andList(d.mal)} are poisoned. The agent is never told which; we mark those rows afterwards from the attack log. Hover any square to read its reason.`,
  seed: (s) => `Seed ${s}`,
  replay: 'Replay',
  legend: {
    trust: 'Trust',
    downweight: 'Downweight',
    quarantine: 'Quarantine',
    poisoned: 'Poisoned (ground truth, hidden from agent)',
  },
  colClean: 'NO ATTACK',
  colAttack: (nMal, nSilos) => `${nMal} OF ${nSilos} POISONED`,
  colFlag: ['FLAG RATE', 'clean → attack'],
  sumClean: (k, n) => `${k} of ${n} calls flagged, nobody attacking`,
  sumAttack: (km, nm, kh, nh) => `poisoned ${km}/${nm} flagged · honest ${kh}/${nh}`,
  roundAxis: 'round',
  loading: 'Loading the agent’s decisions…',
  loadError: 'The decision file could not be loaded.',
  decisions: { trust: 'Trust', downweight: 'Downweight', quarantine: 'Quarantine' },
  detailHead: (seed, side, silo, round) => `SEED ${seed} · ${side === 'a' ? 'NO-ATTACK RUN' : 'ATTACK RUN'} · ORG ${silo} · ROUND ${round}`,
  truthClean: 'Truth: nobody is attacking in this run',
  truthPoisoned: (flip) => `Truth: poisoned, ${pctWhole(flip)} of its attack labels flipped to Benign`,
  truthHonest: 'Truth: honest organization',
  truthHidden: 'ground truth, hidden from agent',
  reasonLabel: 'THE AGENT’S STATED REASON, VERBATIM',
  stats: { tl: 'training loss', un: 'update norm', cg: 'cosine to global' },
  cellLabel: (silo, round, side, decision) => `Org ${silo}, round ${round}, ${side === 'a' ? 'no-attack run' : 'attack run'}: ${decision}`,
  org: (i) => `Org ${i}`,
  seedGroup: 'Seed',
  gridLabel: (seed) => `Agent decisions, seed ${seed}: organizations by training rounds, no-attack run then attack run`,
  notes: {
    '42': (fr) => ['SEED 42 · THE CEILING CASE', `Organizations 0, 3 and 5 were already flagged in nearly every round with no attack (${f2(fr('a', 0))}, ${f2(fr('a', 3))}, ${f2(fr('a', 5))}), so poisoning them had almost nothing left to change. That ceiling is why this seed first looked like the agent ignored attacks.`],
    '1337': (fr) => ['SEED 1337 · WHERE THE RESPONSE SHOWS', `Org 5 goes from ${f2(fr('a', 5))} to ${f2(fr('b', 5))} once poisoned, and org 3 from ${f2(fr('a', 3))} to ${f2(fr('b', 3))}. Org 0 barely moves (${f2(fr('a', 0))} → ${f2(fr('b', 0))}); it held little attack traffic to poison, and we cannot separate that from the agent missing it.`],
    '2024': (fr) => ['SEED 2024 · BOTH EFFECTS', `Org 5 rises ${f2(fr('a', 5))} → ${f2(fr('b', 5))} and org 0 ${f2(fr('a', 0))} → ${f2(fr('b', 0))}. Org 3 was already at ${f2(fr('a', 3))} with no attack, the same ceiling seen at seed 42.`],
  },
  flagDef: (d) => `Flag rate = share of ${d.nRounds} rounds where the agent downweighted or quarantined that organization. Reasons are shown as written; about ${d.trend.low}–${d.trend.high}% of the agent's trend claims contradicted the numbers it was given.`,
  fidelity: (d) => `The agent produces decisions plus a rationale of measured fidelity. About ${d.trend.low}–${d.trend.high}% of its trend claims contradicted the numbers it was given; we report that.`,
};

export const replay = {
  kicker: 'N—04 · REPLAY',
  title: ['Watch it ', { em: 'work' }, '.'],
  pill: '● Recorded from real runs · nothing simulated',
  stream: 'FLOW STREAM',
  pause: 'Pause',
  play: 'Play',
  jump: 'Jump to a miss',
  seen: (n) => `/ ${n} seen`,
  right: 'right',
  missed: 'missed',
  statusRight: '✓ right',
  statusMissed: (t) => `✕ missed · was ${t}`,
  why: (seq) => `WHY THIS ALERT · #${seq}`,
  verdictRight: '✓ correct',
  verdictMissed: (t) => `✕ missed · this was ${t}`,
  confidence: 'model confidence',
  reasons: 'TOP 5 REASONS · SHAP VALUE FOR THE PREDICTED CLASS',
  away: (p) => `← pushes away from ${p}`,
  toward: (p) => `pushes toward ${p} →`,
  noteLabel: 'ANALYST NOTE · written by a local LLM from the raw values',
  loading: 'Loading recorded alerts…',
  loadError: 'The alert file could not be loaded.',
  feedLabel: 'Recorded alerts, newest first',
  footLinks: ['alerts', 'served model'],
  foot: (d) => `Served model ${d.served.tag}, round ${d.served.round}. ${d.nAlerts} real test rows, read once for display only; no metric comes from them. The analyst note is a usability feature, not a research claim. All ${d.nAlerts} stream in stored order.`,
};

export const limits = {
  kicker: 'N—05 · WHAT WE DIDN\'T CLAIM',
  title: ['Some of our first answers were ', { em: 'wrong' }, '. Here is what we kept.'],
  items: [
    'The drop below seed noise at α = 0.1 is directional, not significant; the intervals overlap.',
    'Our first outlier flags were noise from a single random draw. Averaging three draws removed them.',
    "Entropy didn't explain the effect. KL divergence did, and we say we tried entropy first.",
    'Giving the agent memory of past rounds failed the test we set before running it.',
  ],
};

export const footer = {
  team: 'TEAM',
  members: [
    ['V Naga Adithya', '23BCE9062'],
    ['T Shaun', '23BCE9916'],
    ['P Sampath', '23BCE8614'],
    ['D Tharun', '23BCE8818'],
  ],
  name: ['XFed-IDS-', { em: 'ByzAgent' }],
  data: 'Data: Distrinet CICIDS2017 V4 — Liu et al., IEEE CNS 2022; Engelen et al., WTMC 2021. Not redistributed here.',
  code: 'Code on GitHub ↗',
};
