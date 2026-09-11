import { useEffect, useState } from 'react';
import { getConfig, getHealth } from './client';

// Fetches GET /health and GET /config once on mount. This is the thing that
// proves the frontend actually talks to the backend, not a fixture --
// Sidebar renders the result as the loaded-model identity in the sidebar
// footer.
export function useBackendStatus() {
  const [status, setStatus] = useState({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    Promise.all([getHealth(), getConfig()])
      .then(([health, config]) => {
        if (!cancelled) setStatus({ state: 'ok', health, config });
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
