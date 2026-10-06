// Source links. Every link target is an entry of a JSON file's own `source` list,
// selected by a substring; paths are never typed here. Entries like
// "tools/x.py::fn" or "tools/x.py (note)" link to the file part only.

export const REPO = 'https://github.com/Pilli9375/XFed-IDS-ByzAgent';
const BLOB = REPO + '/blob/master/';

export const filePart = (entry) => entry.split('::')[0].replace(/\s*\(.*$/, '').trim();

export function pick(sourceList, match) {
  const hit = sourceList.find((s) => filePart(s).includes(match));
  if (!hit) throw new Error(`source "${match}" not found in [${sourceList.join(', ')}]`);
  return filePart(hit);
}

export const ghUrl = (path) => BLOB + path;

// Which source entry backs each displayed number. Where the computing file is
// git-ignored (results/aggregated/*.csv, flip_log.csv, streamed_pool.npz), the
// link goes to the tracked canonical file in the same source list instead.
export const SRC = {
  flows: ['headline', 'data/processed/clean_log.json'],
  classes: ['headline', 'data/processed/clean_log.json'],
  orgs: ['headline', 'data/processed/partitions/manifest.json'],
  macroF1: ['headline', 'docs/contribution_a_results.md'],
  servedModel: ['headline', 'results/inspection/best_rounds_manifest.json'],
  agreement: ['agreement', 'results/inspection/agreement_metrics.csv'],
  floor: ['agreement', 'results/inspection/centralized_instability_floor.csv'],
  chance: ['agreement', 'tools/agreement_metrics.py'],
  ci: ['ci', 'tools/chat04_closeout.py'],
  composition: ['story', 'silo_family_composition_'],
  perSilo: ['story', 'results/inspection/per_silo_agreement.csv'],
  multiKrum: ['baselines', 'multikrum_f3_a0.5_s42_poisoned_f3_sudden_silos0-3-5/krum_selection.jsonl'],
  krumCost: ['baselines', 'krumclassical_f3_a0.5_s42/final_metrics.json'],
  attackSignal: ['baselines', 'docs/contribution_b_results.md'],
  trendRange: ['byz', 'docs/contribution_b_results.md'],
  lockedClaim: ['byz', 'docs/contribution_b_results.md'],
  alerts: ['replay', 'results/explanations/fedavg_a0.5_s42/sentences.json'],
};
