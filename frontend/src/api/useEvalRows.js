import { useEffect, useState } from 'react';
import { getShap } from './client';

const N_EVAL_ROWS = 14; // GET /shap/{id} is positional over sample_id in [0,13] only

// Fetches all 14 fixed evaluation rows once (GET /shap/0..13 in parallel).
// Each row's raw_values + feature_names now come from the same response
// SHAP itself does, so this single fetch backs both Detect's preset-row
// prediction and Explain's SHAP view -- one data path, not two.
export function useEvalRows() {
  const [status, setStatus] = useState({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    Promise.all(Array.from({ length: N_EVAL_ROWS }, (_, i) => getShap(i)))
      .then((rows) => {
        if (!cancelled) setStatus({ state: 'ok', rows });
      })
      .catch((err) => {
        if (!cancelled) setStatus({ state: 'error', error: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return status;
}
