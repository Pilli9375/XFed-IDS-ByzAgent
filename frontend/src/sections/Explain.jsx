import { useEffect, useMemo, useState } from 'react';
import { postPredict } from '../api/client';
import { useEvalRows } from '../api/useEvalRows';
import Callout from '../components/Callout';
import DataTable from '../components/DataTable';
import Expander from '../components/Expander';
import Pills from '../components/Pills';
import Rule from '../components/Rule';
import SectionHeader from '../components/SectionHeader';
import Stat from '../components/Stat';
import Subhead from '../components/Subhead';
import ShapContributionsChart from '../charts/ShapContributionsChart';
import { buildEvalRowLabels } from '../lib/detect';
import { ACCENT, ALERT, TEXT_FAINT, WARN } from '../theme/tokens';

const TOP_K = 10;

const RAW_COLUMNS = [
  { key: 'feature', label: 'Feature', render: (r) => r.feature },
  { key: 'raw', label: 'Raw value', render: (r) => r.raw },
  { key: 'shap', label: 'SHAP contribution (logit)', render: (r) => `${r.shap >= 0 ? '+' : ''}${r.shap.toFixed(4)}` },
];

export default function Explain({ eyebrow, title, lede }) {
  const evalStatus = useEvalRows();

  return (
    <>
      <SectionHeader eyebrow={eyebrow} title={title} lede={lede} />
      <Rule />
      {evalStatus.state === 'loading' && (
        <Callout tone={TEXT_FAINT}>Loading the 14 fixed evaluation rows (GET /shap)…</Callout>
      )}
      {evalStatus.state === 'error' && (
        <Callout tone={ALERT}>Could not load evaluation rows: {evalStatus.error}</Callout>
      )}
      {evalStatus.state === 'ok' && <ExplainBody rows={evalStatus.rows} />}
    </>
  );
}

function ExplainBody({ rows }) {
  const featureNames = rows[0].feature_names;
  const classNames = rows[0].class_names;
  const rowLabels = useMemo(() => buildEvalRowLabels(rows), [rows]);
  const [rowIdx, setRowIdx] = useState(0);
  const [explainTrue, setExplainTrue] = useState(false);

  const row = rows[rowIdx];
  const trueName = row.eval_family;
  const features = useMemo(
    () => Object.fromEntries(featureNames.map((n, i) => [n, row.raw_values[i]])),
    [featureNames, row],
  );

  const [predState, setPredState] = useState({ status: 'loading' });
  useEffect(() => {
    let cancelled = false;
    setPredState({ status: 'loading' });
    postPredict(features, trueName)
      .then((r) => {
        if (!cancelled) setPredState({ status: 'ok', result: r });
      })
      .catch((err) => {
        if (!cancelled) setPredState({ status: 'error', error: err.message });
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(features), trueName]);

  return (
    <div className="xf-grid-explain">
      <div>
        <Subhead title="Input" />
        <div style={{ height: 'var(--sp-sm)' }} />
        <div className="xf-field-label">Evaluation row</div>
        <select className="xf-select" value={rowIdx} onChange={(e) => setRowIdx(Number(e.target.value))}>
          {rowLabels.map((label, i) => (
            <option key={rows[i].sample_id} value={i}>
              {label}
            </option>
          ))}
        </select>
        <div style={{ height: 'var(--sp-sm)' }} />
        <div className="xf-caption" style={{ marginTop: 0 }}>
          True label: <b>{trueName}</b>
        </div>
        <div style={{ height: 'var(--sp-md)' }} />

        {predState.status === 'loading' && <Callout tone={TEXT_FAINT}>Predicting…</Callout>}
        {predState.status === 'error' && (
          <Callout tone={ALERT}>Could not get a prediction: {predState.error}</Callout>
        )}
        {predState.status === 'ok' && (
          <>
            <label className="xf-checkbox-option">
              <input
                type="checkbox"
                checked={explainTrue}
                onChange={(e) => setExplainTrue(e.target.checked)}
              />
              Explain the TRUE class ({trueName}) instead of the predicted class (
              {predState.result.family})
            </label>
            <div style={{ height: 'var(--sp-sm)' }} />
            <div className="xf-caption" style={{ marginTop: 0 }}>
              Reported agreement metrics (Jaccard@k, Kendall's τ) elsewhere in the project are
              computed relative to the TRUE class, for a stable ground truth across seeds and
              silos. This view defaults to the PREDICTED class instead — flip the box above to
              match the reported methodology exactly.
            </div>
            <div style={{ height: 'var(--sp-md)' }} />
            <Stat
              label="Additivity residual"
              value={row.additivity_max_diff.toFixed(3)}
              sub="Background size not exposed by this endpoint"
              tone={WARN}
            />
          </>
        )}
      </div>

      <div>
        {predState.status === 'ok' && (
          <ExplainRight
            row={row}
            featureNames={featureNames}
            classNames={classNames}
            className={explainTrue ? trueName : predState.result.family}
          />
        )}
      </div>
    </div>
  );
}

function ExplainRight({ row, featureNames, classNames, className }) {
  const classIdx = classNames.indexOf(className);

  const { chartData, baseValue, reconstructed } = useMemo(() => {
    const svRow = row.shap_values.map((f) => f[classIdx]);
    const base = row.base_values[classIdx];
    const order = svRow.map((_, i) => i).sort((a, b) => Math.abs(svRow[b]) - Math.abs(svRow[a]));
    const topIdx = order.slice(0, TOP_K);
    const restSum = order.slice(TOP_K).reduce((s, i) => s + svRow[i], 0);

    const data = topIdx.map((i) => ({ name: featureNames[i], value: svRow[i], raw: row.raw_values[i] }));
    data.push({ name: `Other ${featureNames.length - TOP_K} features (sum)`, value: restSum, raw: null });

    return {
      chartData: data,
      baseValue: base,
      reconstructed: base + svRow.reduce((a, b) => a + b, 0),
    };
  }, [row, classIdx, featureNames]);

  const rawTableRows = chartData
    .filter((d) => d.raw != null)
    .map((d) => ({ feature: d.name, raw: d.raw, shap: d.value }));

  return (
    <>
      <Subhead title={`Why "${className}"?`} />
      <div style={{ height: 'var(--sp-sm)' }} />
      <div className="xf-caption" style={{ marginTop: 0 }}>
        Base value (background mean logit for &apos;{className}&apos;):{' '}
        <b>
          {baseValue >= 0 ? '+' : ''}
          {baseValue.toFixed(3)}
        </b>{' '}
        → reconstructed model output for this row:{' '}
        <b>
          {reconstructed >= 0 ? '+' : ''}
          {reconstructed.toFixed(3)}
        </b>
      </div>
      <div style={{ height: 'var(--sp-md)' }} />

      <div className="xf-chart-card">
        <ShapContributionsChart data={chartData} />
      </div>
      <div style={{ height: 'var(--sp-sm)' }} />
      <Pills
        items={[
          ['↑ pushes toward this class', ALERT],
          ['↓ pushes away', ACCENT],
        ]}
      />
      <div style={{ height: 'var(--sp-md)' }} />

      <Expander title="Raw feature values (top 10)">
        <DataTable columns={RAW_COLUMNS} rows={rawTableRows} getRowKey={(r) => r.feature} />
      </Expander>
    </>
  );
}
