import { useEffect, useRef, useState } from 'react';
import { postHotswapTrigger } from '../api/client';

// Real <dialog>: confirm or correct the alert's family, then POST
// /hotswap/trigger. Status afterwards comes from the shared hot-swap poll,
// read the same way the banner reads it. Closes inventory item 5.2.
export default function HotSwapDialog({ open, onClose, alert, classNames, hs }) {
  const ref = useRef(null);
  const [family, setFamily] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [startedJob, setStartedJob] = useState(null);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      setFamily(alert?.predicted_family ?? classNames[0] ?? '');
      setError(null);
      setStartedJob(null);
      d.showModal();
    } else if (!open && d.open) {
      d.close();
    }
  }, [open, alert, classNames]);

  const job = hs.status;
  const running = job?.status === 'running';
  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await postHotswapTrigger(family);
      setStartedJob(res.job_id);
      hs.refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const confirming = alert && family === alert.predicted_family;
  return (
    <dialog ref={ref} className="v-dialog" aria-labelledby="hs-title" onClose={onClose}>
      <form onSubmit={submit}>
        <div className="dlg-head">
          <div>
            <p className="eyebrow">Analyst action</p>
            <h2 id="hs-title">Hot-swap model</h2>
          </div>
          <button type="button" className="btn" onClick={onClose} aria-label="Close dialog">✕</button>
        </div>
        <div className="dlg-body">
          <p className="note">
            Confirm the family for this flow, or correct it. The backend then retrains a candidate from the base model in a
            separate process. The candidate replaces the served model only if it clears the validation non-regression gate;
            otherwise nothing changes. Only the family label is sent, never the flow&apos;s features.
          </p>
          <label className="field">
            Family for this flow
            <select className="v-select" value={family} onChange={(e) => setFamily(e.target.value)} disabled={submitting || running}>
              {classNames.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </label>
          {alert && (
            <p className="small">
              Model predicted <b>{alert.predicted_family}</b>
              {alert.true_family != null && <> · true label {alert.true_family}</>} ·{' '}
              {confirming ? 'you are confirming the prediction' : 'you are correcting the prediction'}
            </p>
          )}
          <div className="status-box" role="status" aria-live="polite">
            {error ? (
              <span className="text-attack">{error}</span>
            ) : running ? (
              <>Retraining for {job.family ?? family}… the served model has not changed yet.</>
            ) : startedJob && job?.job_id === startedJob && job.status ? (
              <>
                Job {job.status}.{' '}
                {job.status === 'accepted' && <>Candidate swapped in (event {job.hotswap.event_id}). The banner above the page can revert it.</>}
                {job.status === 'rejected' && <>The candidate did not clear the gate; the served model is unchanged.</>}
                {(job.status === 'error' || job.status === 'crashed') && <>The served model is unchanged. {job.detail}</>}
              </>
            ) : job?.hotswap?.active ? (
              <>A hot-swap is already active (event {job.hotswap.event_id}). A new one warm-starts from the base model again.</>
            ) : (
              <>No retraining job running.</>
            )}
          </div>
        </div>
        <div className="dlg-foot">
          <button type="button" className="btn btn--lg" onClick={onClose}>Close</button>
          <button type="submit" className="btn btn--lg btn--primary" disabled={submitting || running || !family}>
            {submitting ? 'Starting…' : confirming ? 'Confirm and retrain' : 'Correct and retrain'}
          </button>
        </div>
      </form>
    </dialog>
  );
}
