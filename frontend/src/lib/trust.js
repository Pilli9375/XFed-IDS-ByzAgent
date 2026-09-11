// Client-side helpers for the Client Trust Monitor (Contribution B).
// GET /trust already does the hard part -- pairing clean+attack runs and
// excluding anything that isn't a real pair, with a reason -- so there's no
// pairing logic to reimplement here. The one thing this file does compute
// is the clean-vs-attack join + lift, which mirrors
// app_lib/trust_loaders.py's clean_vs_attack_table(): a per-silo outer
// join with missing flag rates filled to 0.0, then lift = attack - clean.
// Flagged for visibility (per the standing instruction to flag client-side
// reimplementations of a canonical Python computation): this one is a
// straight join + subtraction with no aggregation choices (no medians, no
// quantile method) to diverge on, unlike lib/agreement.js's statistics.

export function buildCleanVsAttackRows(cleanPerSilo, attackPerSilo, maliciousSilos) {
  const cleanBySilo = new Map(cleanPerSilo.map((r) => [r.silo_id, r]));
  const attackBySilo = new Map(attackPerSilo.map((r) => [r.silo_id, r]));
  const silos = [...new Set([...cleanBySilo.keys(), ...attackBySilo.keys()])].sort((a, b) => a - b);

  return silos.map((silo) => {
    const cleanRate = cleanBySilo.get(silo)?.flag_rate ?? 0.0;
    const attackRate = attackBySilo.get(silo)?.flag_rate ?? 0.0;
    return {
      silo,
      label: `silo ${silo}`,
      clean_flag_rate: cleanRate,
      attack_flag_rate: attackRate,
      lift: attackRate - cleanRate,
      malicious: maliciousSilos.includes(silo),
    };
  });
}

// Every field here comes straight from the condition object GET /trust
// serves (alpha, seed, f, mode, true_malicious_silos) -- just formatted
// into one label, nothing invented.
export function formatConditionLabel(condition) {
  const silos = condition.true_malicious_silos.join(',');
  return `α=${condition.alpha}, seed=${condition.seed}, f=${condition.f}, ${condition.mode} (malicious silos ${silos})`;
}
