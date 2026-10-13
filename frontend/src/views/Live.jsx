import { useEffect, useMemo, useState } from 'react';
import { getConfig, getFigures, getHealth, getTrust } from '../api/client';
import { fetchExplanation } from '../api/useAlertExplanation';
import { useAlerts } from '../api/useAlerts';
import Ambient from '../components/Ambient';
import Header from '../components/Header';
import HotSwapBanner from '../components/HotSwapBanner';
import HotSwapDialog from '../components/HotSwapDialog';
import ScoreFlowDrawer from '../components/ScoreFlowDrawer';
import { useLoadingGate } from '../hooks/useLoadingGate';
import { useResource } from '../hooks/useResource';
import { useTheme } from '../hooks/useTheme';
import { kindOf } from '../lib/alerts';
import FlowStream from './live/FlowStream';
import KeyFigures from './live/KeyFigures';
import LiveSkeleton from './live/LiveSkeleton';
import SelectedAlert from './live/SelectedAlert';
import TrustDumbbell from './live/TrustDumbbell';

// Strength of the ambient pulse for a missed flow, relative to the theme's
// glow (live_console.dc.html: ambA = glow * 1.35 on a miss).
const MISS_STRENGTH = 1.35;

export default function Live({ hs }) {
  const { epoch } = useTheme();
  const swapActive = !!hs.status?.hotswap?.active;
  // /config changes when a hot-swap toggles (engine), so key it on that.
  const config = useResource(`config:${swapActive}`, getConfig);
  const health = useResource('health', getHealth);
  const figures = useResource('figures', getFigures);
  const trust = useResource('trust', getTrust);
  const feed = useAlerts();

  const [playing, setPlaying] = useState(true);
  const [frozen, setFrozen] = useState(null);
  const [filter, setFilter] = useState('all');
  const [pickedTs, setPickedTs] = useState(null);
  const [reviewed, setReviewed] = useState(() => new Set());
  const [condIdx, setCondIdx] = useState(0);
  const [dialog, setDialog] = useState(null); // 'hotswap' | 'score' | null

  const alerts = playing ? feed.alerts : (frozen ?? feed.alerts);
  const newest = alerts[0] ?? null;
  const selected = useMemo(
    () => (pickedTs ? (alerts.find((a) => a.timestamp === pickedTs) ?? null) : null) ?? newest,
    [alerts, pickedTs, newest],
  );

  // The first selected flow's explanation is part of what the skeleton
  // waits for, fetched in parallel with the rest instead of after it.
  const [firstExplained, setFirstExplained] = useState(false);
  const firstId = selected?.shap_available ? `${selected.shap_source}:${selected.shap_sample_id}` : null;
  useEffect(() => {
    if (firstExplained || !firstId) return;
    const [src, id] = firstId.split(':');
    fetchExplanation(Number(id), src).finally(() => setFirstExplained(true));
  }, [firstId, firstExplained]);
  const explainReady = firstExplained || (feed.status !== 'loading' && !firstId);

  const settled =
    [config, health, figures, trust].every((r) => r.status !== 'loading') && feed.status !== 'loading' && explainReady;
  const loading = useLoadingGate(settled, epoch);
  const kind = kindOf(newest);
  const tone = kind === 'ok' ? 'ok' : 'attack';
  const strength = kind === 'miss' ? MISS_STRENGTH : 1;

  const togglePlay = () => {
    if (playing) setFrozen(feed.alerts);
    setPlaying(!playing);
  };

  const cfg = config.data;
  const statusTone = loading ? 'agent' : kind;
  const liveLabel = loading
    ? 'LOADING'
    : !playing
      ? 'PAUSED'
      : kind === 'ok'
        ? 'LIVE · quiet'
        : kind === 'miss'
          ? 'LIVE · missed flow'
          : 'LIVE · attack flow';
  const errors = [
    ['GET /config', config],
    ['GET /health', health],
    ['GET /figures', figures],
    ['GET /trust', trust],
  ].filter(([, r]) => r.status === 'error');
  const sources = cfg
    ? {
        sentences: `results/explanations/${cfg.tag}/val_sentences.json`,
        shap: `results/shap/${cfg.tag}/val_pool.npz`,
      }
    : {};

  return (
    <div className={`v-page v-page--live${loading ? ' is-loading' : ''}`}>
      <Ambient tone={tone} strength={strength} loading={loading} />
      <div className="v-layer">
        <Header>
          <div className={`v-status tone-${statusTone}`} aria-live="polite">
            <span className="v-dot" />
            <span>{liveLabel}</span>
            {cfg && (
              <span className="v-model">
                {cfg.tag} · r{cfg.best_round} · {cfg.engine}
              </span>
            )}
          </div>
        </Header>
        <HotSwapBanner hs={hs} />
        <main id="main" className="v-main">
          <h1 className="sr-only">Live console</h1>
          {loading ? (
            <LiveSkeleton nValRows={health.data?.verified_val_rows} />
          ) : errors.length > 0 ? (
            <div className="panel" role="alert" style={{ padding: 20 }}>
              <p className="note text-attack">
                Could not load {errors.map(([n]) => n).join(', ')}. Is the backend running (uvicorn backend.main:app)?
              </p>
            </div>
          ) : (
            <div className="v-fade">
              <KeyFigures figures={figures.data} />
              <div className="v-row">
                <FlowStream
                  alerts={alerts}
                  newest={newest}
                  selectedTs={selected?.timestamp}
                  onSelect={setPickedTs}
                  filter={filter}
                  onFilter={setFilter}
                  playing={playing}
                  onTogglePlay={togglePlay}
                  onScore={() => setDialog('score')}
                  status={feed.status}
                />
                <SelectedAlert
                  alert={selected}
                  reviewed={!!selected && reviewed.has(selected.timestamp)}
                  onToggleReviewed={() =>
                    setReviewed((prev) => {
                      const next = new Set(prev);
                      if (next.has(selected.timestamp)) next.delete(selected.timestamp);
                      else next.add(selected.timestamp);
                      return next;
                    })
                  }
                  onHotSwap={() => {
                    // Pin the selection so the dialog's flow cannot move under it.
                    setPickedTs(selected.timestamp);
                    setDialog('hotswap');
                  }}
                  sources={sources}
                />
                <TrustDumbbell trust={trust.data} condIdx={condIdx} onCond={setCondIdx} />
              </div>
              <p className="foot">
                The stream replays the validation SHAP pool through the served model (backend/simulator.py); no test rows.
                {pickedTs ? (
                  <>
                    {' '}
                    <button type="button" className="btn btn--link" onClick={() => setPickedTs(null)}>
                      Follow newest flow
                    </button>
                  </>
                ) : (
                  ' Selection follows the newest flow until you pick one.'
                )}
              </p>
            </div>
          )}
        </main>
      </div>
      {cfg && (
        <>
          <HotSwapDialog
            open={dialog === 'hotswap'}
            onClose={() => setDialog(null)}
            alert={selected}
            classNames={cfg.class_names}
            hs={hs}
          />
          <ScoreFlowDrawer
            open={dialog === 'score'}
            onClose={() => setDialog(null)}
            featureNames={cfg.feature_names}
            presetAlert={selected}
          />
        </>
      )}
    </div>
  );
}
