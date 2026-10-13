import { useEffect, useState } from 'react';

// One GET per key, fetched once and cached for the life of the page, so
// switching routes or themes does not refetch static results. When `key`
// changes (e.g. /config after a hot-swap toggles), the hook answers for the
// new key: from the cache if present, otherwise loading until it arrives,
// or, with `keepGroup`, the last data any key in that group returned (so a
// refetch never blanks what is on screen).
const cache = new Map();
const lastByGroup = new Map();

export function useResource(key, fetcher, keepGroup) {
  const [results, setResults] = useState({});
  useEffect(() => {
    if (cache.has(key)) return undefined;
    let cancelled = false;
    fetcher()
      .then((data) => {
        cache.set(key, data);
        if (keepGroup) lastByGroup.set(keepGroup, data);
        if (!cancelled) setResults((r) => ({ ...r, [key]: { status: 'ok', data } }));
      })
      .catch((err) => {
        if (!cancelled) setResults((r) => ({ ...r, [key]: { status: 'error', data: null, error: err.message } }));
      });
    return () => {
      cancelled = true;
    };
    // fetcher is a stable module function per key
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  if (cache.has(key)) return { status: 'ok', data: cache.get(key) };
  if (keepGroup && lastByGroup.has(keepGroup) && !results[key]) return { status: 'ok', data: lastByGroup.get(keepGroup), stale: true };
  return results[key] ?? { status: 'loading', data: null };
}
