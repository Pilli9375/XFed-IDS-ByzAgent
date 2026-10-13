import { useEffect, useState } from 'react';

// Skeleton stays up until the view's endpoints have resolved AND at least
// MIN_MS have passed since the last (re)start, so it never flashes. `epoch`
// restarts the gate (theme switch replays the bloom).
export const MIN_MS = 600;

export function useLoadingGate(ready, epoch) {
  const [elapsed, setElapsed] = useState({ epoch: -1 });
  useEffect(() => {
    const t = setTimeout(() => setElapsed({ epoch }), MIN_MS);
    return () => clearTimeout(t);
  }, [epoch]);
  return !(ready && elapsed.epoch === epoch);
}
