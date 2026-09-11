// Helpers for Detect's row-label building and custom-flow input parsing.
// Pure input handling / reshaping, not a statistical computation -- no
// canonical Python version to diverge from.

/**
 * "{family} — sample {n}" per row, n counting occurrences of that family in
 * ascending sample_id order. Mirrors sections.py's row_labels loop.
 */
export function buildEvalRowLabels(rows) {
  const seen = {};
  return rows.map((r) => {
    seen[r.eval_family] = (seen[r.eval_family] ?? 0) + 1;
    return `${r.eval_family} — sample ${seen[r.eval_family]}`;
  });
}

export function evalRowTemplateText(row) {
  return row.raw_values.join(', ');
}

function parseNumberList(text) {
  return text
    .trim()
    .split(/[\s,]+/)
    .filter((s) => s.length > 0)
    .map(Number);
}

/**
 * Parses pasted text into a { featureName: value } dict, positionally
 * zipped with featureNames (the model's canonical 82-column order) -- the
 * same order GET /shap/{id}'s feature_names already gives.
 */
export function parsePastedFlow(text, featureNames) {
  const values = parseNumberList(text);
  if (values.length !== featureNames.length) {
    throw new Error(
      `Expected exactly ${featureNames.length} values, got ${values.length}.`,
    );
  }
  if (values.some((v) => Number.isNaN(v))) {
    throw new Error('Could not parse one or more values as numbers.');
  }
  return Object.fromEntries(featureNames.map((name, i) => [name, values[i]]));
}

/**
 * Parses a one-row CSV (with or without a header) into the same dict shape.
 * If the first line's cells aren't all numeric, it's treated as a header
 * naming each column -- values are then matched by name, not position, so
 * a differently-ordered CSV still works. Otherwise the first line is the
 * one data row, matched positionally to featureNames.
 */
export function parseCsvFlow(csvText, featureNames) {
  const lines = csvText.split(/\r?\n/).map((l) => l.trim()).filter((l) => l.length > 0);
  if (lines.length === 0) {
    throw new Error('Empty CSV.');
  }
  const firstCells = lines[0].split(',').map((c) => c.trim());
  const firstIsHeader = firstCells.some((c) => Number.isNaN(Number(c)));

  if (!firstIsHeader) {
    return parsePastedFlow(lines[0], featureNames);
  }

  if (lines.length < 2) {
    throw new Error('CSV has a header row but no data row.');
  }
  const header = firstCells;
  const values = lines[1].split(',').map((c) => Number(c.trim()));
  const missing = featureNames.filter((f) => !header.includes(f));
  if (missing.length > 0) {
    throw new Error(`CSV header is missing ${missing.length} expected feature column(s).`);
  }
  const byName = Object.fromEntries(header.map((h, i) => [h, values[i]]));
  const out = {};
  for (const name of featureNames) {
    const v = byName[name];
    if (Number.isNaN(v) || v == null) {
      throw new Error(`Column "${name}" did not parse as a number.`);
    }
    out[name] = v;
  }
  return out;
}

export function confidenceTier(confidence) {
  if (confidence >= 0.9) return 'High';
  if (confidence >= 0.6) return 'Medium';
  return 'Low';
}
