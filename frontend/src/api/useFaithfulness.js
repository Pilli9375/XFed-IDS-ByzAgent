import { useEffect, useState } from 'react';
import { getFaithfulness } from './client';

export function useFaithfulness() {
  const [status, setStatus] = useState({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    getFaithfulness()
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
