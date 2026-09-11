import { useEffect, useState } from 'react';
import { getAgreement } from './client';

// Fetches GET /agreement once on mount. Same {state, ...} shape as
// useBackendStatus -- 'loading' | 'ok' (data) | 'error' (error).
export function useAgreement() {
  const [status, setStatus] = useState({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    getAgreement()
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
