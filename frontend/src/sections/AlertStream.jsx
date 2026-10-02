import { useMemo, useState } from 'react';
import { useAlerts } from '../api/useAlerts';
import AlertExplainPanel from '../components/AlertExplainPanel';
import Callout from '../components/Callout';
import Rule from '../components/Rule';
import SectionHeader from '../components/SectionHeader';
import Stat from '../components/Stat';
import { ACCENT, ALERT, POSITIVE, TEXT_FAINT, familyColor } from '../theme/tokens';

function pillStyle(tone) {
  return { color: tone, borderColor: `${tone}55`, background: `${tone}14` };
}

function truthText(a) {
  if (a.true_family == null) return '';
  return a.true_family === a.predicted_family ? `✓ ${a.true_family}` : `✗ true: ${a.true_family}`;
}

export default function AlertStream({ eyebrow, title, lede }) {
  const feed = useAlerts();
  // Held as the alert object itself (not an index): the feed is a
  // newest-first ring buffer that shifts every tick, so an index would
  // silently point at a different alert a second later.
  const [selected, setSelected] = useState(null);
  const [shapOnly, setShapOnly] = useState(false);

  const alerts = feed.alerts;
  const nShap = useMemo(() => alerts.filter((a) => a.shap_available).length, [alerts]);
  const shown = useMemo(() => (shapOnly ? alerts.filter((a) => a.shap_available) : alerts), [alerts, shapOnly]);

  return (
    <>
      <SectionHeader eyebrow={eyebrow} title={title} lede={lede} />
      <Rule />

      {feed.status === 'error' && (
        <>
          <Callout tone={ALERT}>Could not refresh GET /alerts: {feed.error}</Callout>
          <div style={{ height: 'var(--sp-sm)' }} />
        </>
      )}

      <div className="xf-grid-2">
        <Stat label="Alerts in buffer" value={String(alerts.length)} sub="Most recent first" tone={ACCENT} small />
        <Stat
          label="With a precomputed SHAP explanation"
          value={`${nShap} of ${alerts.length}`}
          sub="Counted from the alerts currently in the buffer"
          tone={POSITIVE}
          small
        />
      </div>
      <div style={{ height: 'var(--sp-md)' }} />

      <div className="xf-grid-alerts">
        <div>
          <label className="xf-checkbox-option">
            <input type="checkbox" checked={shapOnly} onChange={(e) => setShapOnly(e.target.checked)} />
            Only alerts with SHAP
          </label>
          <div style={{ height: 'var(--sp-sm)' }} />
          {feed.status === 'loading' && <Callout tone={TEXT_FAINT}>Loading GET /alerts…</Callout>}
          {feed.status !== 'loading' && alerts.length === 0 && (
            <div className="xf-alert-panel xf-alert-panel--empty">
              No alerts yet. Alerts appear while the traffic simulator is running
              (<code>python -m backend.simulator</code>).
            </div>
          )}
          {alerts.length > 0 && shown.length === 0 && (
            <div className="xf-alert-panel xf-alert-panel--empty">
              None of the {alerts.length} alerts currently in the buffer has SHAP.
            </div>
          )}
          <div className="xf-alert-list">
            {shown.map((a) => (
              <button
                type="button"
                key={a.timestamp}
                className={`xf-alert-row${selected?.timestamp === a.timestamp ? ' selected' : ''}`}
                onClick={() => setSelected(a)}
              >
                <span className="xf-alert-time">{new Date(a.timestamp).toLocaleTimeString()}</span>
                <span className="xf-pill" style={pillStyle(familyColor(a.predicted_family))}>
                  {a.predicted_family}
                </span>
                <span className="xf-alert-conf">{(a.confidence * 100).toFixed(1)}%</span>
                <span className="xf-alert-truth">{truthText(a)}</span>
                {a.shap_available && (
                  <span className="xf-pill" style={pillStyle(ACCENT)}>
                    SHAP
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        <AlertExplainPanel alert={selected} />
      </div>
    </>
  );
}
