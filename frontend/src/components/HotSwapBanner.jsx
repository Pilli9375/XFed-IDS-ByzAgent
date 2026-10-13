import { useState } from 'react';

// Same states and wording rules as the original banner (frontend/src/
// components/HotSwapBanner.jsx): once a swap is active, /predict answers
// from a model the rest of the dashboard's numbers do not describe, and
// that must be on screen. Status comes from the shared hot-swap poll.
export default function HotSwapBanner({ hs }) {
  const [reverting, setReverting] = useState(false);
  const status = hs.status;
  if (!status) return null;
  const { hotswap, status: jobStatus, detail, family } = status;

  if (hotswap.active) {
    return (
      <div className="v-banner is-active" role="status">
        <span>
          <strong>Hot-swap active.</strong> /predict is answered by hot-swap event <code className="mono">{hotswap.event_id}</code>{' '}
          (swap depth {hotswap.swap_depth}), not {hotswap.base_tag}. Every other number on this dashboard was computed
          against {hotswap.base_tag}.
        </span>
        <button
          type="button"
          className="btn"
          disabled={reverting}
          onClick={async () => {
            setReverting(true);
            try {
              await hs.revert();
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
      <div className="v-banner" role="status">
        <span>Hot-swap retraining in progress ({family ?? 'unknown family'}). The served model has not changed yet.</span>
      </div>
    );
  }
  if (jobStatus === 'crashed' || jobStatus === 'error') {
    return (
      <div className="v-banner is-warn" role="status">
        <span>
          Last hot-swap attempt did not complete ({jobStatus}). Served model is unchanged ({hotswap.base_tag}).{' '}
          {detail && <span className="mono-mute">{detail}</span>}
        </span>
      </div>
    );
  }
  return null;
}
