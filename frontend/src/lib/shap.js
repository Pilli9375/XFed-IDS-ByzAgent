// Reshapes one GET /shap/{id} response into what ShapContributionsChart
// renders: the top-K features by |SHAP| for ONE class, plus an "Other N
// features (sum)" bucket. Pure reshaping of already-served numbers -- no
// SHAP is computed here. Shared by Explain (curated rows) and the alert
// panel (streamed-pool rows) so both feed the same chart identically.

export const SHAP_TOP_K = 10;

export function buildShapView({ shapValues, rawValues, baseValues, featureNames, classIdx, topK = SHAP_TOP_K }) {
  const svRow = shapValues.map((f) => f[classIdx]);
  const baseValue = baseValues[classIdx];
  const order = svRow.map((_, i) => i).sort((a, b) => Math.abs(svRow[b]) - Math.abs(svRow[a]));
  const topIdx = order.slice(0, topK);
  const restSum = order.slice(topK).reduce((s, i) => s + svRow[i], 0);

  const chartData = topIdx.map((i) => ({ name: featureNames[i], value: svRow[i], raw: rawValues[i] }));
  chartData.push({ name: `Other ${featureNames.length - topK} features (sum)`, value: restSum, raw: null });

  return {
    chartData,
    baseValue,
    reconstructed: baseValue + svRow.reduce((a, b) => a + b, 0),
  };
}
