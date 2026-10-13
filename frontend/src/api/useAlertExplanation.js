import { useEffect, useState } from 'react';
import { getExplain, getShap } from './client';

// SHAP row + stored sentence for one alert's shap_sample_id, from the pool
// named by source ('test' or 'val'). Promises are cached per id so Live can
// prefetch the selected flow's explanation while its skeleton is still up.
const cache = new Map();

export function fetchExplanation(sampleId, source = 'test') {
  const key = `${source}:${sampleId}`;
  if (!cache.has(key)) {
    const p = Promise.all([getShap(sampleId, source), getExplain(sampleId, source)]).then(([shap, explain]) => ({ shap, explain }));
    p.catch(() => cache.delete(key));
    cache.set(key, p);
  }
  return cache.get(key);
}

export function useAlertExplanation(sampleId, source = 'test') {
  const [state, setState] = useState({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    fetchExplanation(sampleId, source)
      .then(({ shap, explain }) => {
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
