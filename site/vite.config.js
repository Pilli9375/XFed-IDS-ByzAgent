import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const DATA_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), 'public', 'data');

// Build-time slices of site/public/data/*.json. Small files go in whole; from the
// two large files (byzagent_decisions, replay_alerts) only the handful of values the
// page needs before those sections load. No value is changed here, only selected.
function showcaseData() {
  const ID = 'virtual:showcase-data';
  const RID = '\0' + ID;
  return {
    name: 'showcase-data',
    resolveId(id) {
      if (id === ID) return RID;
    },
    load(id) {
      if (id !== RID) return;
      const read = (f) => {
        const p = path.join(DATA_DIR, f);
        this.addWatchFile(p);
        return JSON.parse(readFileSync(p, 'utf8'));
      };
      const headline = read('headline.json');
      const agreement = read('agreement_by_alpha.json');
      const ci = read('ci.json');
      const story = read('story.json');
      const baselines = read('baselines.json');
      const byz = read('byzagent_decisions.json');
      const replay = read('replay_alerts.json');

      const pb = story.pointers.byzagent;
      const cond = byz.by_seed[pb.seed][pb.condition];
      const storyDecisions = cond.decisions
        .filter((d) => d.silo === pb.featured_silo)
        .map((d) => ({ round: d.round, decision: d.decision, explanation: d.explanation }));
      const alert = replay.alerts.find((a) => a.seq === story.pointers.alert.seq);

      const out = {
        headline,
        agreement,
        ci,
        story,
        baselines: {
          source: baselines.source,
          seed: baselines.seed,
          strategies: baselines.strategies.map((s) => ({
            strategy: s.strategy,
            label: s.label,
            conditions: Object.fromEntries(
              Object.entries(s.conditions).map(([k, c]) => [k, {
                run: c.run,
                clean_control_cost_pp: c.clean_control_cost_pp,
                malicious_exclusion_rate: c.mechanism.malicious_exclusion_rate,
                true_malicious_silos: c.true_malicious_silos,
              }]),
            ),
          })),
        },
        byzMeta: {
          source: byz.source,
          n_silos: byz.n_silos,
          n_rounds: byz.n_rounds,
          locked_claim: byz.locked_claim,
          trend_claim_error_range_pct: byz.trend_claim_error_range_pct,
          seeds: Object.keys(byz.by_seed),
          story: {
            seed: pb.seed,
            condition: pb.condition,
            run_file: cond.run_file,
            true_malicious_silos: cond.true_malicious_silos,
            attack: { f: cond.attack.f, mode: cond.attack.mode },
            flip_fraction: cond.attack.sudden.flip_fraction,
            featured_silo: pb.featured_silo,
            featured_round: pb.featured_round,
            decisions: storyDecisions,
          },
        },
        replayMeta: {
          source: replay.source,
          tag: replay.tag,
          n_alerts: replay.n_alerts,
          alerts_length: replay.alerts.length,
          story_alert: {
            seq: alert.seq,
            true_family: alert.true_family,
            predicted_family: alert.predicted_family,
            correct: alert.correct,
            confidence: alert.confidence,
          },
        },
      };
      return Object.entries(out).map(([k, v]) => `export const ${k} = ${JSON.stringify(v)};`).join('\n');
    },
  };
}

export default defineConfig({
  plugins: [react(), showcaseData()],
  build: { outDir: 'dist', target: 'es2020' },
});
