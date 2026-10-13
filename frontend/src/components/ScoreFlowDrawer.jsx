import { useEffect, useRef, useState } from 'react';
import { getShap, postPredict } from '../api/client';
import { parseCsvFlow, parsePastedFlow } from '../lib/detect';
import { pct } from '../lib/format';

// The old Detect custom-flow input, as a drawer. POST /predict without
// record_alert, so a scored flow never enters the alert stream. The only
// preset is the selected alert's own validation row (raw values from its
// SHAP pool entry, GET /shap/{id}?source=val); the 14 test rows Detect used are not offered.
export default function ScoreFlowDrawer({ open, onClose, featureNames, presetAlert }) {
  const ref = useRef(null);
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    else if (!open && d.open) d.close();
  }, [open]);

  const score = async (features) => {
    setBusy(true);
    setError(null);
    try {
      setResult(await postPredict(features));
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setBusy(false);
    }
  };

  const onSubmit = (e) => {
    e.preventDefault();
    try {
      score(parsePastedFlow(text, featureNames));
    } catch (err) {
      setError(err.message);
    }
  };

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      score(parseCsvFlow(await file.text(), featureNames));
    } catch (err) {
      setError(err.message);
    }
  };

  const canPreset = presetAlert?.shap_available && presetAlert.shap_sample_id != null;
  const loadPreset = async () => {
    try {
      const row = await getShap(presetAlert.shap_sample_id, presetAlert.shap_source ?? 'test');
      setText(row.raw_values.join(', '));
    } catch (err) {
      setError(err.message);
    }
  };

  const probs = result ? Object.entries(result.probabilities).sort((a, b) => b[1] - a[1]) : [];
  return (
    <dialog ref={ref} className="v-dialog v-drawer" aria-labelledby="sf-title" onClose={onClose}>
      <form onSubmit={onSubmit}>
        <div className="dlg-head">
          <div>
            <p className="eyebrow">POST /predict · not recorded as an alert</p>
            <h2 id="sf-title">Score a flow</h2>
          </div>
          <button type="button" className="btn" onClick={onClose} aria-label="Close drawer">✕</button>
        </div>
        <div className="dlg-body">
          <label className="field">
            Paste {featureNames.length} raw feature values, comma or space separated, in model column order
            <textarea value={text} onChange={(e) => setText(e.target.value)} spellCheck="false" />
          </label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
            <button type="submit" className="btn btn--lg btn--primary" disabled={busy || !text.trim()}>Score</button>
            <button
              type="button"
              className="btn btn--lg"
              disabled={!canPreset}
              onClick={loadPreset}
              title={canPreset ? undefined : 'The selected flow has no stored raw values'}
            >
              Load selected flow
            </button>
            <label className="btn btn--lg" style={{ cursor: 'pointer' }}>
              Upload 1-row CSV
              <input type="file" accept=".csv,text/csv" onChange={onFile} className="sr-only" />
            </label>
          </div>
          <details className="disc">
            <summary>Column order <span className="mono-mute">{featureNames.length} names</span></summary>
            <p className="mono-mute" style={{ overflowWrap: 'anywhere' }}>{featureNames.join(', ')}</p>
          </details>
          <div role="status" aria-live="polite">
            {error && <p className="note text-attack">{error}</p>}
            {result && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <p style={{ margin: 0, fontSize: 22, fontWeight: 600 }}>
                  {result.family} <span className="mono-mute">{pct(result.confidence)}</span>
                </p>
                {probs.map(([name, p]) => (
                  <div key={name} className="shap-row" style={{ gridTemplateColumns: '110px minmax(0,1fr) 64px' }}>
                    <span className="shap-label">{name}</span>
                    <div className="bar-track">
                      <div className="bar-fill" style={{ width: `${p * 100}%`, background: name === result.family ? 'var(--ok)' : 'var(--away)' }} />
                    </div>
                    <span className="shap-val">{pct(p, 2)}</span>
                  </div>
                ))}
                <p className="tiny">Served model, live. Not a stored result.</p>
              </div>
            )}
          </div>
        </div>
      </form>
    </dialog>
  );
}
