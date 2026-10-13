import { useEffect, useState } from 'react';
import { getExplain, getShap } from './client';

// Fetches the SHAP row and, for test-pool rows only, the precomputed
// sentence for one alert's shap_sample_id. Validation-pool rows have no
// sentence (none was generated), so explain is null for them -- never a
// failed request standing in for "no sentence". Mount it keyed by the alert so each alert starts in
// 'loading' without a synchronous setState inside the effect.
export function useAlertExplanation(sampleId, source = 'test') {
  const [state, setState] = useState({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    Promise.all([getShap(sampleId, source), source === 'val' ? null : getExplain(sampleId)])
      .then(([shap, explain]) => {
        if (!cancelled) setState({ status: 'ok', shap, explain });
      })
      .catch((err) => {
        if (!cancelled) setState({ status: 'error', error: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [sampleId, source]);

  return state;
}
