// Re-reads site/public/data/*.json, rebuilds every on-screen number with src/numbers.js and
// writes out/numbers.json (id, on-screen text, file, key path, raw value).
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from '../src/numbers.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DATA = path.join(ROOT, '..', 'site', 'public', 'data');
const j = (f) => JSON.parse(readFileSync(path.join(DATA, f), 'utf8'));
const { registry } = build({
  story: j('story.json'), headline: j('headline.json'), agreement: j('agreement_by_alpha.json'), ci: j('ci.json'),
  baselines: j('baselines.json'), byz: j('byzagent_decisions.json'), replay: j('replay_alerts.json'), fedprox: j('fedprox_vs_fedavg.json'),
});
mkdirSync(path.join(ROOT, 'out'), { recursive: true });
writeFileSync(path.join(ROOT, 'out', 'numbers.json'), JSON.stringify(registry, null, 2));
for (const r of registry) console.log(r.id.padEnd(12), JSON.stringify(r.text).slice(0, 70).padEnd(46), r.file, '·', r.key);
