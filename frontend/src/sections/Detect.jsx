import { useEffect, useMemo, useState } from 'react';
import { postPredict } from '../api/client';
import { useEvalRows } from '../api/useEvalRows';
import Callout from '../components/Callout';
import Expander from '../components/Expander';
import Rule from '../components/Rule';
import SectionHeader from '../components/SectionHeader';
import Subhead from '../components/Subhead';
import Verdict from '../components/Verdict';
import ClassConfidenceChart from '../charts/ClassConfidenceChart';
import { buildEvalRowLabels, confidenceTier, evalRowTemplateText, parseCsvFlow, parsePastedFlow } from '../lib/detect';
import { ALERT, TEXT_FAINT, WARN, familyColor } from '../theme/tokens';

export default function Detect({ eyebrow, title, lede }) {
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
      {evalStatus.state === 'ok' && <DetectBody rows={evalStatus.rows} />}
    </>
  );
}

function DetectBody({ rows }) {
  const featureNames = rows[0].feature_names;
  const rowLabels = useMemo(() => buildEvalRowLabels(rows), [rows]);
  const [mode, setMode] = useState('preset');
  const [rowIdx, setRowIdx] = useState(0);

  const [pasteText, setPasteText] = useState('');
  const [uploadedText, setUploadedText] = useState(null);
  const [uploadName, setUploadName] = useState(null);

  // Pure parse of whatever input is currently present -- derived during
  // render, not an effect: nothing external to synchronize with here.
  const { customFeatures, parseError } = useMemo(() => {
    const source = uploadedText ?? pasteText;
    if (!source || !source.trim()) {
      return { customFeatures: null, parseError: null };
    }
    try {
      const features = uploadedText
        ? parseCsvFlow(uploadedText, featureNames)
        : parsePastedFlow(pasteText, featureNames);
      return { customFeatures: features, parseError: null };
    } catch (err) {
      return { customFeatures: null, parseError: err.message };
    }
  }, [pasteText, uploadedText, featureNames]);

  const presetRow = rows[rowIdx];
  const presetFeatures = useMemo(
    () => Object.fromEntries(featureNames.map((n, i) => [n, presetRow.raw_values[i]])),
    [featureNames, presetRow],
  );

  const handleFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadName(file.name);
    const reader = new FileReader();
    reader.onload = () => setUploadedText(String(reader.result));
    reader.readAsText(file);
  };

  return (
    <div className="xf-grid-2">
      <div>
        <Subhead title="Input" />
        <div style={{ height: 'var(--sp-sm)' }} />

        <div className="xf-radio-group">
          <label className="xf-radio-option">
            <input
              type="radio"
              name="flow-source"
              checked={mode === 'preset'}
              onChange={() => setMode('preset')}
            />
            Preset evaluation row
          </label>
          <label className="xf-radio-option">
            <input
              type="radio"
              name="flow-source"
              checked={mode === 'custom'}
              onChange={() => setMode('custom')}
            />
            Custom flow
          </label>
        </div>
        <div style={{ height: 'var(--sp-md)' }} />

        {mode === 'preset' ? (
          <>
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
              True label: <b>{presetRow.eval_family}</b>
            </div>
            <div className="xf-caption">
              These 14 rows are fixed and reused everywhere in the app — the same ones behind
              every SHAP explanation in Explain.
            </div>
          </>
        ) : (
          <>
            <div className="xf-caption" style={{ marginTop: 0 }}>
              Paste {featureNames.length} comma- or space-separated raw feature values, or
              upload a one-row CSV. Values must be <b>unscaled</b> — the app applies the
              training scaler itself.
            </div>
            <div style={{ height: 'var(--sp-sm)' }} />
            <input className="xf-file-input" type="file" accept=".csv" onChange={handleFile} />
            {uploadName && <div className="xf-caption">Loaded: {uploadName}</div>}
            <div style={{ height: 'var(--sp-sm)' }} />
            <textarea
              className="xf-textarea"
              rows={5}
              placeholder="0, 1234, 5, 3, ..."
              value={pasteText}
              onChange={(e) => {
                setPasteText(e.target.value);
                setUploadedText(null);
                setUploadName(null);
              }}
            />
            {parseError && (
              <>
                <div style={{ height: 'var(--sp-xs)' }} />
                <Callout tone={ALERT}>{parseError}</Callout>
              </>
            )}
            <div style={{ height: 'var(--sp-sm)' }} />
            <Expander title="Need a template?">
              <div className="xf-caption" style={{ marginTop: 0 }}>
                Copy this correctly-shaped row (it's eval row 1) and edit the values.
              </div>
              <div style={{ height: 'var(--sp-xs)' }} />
              <div className="xf-code-block">{evalRowTemplateText(rows[0])}</div>
            </Expander>
          </>
        )}
      </div>

      <div>
        <Subhead title="Prediction" />
        <div style={{ height: 'var(--sp-sm)' }} />
        {mode === 'preset' ? (
          <PredictionResult features={presetFeatures} trueName={presetRow.eval_family} />
        ) : (
          <>
            <Callout tone={WARN}>
              <b>Prediction only — no explanation for custom flows.</b> SHAP explanations
              come from precomputed artifacts covering the fixed 14 evaluation rows. An
              arbitrary flow has no stored explanation, and this app never computes one on
              demand. Use a preset row if you need the explanation too.
            </Callout>
            <div style={{ height: 'var(--sp-sm)' }} />
            {customFeatures ? (
              <PredictionResult features={customFeatures} trueName={null} />
            ) : (
              <div className="xf-caption" style={{ marginTop: 0 }}>
                Waiting for input.
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function PredictionResult({ features, trueName }) {
  const [state, setState] = useState({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading' });
    postPredict(features, trueName)
      .then((r) => {
        if (!cancelled) setState({ status: 'ok', result: r });
      })
      .catch((err) => {
        if (!cancelled) setState({ status: 'error', error: err.message });
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(features), trueName]);

  if (state.status === 'loading') return <Callout tone={TEXT_FAINT}>Predicting…</Callout>;
  if (state.status === 'error') {
    return <Callout tone={ALERT}>Could not get a prediction: {state.error}</Callout>;
  }

  const { family, confidence, probabilities } = state.result;
  const tier = confidenceTier(confidence);
  let tone = familyColor(family);
  let meta;
  if (trueName == null) {
    meta = `Confidence <b>${(confidence * 100).toFixed(1)}%</b> · ${tier} · no ground-truth label for a custom flow`;
  } else {
    const hit = family === trueName;
    const mark = hit ? '✓ matches' : '✗ differs from';
    meta = `Confidence <b>${(confidence * 100).toFixed(1)}%</b> · ${tier} · ${mark} true label <b>${trueName}</b>`;
    if (!hit) tone = WARN;
  }

  return (
    <>
      <Verdict name={family} meta={meta} tone={tone} />
      <div style={{ height: 'var(--sp-sm)' }} />
      <div className="xf-stat-label">Class confidence</div>
      <div style={{ height: 'var(--sp-xs)' }} />
      <div className="xf-chart-card">
        <ClassConfidenceChart probs={probabilities} />
      </div>
    </>
  );
}
