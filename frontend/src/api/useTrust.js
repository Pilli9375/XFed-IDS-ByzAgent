import { useEffect, useState } from 'react';
import { getTrust } from './client';

// Fetches GET /trust once on mount. Same {state, ...} shape as
// useBackendStatus/useAgreement -- 'loading' | 'ok' (data) | 'error' (error).
export function useTrust() {
  const [status, setStatus] = useState({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    getTrust()
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
