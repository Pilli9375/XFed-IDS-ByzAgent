// Resolves every "source" link the site can render and checks that each target
// is a file tracked in git (so the GitHub link resolves). Run: npm run check:sources
import { readFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { SRC, pick, filePart } from '../src/sources.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const dataDir = path.join(here, '..', 'public', 'data');
const repoRoot = path.join(here, '..', '..');
const read = (f) => JSON.parse(readFileSync(path.join(dataDir, f), 'utf8'));

const J = {
  headline: read('headline.json'),
  agreement: read('agreement_by_alpha.json'),
  ci: read('ci.json'),
  story: read('story.json'),
  baselines: read('baselines.json'),
  byz: read('byzagent_decisions.json'),
  replay: read('replay_alerts.json'),
};

let tracked = null;
try {
  tracked = new Set(execSync('git ls-files', { cwd: repoRoot, maxBuffer: 1 << 28 }).toString().split('\n'));
} catch {
  console.warn('git not available: checking source-list membership only');
}

const links = new Map(); // path -> where it is used
const add = (p, why) => links.set(p, [...(links.get(p) || []), why]);

for (const [key, [list, match]] of Object.entries(SRC)) add(pick(J[list].source, match), `SRC.${key}`);

for (const [seed, conds] of Object.entries(J.byz.by_seed)) {
  for (const name of ['clean', 'f3_sudden']) {
    add(pick(J.byz.source, filePart(conds[name].run_file)), `trust grid seed ${seed} ${name}`);
  }
  const a = conds.f3_sudden.attack;
  const hit = J.byz.source.find((s) => s.endsWith('/attack_config.json') && s.includes(`_s${seed}_f${a.f}_${a.mode}_`));
  if (!hit) throw new Error(`no attack_config.json for seed ${seed}`);
  add(hit, `attack log seed ${seed}`);
}

let bad = 0;
for (const [p, uses] of [...links].sort()) {
  const ok = !tracked || tracked.has(p);
  if (!ok) bad += 1;
  console.log(`${ok ? 'ok     ' : 'MISSING'}  ${p}  <- ${uses.join(', ')}`);
}
console.log(`\n${links.size} link targets, ${bad} not tracked in git`);
process.exit(bad ? 1 : 0);
