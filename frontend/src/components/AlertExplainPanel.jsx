import { useMemo } from 'react';
import { useAlertExplanation } from '../api/useAlertExplanation';
import Callout from './Callout';
import Pills from './Pills';
import ShapContributionsChart from '../charts/ShapContributionsChart';
import { buildShapView } from '../lib/shap';
import { ACCENT, ALERT, TEXT_FAINT, WARN, familyColor } from '../theme/tokens';

// Detail panel for ONE alert in the Alert Stream. Three honest states:
//   - nothing selected,
//   - selected but no precomputed SHAP exists (the common case: say so
//     plainly -- no empty chart, no spinner that never resolves),
//   - selected with SHAP: the same ShapContributionsChart Explain uses, plus
//     the precomputed sentence in a visually separate "analyst aid" block.
export default function AlertExplainPanel({ alert }) {
  if (!alert) {
    return (
      <div className="xf-alert-panel xf-alert-panel--empty">
        Select an alert to inspect it. Alerts tagged <b>SHAP</b> have a precomputed explanation.
      </div>
    );
  }

  return (
    <div className="xf-alert-panel">
      <AlertSummary alert={alert} />
      {alert.shap_available && alert.shap_sample_id != null ? (
        <ExplanationBody key={alert.timestamp} alert={alert} />
      ) : (
        <div className="xf-alert-nosnap">
          <b>No SHAP explanation for this alert.</b> SHAP values are precomputed offline for a
          small fixed set of streamed rows, and this alert&apos;s row is not in it. The dashboard
          never computes SHAP on demand, so there is nothing to show here — this is not an error.
        </div>
      )}
    </div>
  );
}

function AlertSummary({ alert }) {
  const tone = familyColor(alert.predicted_family);
  const truth =
    alert.true_family == null
      ? 'no ground-truth label'
      : alert.true_family === alert.predicted_family
        ? `✓ matches true label ${alert.true_family}`
        : `✗ differs from true label ${alert.true_family}`;
  return (
    <div className="xf-alert-summary" style={{ '--tone': tone }}>
      <div className="xf-alert-summary__family">{alert.predicted_family}</div>
      <div className="xf-alert-summary__meta">
        Confidence <b>{(alert.confidence * 100).toFixed(1)}%</b> · {truth} ·{' '}
        {new Date(alert.timestamp).toLocaleString()}
      </div>
    </div>
  );
}

function ExplanationBody({ alert }) {
  const state = useAlertExplanation(alert.shap_sample_id);

  if (state.status === 'loading') return <Callout tone={TEXT_FAINT}>Loading explanation…</Callout>;
  if (state.status === 'error') {
    return (
      <Callout tone={ALERT}>
        This alert is tagged as having SHAP, but loading it failed: {state.error}
      </Callout>
    );
  }
  return <ExplanationView alert={alert} shap={state.shap} explain={state.explain} />;
}

function ExplanationView({ alert, shap, explain }) {
  // Chart the class the sentence is about (the base model's prediction for
  // this row), not blindly the alert's own label -- see the mismatch note.
  const classIdx = shap.class_names.indexOf(explain.predicted_family);
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
  const mismatch = explain.predicted_family !== alert.predicted_family;
  const signed = (v) => `${v >= 0 ? '+' : ''}${v.toFixed(3)}`;

  return (
    <>
      <div className="xf-analyst-aid">
        <div className="xf-analyst-aid__label">Analyst aid · not a research result</div>
        <p className="xf-analyst-aid__sentence">{explain.sentence}</p>
        <div className="xf-analyst-aid__note">
          Written offline by a local language model from this row&apos;s top 5 SHAP features, then
          stored — not generated live, and its wording is not independently checked against the
          numbers. The chart below is the evidence; the sentence is a reading aid. Precomputed
          against <code>{explain.tag}</code>; if a hot-swap is active, the alert itself may have
          come from a different model.
        </div>
      </div>

      {mismatch && (
        <>
          <div style={{ height: 'var(--sp-sm)' }} />
          <Callout tone={WARN}>
            This alert was labelled <b>{alert.predicted_family}</b>, but the precomputed
            explanation describes the base model&apos;s prediction for this row,{' '}
            <b>{explain.predicted_family}</b>.
          </Callout>
        </>
      )}

      <div style={{ height: 'var(--sp-md)' }} />
      <div className="xf-caption" style={{ marginTop: 0 }}>
        SHAP contributions toward <b>{explain.predicted_family}</b> (logit space). Base value{' '}
        <b>{signed(view.baseValue)}</b> → reconstructed model output{' '}
        <b>{signed(view.reconstructed)}</b>. Additivity residual for this row:{' '}
        {shap.additivity_max_diff.toFixed(3)}.
      </div>
      <div style={{ height: 'var(--sp-sm)' }} />
      <div className="xf-chart-card">
        <ShapContributionsChart data={view.chartData} />
      </div>
      <div style={{ height: 'var(--sp-sm)' }} />
      <Pills
        items={[
          ['↑ pushes toward this class', ALERT],
          ['↓ pushes away', ACCENT],
        ]}
      />
    </>
  );
}
