import { useCallback, useEffect, useRef, useState } from 'react';
import { getShap } from './client';

const N_EVAL_ROWS = 14; // GET /shap/{id} is positional over sample_id in [0,13] only
const ALL_IDS = Array.from({ length: N_EVAL_ROWS }, (_, i) => i);

// Fetches the 14 fixed evaluation rows (GET /shap/0..13 in parallel) and
// tolerates partial failure: each id succeeds or fails on its own.
// Each row's raw_values + feature_names come from the same response SHAP
// itself does, so this one fetch backs both Detect's preset-row prediction
// and Explain's SHAP view -- one data path, not two.
//
// Returns { state, rows, failed, retrying, retry }:
//   state    'loading' (first load only) | 'ok' (>=1 row loaded) | 'error' (all 14 failed)
//   rows     only the rows that loaded, ordered by id -- a failed row is never
//            substituted or invented
//   failed   [{ id, error }] for the ids that failed
//   retry()  re-fetches ONLY the currently failed ids
export function useEvalRows() {
  const [slots, setSlots] = useState(null); // null until first load settles; else { [id]: {row}|{error} }
  const [retrying, setRetrying] = useState(false);
  const alive = useRef(true);
  const slotsRef = useRef(null);

  const load = useCallback((ids) => {
    return Promise.allSettled(ids.map((id) => getShap(id))).then((results) => {
      if (!alive.current) return;
      const next = { ...(slotsRef.current ?? {}) };
      results.forEach((r, i) => {
        next[ids[i]] =
          r.status === 'fulfilled' ? { row: r.value } : { error: r.reason?.message ?? String(r.reason) };
      });
      slotsRef.current = next;
      setSlots(next);
    });
  }, []);

  useEffect(() => {
    alive.current = true;
    load(ALL_IDS);
    return () => {
      alive.current = false;
    };
  }, [load]);

  const retry = useCallback(() => {
    const current = slotsRef.current;
    if (!current) return;
    const failedIds = ALL_IDS.filter((id) => current[id]?.error != null);
    if (failedIds.length === 0) return;
    setRetrying(true);
    load(failedIds).finally(() => {
      if (alive.current) setRetrying(false);
    });
  }, [load]);

  if (slots === null) return { state: 'loading', rows: [], failed: [], retrying, retry };

  const rows = ALL_IDS.filter((id) => slots[id]?.row).map((id) => slots[id].row);
  const failed = ALL_IDS.filter((id) => slots[id]?.error != null).map((id) => ({ id, error: slots[id].error }));
  return { state: rows.length === 0 ? 'error' : 'ok', rows, failed, retrying, retry };
}
