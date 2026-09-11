import { useEffect, useState } from 'react';
import { getFederation } from './client';

export function useFederation() {
  const [status, setStatus] = useState({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    getFederation()
      .then((data) => {
        if (!cancelled) setStatus({ state: 'ok', data });
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
