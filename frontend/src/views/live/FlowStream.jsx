import { useRef } from 'react';
import { FILTERS, isAttack, isMiss, kindOf } from '../../lib/alerts';
import { pct, timeOf } from '../../lib/format';

const MAX_ROWS = 40;

// Newest-first feed from GET /alerts (2 s poll). Arrow keys move the
// selection; "Next miss" jumps to the next older missed flow.
export default function FlowStream({ alerts, newest, selectedTs, onSelect, filter, onFilter, playing, onTogglePlay, onScore, status }) {
  const listRef = useRef(null);
  const shown = alerts.filter(FILTERS.find((f) => f.id === filter).test).slice(0, MAX_ROWS);
  const kind = kindOf(newest);

  const focusRow = (ts) => {
    requestAnimationFrame(() => {
      const el = listRef.current?.querySelector(`[data-ts="${CSS.escape(ts)}"]`);
      el?.focus();
      el?.scrollIntoView({ block: 'nearest' });
    });
  };

  const nextMiss = () => {
    const start = shown.findIndex((a) => a.timestamp === selectedTs);
    const ordered = [...shown.slice(start + 1), ...shown.slice(0, start + 1)];
    const target = ordered.find(isMiss);
    if (target) {
      onSelect(target.timestamp);
      focusRow(target.timestamp);
    }
  };

  const onKeyDown = (e) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp' && e.key !== 'Home' && e.key !== 'End') return;
    e.preventDefault();
    const i = shown.findIndex((a) => a.timestamp === selectedTs);
    let j = i;
    if (e.key === 'ArrowDown') j = Math.min(shown.length - 1, i + 1);
    if (e.key === 'ArrowUp') j = Math.max(0, i - 1);
    if (e.key === 'Home') j = 0;
    if (e.key === 'End') j = shown.length - 1;
    if (shown[j]) {
      onSelect(shown[j].timestamp);
      focusRow(shown[j].timestamp);
    }
  };

  const verdict = !newest
    ? ''
    : newest.true_family == null
      ? 'no true label'
      : isMiss(newest)
        ? `missed — true ${newest.true_family}`
        : 'matches true label';

  return (
    <section aria-labelledby="stream-h" className={`panel p-stream panel--focus tone-${kind}`}>
      <div className="panel-head">
        <h2 id="stream-h">Flow stream</h2>
        <div style={{ display: 'flex', gap: 6 }}>
          <button type="button" className="btn" aria-pressed={!playing} onClick={onTogglePlay}>
            {playing ? 'Pause' : 'Play'}
          </button>
          <button type="button" className="btn" onClick={nextMiss} disabled={!shown.some(isMiss)}>
            Next miss
          </button>
        </div>
      </div>
      <div className="now-bar" aria-live="polite">
        <span className="eyebrow">Just arrived</span>
        <span className="now-fam">{newest ? newest.predicted_family : '—'}</span>
        {newest && (
          <span className="now-meta">
            {pct(newest.confidence)} · {verdict}
          </span>
        )}
      </div>
      <div className="stream-tools">
        <div role="group" aria-label="Filter flows" style={{ display: 'flex', gap: 4 }}>
          {FILTERS.map((f) => (
            <button key={f.id} type="button" className="btn" aria-pressed={filter === f.id} onClick={() => onFilter(f.id)}>
              {f.label}
            </button>
          ))}
        </div>
        <div style={{ flex: '1 1 0' }} />
        <button type="button" className="btn" onClick={onScore}>
          Score a flow…
        </button>
      </div>
      {status === 'error' && <p className="feed-empty text-attack">Could not refresh GET /alerts. Showing the last good list.</p>}
      {shown.length === 0 ? (
        <p className="feed-empty">
          {alerts.length === 0
            ? 'No flows yet. Flows appear while the traffic simulator runs (python -m backend.simulator).'
            : `None of the ${alerts.length} buffered flows match this filter.`}
        </p>
      ) : (
        <ol className="feed" ref={listRef} aria-label="Flows, newest first" onKeyDown={onKeyDown}>
          {shown.map((a, k) => {
            const miss = isMiss(a);
            const current = a.timestamp === selectedTs;
            return (
              <li key={a.timestamp}>
                <button
                  type="button"
                  data-ts={a.timestamp}
                  aria-current={current ? 'true' : undefined}
                  tabIndex={current || (!shown.some((x) => x.timestamp === selectedTs) && k === 0) ? 0 : -1}
                  className={`feed-row tone-${kindOf(a)}${k === 0 ? ' is-new' : ''}${miss ? ' is-miss' : ''}`}
                  onClick={() => onSelect(a.timestamp)}
                >
                  <span className="feed-time">{timeOf(a.timestamp)}</span>
                  <span className="feed-dot" style={{ background: isAttack(a) ? 'var(--attack)' : 'var(--ok)' }} aria-hidden="true" />
                  <span className="feed-fam">{a.predicted_family}</span>
                  <span className="feed-conf">{pct(a.confidence)}</span>
                  <span className={`feed-mark ${miss ? 'text-attack' : 'text-ok'}`}>
                    {a.true_family == null ? '—' : miss ? `✗ ${a.true_family}` : '✓'}
                  </span>
                  <span className="sr-only">{miss ? `, missed, true label ${a.true_family}` : ''}</span>
                </button>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
