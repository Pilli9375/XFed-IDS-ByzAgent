import { useCallback, useEffect, useRef, useState } from 'react';
import { getHotswapStatus, postHotswapRevert, postHotswapTrigger } from './client';

// Polls GET /hotswap/status regardless of which section is mounted (the
// banner using this lives above <Routes>, not inside a section) -- a
// hot-swap job can finish while the analyst is looking at an unrelated
// chart, and the banner must catch that without a manual refresh.
const POLL_MS = 3000;

export function useHotSwapStatus() {
  const [status, setStatus] = useState(null); // null until the first fetch resolves
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  const refresh = useCallback(() => {
    getHotswapStatus()
      .then((s) => setStatus(s))
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    refresh();
    timerRef.current = setInterval(refresh, POLL_MS);
    return () => clearInterval(timerRef.current);
  }, [refresh]);

  const trigger = useCallback(
    async (family) => {
      await postHotswapTrigger(family);
      refresh();
    },
    [refresh],
  );

  const revert = useCallback(async () => {
    await postHotswapRevert();
    refresh();
  }, [refresh]);

  return { status, error, trigger, revert, refresh };
}
