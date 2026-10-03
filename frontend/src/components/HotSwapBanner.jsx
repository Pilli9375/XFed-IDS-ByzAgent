import { useState } from 'react';
import { useHotSwapStatus } from '../api/useHotSwapStatus';

// Rendered once in App.jsx, above <Routes> -- visible on every section,
// not just Detect/Explain. This exists for one reason: once a hot-swap is
// active, /predict answers from a DIFFERENT model than the one every other
// number on this dashboard (agreement, parity, faithfulness, federation)
// was computed against. A viewer who doesn't know that reads a stale
// number as if it described live behavior. Silence here is the failure
// mode this component exists to prevent -- see the Step 2 design note:
// "A dashboard showing the explanation check's reported metrics next to a
// silently-swapped model is the worst outcome this feature can produce."
export default function HotSwapBanner() {
  const { status, revert } = useHotSwapStatus();
  const [reverting, setReverting] = useState(false);

  if (!status) return null; // first poll hasn't resolved yet

  const { hotswap, status: jobStatus, detail, family } = status;

  if (hotswap.active) {
    return (
      <div className="xf-hotswap-banner xf-hotswap-banner--active">
        <div className="xf-hotswap-banner__text">
          <strong>Hot-swap active.</strong> The model answering Detect/Explain right
          now is <strong>not</strong> {hotswap.base_tag} — it is hot-swap event{' '}
          <code>{hotswap.event_id}</code> (swap depth {hotswap.swap_depth}). Every
          other number on this dashboard (agreement, parity, faithfulness,
          federation) was computed against {hotswap.base_tag} and does <strong>not</strong>{' '}
          describe the model currently serving predictions.
        </div>
        <button
          type="button"
          className="xf-hotswap-banner__revert"
          disabled={reverting}
          onClick={async () => {
            setReverting(true);
            try {
              await revert();
            } finally {
              setReverting(false);
            }
          }}
        >
          {reverting ? 'Reverting…' : 'Revert to base model'}
        </button>
      </div>
    );
  }

  if (jobStatus === 'running') {
    return (
      <div className="xf-hotswap-banner xf-hotswap-banner--running">
        Hot-swap retraining in progress ({family ?? 'unknown family'})… the served
        model has not changed yet.
      </div>
    );
  }

  if (jobStatus === 'crashed' || jobStatus === 'error') {
    return (
      <div className="xf-hotswap-banner xf-hotswap-banner--warn">
        Last hot-swap attempt did not complete ({jobStatus}) — served model is
        unchanged ({hotswap.base_tag}).{' '}
        {detail && <span className="xf-hotswap-banner__detail">{detail}</span>}
      </div>
    );
  }

  return null; // inactive, no job, or last job was a clean "rejected" -- nothing to warn about
}
