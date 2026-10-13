// Classifies one GET /alerts entry for colour and filtering. A "miss" is a
// flow whose predicted family differs from its true label (validation rows
// carry the true label; the model never sees it). Benign is the one
// non-attack family in the frozen vocabulary.
export const BENIGN = 'Benign';

export function isMiss(a) {
  return a.true_family != null && a.true_family !== a.predicted_family;
}

export function isAttack(a) {
  return a.predicted_family !== BENIGN;
}

export function kindOf(a) {
  if (!a) return 'ok';
  if (isMiss(a)) return 'miss';
  return isAttack(a) ? 'attack' : 'ok';
}

export const FILTERS = [
  { id: 'all', label: 'All', test: () => true },
  { id: 'attacks', label: 'Attacks', test: isAttack },
  { id: 'misses', label: 'Misses', test: isMiss },
];
