// Display rules for the trust check (not results): the clean-run flag rate
// at or above which a clean org counts as saturated by the compositional
// confound (the brief's rule for the Investigate ambient light), and the
// lift above which the design highlights a row.
export const CONFOUND_CLEAN_RATE = 0.9;
export const LIFT_HIGHLIGHT = 0.3;

export function conditionLabel(c) {
  return `α=${c.alpha} · seed ${c.seed} · f=${c.f} ${c.mode}`;
}

const RESULTS_FED = 'results/federated';

// Files /trust read for one condition (backend/trust.py): the attack's
// attack_config.json and both runs' decision logs and client stats.
export function conditionSources(c) {
  return [
    `results/attacks/${c.attack_tag}/attack_config.json`,
    `${RESULTS_FED}/${c.clean.run_tag}/${c.clean.decision_log}`,
    `${RESULTS_FED}/${c.attack.run_tag}/${c.attack.decision_log}`,
    `${RESULTS_FED}/${c.clean.run_tag}/client_stats.jsonl`,
    `${RESULTS_FED}/${c.attack.run_tag}/client_stats.jsonl`,
  ];
}

export function orgTone(row) {
  if (row.malicious) return 'attack';
  return row.clean_flag_rate >= CONFOUND_CLEAN_RATE ? 'agent' : 'ok';
}
