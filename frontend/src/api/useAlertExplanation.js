import { useEffect, useState } from 'react';
import { getExplain, getShap } from './client';

// Fetches the SHAP row and the precomputed sentence for one alert's
// shap_sample_id, from the pool named by source ('test' or 'val'). Mount it keyed by the alert so each alert starts in
// 'loading' without a synchronous setState inside the effect.
export function useAlertExplanation(sampleId, source = 'test') {
  const [state, setState] = useState({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    Promise.all([getShap(sampleId, source), getExplain(sampleId, source)])
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
