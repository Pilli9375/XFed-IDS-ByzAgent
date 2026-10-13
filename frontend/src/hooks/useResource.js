import { useEffect, useState } from 'react';

// One GET, fetched once on mount. Results are cached per key for the life of
// the page, so switching routes or themes does not refetch static results.
const cache = new Map();

export function useResource(key, fetcher) {
  const [state, setState] = useState(() =>
    cache.has(key) ? { status: 'ok', data: cache.get(key) } : { status: 'loading', data: null },
  );
  useEffect(() => {
    if (cache.has(key)) return undefined;
    let cancelled = false;
    fetcher()
      .then((data) => {
        cache.set(key, data);
        if (!cancelled) setState({ status: 'ok', data });
      })
      .catch((err) => {
        if (!cancelled) setState({ status: 'error', data: null, error: err.message });
      });
    return () => {
      cancelled = true;
    };
    // fetcher is a stable module function per key
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return state;
}
