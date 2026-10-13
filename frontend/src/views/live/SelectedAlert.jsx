import { useMemo } from 'react';
import { useAlertExplanation } from '../../api/useAlertExplanation';
import { Sources } from '../../components/Src';
import { BENIGN, isMiss } from '../../lib/alerts';
import { fixed, pct, signed, timeOf } from '../../lib/format';
import { buildShapView } from '../../lib/shap';

const RING_R = 27;
const RING_C = 2 * Math.PI * RING_R;

// The selected flow: confidence ring, verdict against the true label, the
// stored LLM sentence and the SHAP contributions toward the predicted class.
export default function SelectedAlert({ alert, reviewed, onToggleReviewed, onHotSwap, sources }) {
  if (!alert) {
    return (
      <section aria-labelledby="why-h" className="panel p-why">
        <div className="why-body">
          <h2 id="why-h" className="sr-only">Selected flow</h2>
          <p className="note">No flow selected yet. Flows arrive while the traffic simulator runs.</p>
        </div>
      </section>
    );
  }
  const attack = alert.predicted_family !== BENIGN;
  const miss = isMiss(alert);
  const ringColor = attack ? 'var(--attack)' : 'var(--ok)';
  return (
    <section aria-labelledby="why-h" className="panel p-why">
      <div className="why-head">
        <svg width="64" height="64" viewBox="0 0 64 64" role="img" aria-label={`Confidence ${pct(alert.confidence)}`}>
          <circle cx="32" cy="32" r={RING_R} fill="none" stroke="var(--line)" strokeWidth="5" />
          <circle
            cx="32" cy="32" r={RING_R} fill="none" stroke={ringColor} strokeWidth="5" strokeLinecap="round"
            strokeDasharray={`${alert.confidence * RING_C} ${RING_C}`} transform="rotate(-90 32 32)"
          />
          <text x="32" y="36" textAnchor="middle" fontSize="11" fill="var(--ink)">
            {pct(alert.confidence)}
          </text>
        </svg>
        <div style={{ flex: '1 1 240px', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <span className="eyebrow">Selected · flow {timeOf(alert.timestamp)}</span>
          <h2 id="why-h" className="why-title">
            {alert.predicted_family}{' '}
            {alert.true_family == null ? (
              <span className="why-verdict text-mute">no true label</span>
            ) : miss ? (
              <span className="why-verdict text-attack">✗ true label {alert.true_family}</span>
            ) : (
              <span className="why-verdict text-ok">✓ matches true label</span>
            )}
          </h2>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button type="button" className="btn btn--lg" aria-pressed={reviewed} onClick={onToggleReviewed}>
            {reviewed ? '✓ Reviewed' : 'Mark reviewed'}
          </button>
          <button type="button" className="btn btn--lg btn--primary" onClick={onHotSwap}>
            Hot-swap model…
          </button>
        </div>
      </div>
      {alert.shap_available && alert.shap_sample_id != null ? (
        <Explanation key={`${alert.shap_source}:${alert.shap_sample_id}`} alert={alert} sources={sources} />
      ) : (
        <div className="why-body">
          <p className="note">
            This flow is not in a precomputed SHAP pool, so there is no explanation to show. The dashboard never computes
            SHAP on demand.
          </p>
        </div>
      )}
    </section>
  );
}

function Explanation({ alert, sources }) {
  const state = useAlertExplanation(alert.shap_sample_id, alert.shap_source ?? 'test');
  if (state.status === 'loading') {
    return (
      <div className="why-body" aria-busy="true">
        <div className="shim" style={{ height: 14 }} />
        <div className="shim" style={{ height: 14, width: '70%' }} />
      </div>
    );
  }
  if (state.status === 'error') {
    return (
      <div className="why-body">
        <p className="note text-attack">This flow is tagged as having SHAP, but loading it failed: {state.error}</p>
      </div>
    );
  }
  return <ExplanationView alert={alert} shap={state.shap} explain={state.explain} sources={sources} />;
}

function ExplanationView({ alert, shap, explain, sources }) {
  // Chart the class the stored sentence is about: the base model's
  // prediction for this row (differs from the alert only under a hot-swap).
  const family = explain.predicted_family;
  const classIdx = shap.class_names.indexOf(family);
  const view = useMemo(
    () =>
      buildShapView({
        shapValues: shap.shap_values,
        rawValues: shap.raw_values,
        baseValues: shap.base_values,
        featureNames: shap.feature_names,
        classIdx,
      }),
    [shap, classIdx],
  );
  const rows = [...view.chartData].sort((a, b) => b.value - a.value);
  const maxAbs = Math.max(...rows.map((r) => Math.abs(r.value)), 1e-9);
  const toward = family === BENIGN ? 'var(--ok)' : 'var(--attack)';
  return (
    <div className="why-body">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <span className="eyebrow eyebrow--agent">LLM-generated summary · not a research result</span>
        <p className="llm-text">{explain.sentence}</p>
      </div>
      {family !== alert.predicted_family && (
        <p className="note text-agent">
          This flow was labelled {alert.predicted_family} by the model serving now, but the stored explanation describes the
          base model&apos;s prediction, {family}.
        </p>
      )}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' }}>
        <h3 style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>Why — SHAP contribution toward {family}</h3>
        <span className="mono-mute">
          logit · base {signed(view.baseValue)} → {signed(view.reconstructed)} · residual {fixed(shap.additivity_max_diff)}
        </span>
      </div>
      <div role="img" aria-label={`Top SHAP contributions toward ${family} for this flow`} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {rows.map((r) => {
          const w = (Math.abs(r.value) / maxAbs) * 50;
          return (
            <div key={r.name} className="shap-row">
              <span className="shap-label" title={r.name}>{r.name}</span>
              <div className="shap-track">
                <div
                  className="shap-bar"
                  style={r.value >= 0 ? { left: '50%', width: `${w}%`, background: toward } : { right: '50%', width: `${w}%`, background: 'var(--away)' }}
                />
              </div>
              <span className="shap-val">{signed(r.value, 2)}</span>
            </div>
          );
        })}
      </div>
      <div className="legend">
        <span><i style={{ background: toward }} />pushes toward {family}</span>
        <span><i style={{ background: 'var(--away)' }} />pushes away</span>
        <span className="text-mute">residual = max |ΣSHAP − (f(x) − E f)| over classes, logit</span>
      </div>
      <Sources paths={[sources.sentences, sources.shap]} />
    </div>
  );
}
