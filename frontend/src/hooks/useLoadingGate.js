import { useEffect, useState } from 'react';

// Skeleton stays up until the view's endpoints have resolved AND at least
// MIN_MS have passed since the last (re)start, so it never flashes. `epoch`
// restarts the gate (a theme switch replays the bloom). Once open for an
// epoch it stays open, even if `ready` later flips back.
export const MIN_MS = 600;

export function useLoadingGate(ready, epoch) {
  const [elapsed, setElapsed] = useState(-1);
  const [opened, setOpened] = useState(-1);
  useEffect(() => {
    const t = setTimeout(() => setElapsed(epoch), MIN_MS);
    return () => clearTimeout(t);
  }, [epoch]);
  const open = opened === epoch || (ready && elapsed === epoch);
  // Latch during render (React's "adjust state on prop change" pattern).
  if (open && opened !== epoch) setOpened(epoch);
  return !open;
}
