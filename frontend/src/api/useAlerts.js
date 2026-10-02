import { useEffect, useState } from 'react';
import { getAlerts } from './client';

// Polls GET /alerts. A failed poll keeps the last good list on screen and
// reports the error alongside it, rather than blanking the feed.
export function useAlerts(intervalMs = 2000) {
  const [state, setState] = useState({ status: 'loading', alerts: [] });

  useEffect(() => {
    let cancelled = false;
    let timer;
    const tick = async () => {
      try {
        const alerts = await getAlerts();
        if (!cancelled) setState({ status: 'ok', alerts });
      } catch (err) {
        if (!cancelled) setState((prev) => ({ status: 'error', error: err.message, alerts: prev.alerts }));
      }
      if (!cancelled) timer = setTimeout(tick, intervalMs);
    };
    tick();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [intervalMs]);

  return state;
}
