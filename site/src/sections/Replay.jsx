import { useEffect, useMemo, useRef, useState } from 'react';
import { replay, sources as sourcesLabel } from '../copy.js';
import { d, loadLarge, src } from '../data.js';
import { conf4, pad3, signed2 } from '../format.js';
import { useInView } from '../motion.js';
import SplitHeading, { Wipe } from '../components/SplitHeading.jsx';
import Src from '../components/Src.jsx';
import Reveal from '../components/Reveal.jsx';
import TypeOut from '../components/TypeOut.jsx';

const TICK_MS = 1700;
const FEED = 7;
const FADE = 0.023; // per older row; the oldest of 7 sits at 0.86, keeping every status ≥4.5:1

// Alerts stream in stored order (replay_alerts.json `alerts`, seq 0..n-1). Never shuffled or filtered.
export default function Replay() {
  const secRef = useRef(null);
  const bodyRef = useRef(null);
  const near = useInView(secRef, { rootMargin: '1200px 0px', threshold: 0 });
  const seen = useInView(bodyRef, { threshold: 0.18 });
  const [alerts, setAlerts] = useState(null);
  const [err, setErr] = useState(false);
  const [rp, setRp] = useState(-1); // index of the newest alert shown
  const [run, setRun] = useState(false);
  const [pin, setPin] = useState(null); // alert picked from the feed

  useEffect(() => {
    if (!near) return;
    loadLarge('replay_alerts').then((j) => setAlerts(j.alerts), () => setErr(true));
  }, [near]);

  // start streaming the first time the feed is in view
  useEffect(() => {
    if (alerts && seen && rp < 0) { setRp(0); setRun(true); }
  }, [alerts, seen, rp]);

  useEffect(() => {
    if (!run || !alerts) return;
    const id = setInterval(() => {
      setRp((i) => {
        if (i + 1 >= alerts.length) { setRun(false); return i; }
        return i + 1;
      });
    }, TICK_MS);
    return () => clearInterval(id);
  }, [run, alerts]);

  const rpi = Math.max(0, rp);
  const counts = useMemo(() => {
    if (!alerts) return { ok: 0, miss: 0 };
    let ok = 0;
    for (let i = 0; i <= rpi; i++) if (alerts[i].correct) ok += 1;
    return { ok, miss: rpi + 1 - ok };
  }, [alerts, rpi]);

  const toggle = () => {
    if (run) setRun(false);
    else { setPin(null); if (rp + 1 < alerts.length) setRun(true); }
  };
  const jumpMiss = () => {
    let j = -1;
    for (let i = rpi + 1; i < alerts.length; i++) if (!alerts[i].correct) { j = i; break; }
    if (j < 0) for (let i = 0; i < alerts.length; i++) if (!alerts[i].correct) { j = i; break; }
    if (j < 0) return;
    setRp(j); setPin(null); setRun(false);
  };

  const sel = alerts ? alerts[pin === null ? rpi : pin] : null;
  const mx = sel ? Math.max(...sel.top_features.map((x) => Math.abs(x.shap_value))) : 1;

  return (
    <section id="replay" ref={secRef} className="replay dark" aria-labelledby="replay-title">
      <div className="wrap">
        <div className="rp-head">
          <div>
            <Wipe className="kicker mono">{replay.kicker}</Wipe>
            <SplitHeading id="replay-title" className="h2 disp" parts={replay.title} />
          </div>
          <Reveal as="p" className="rp-pill mono">{replay.pill}</Reveal>
        </div>

        <div ref={bodyRef} className={`rp-body rv${seen ? ' in' : ''}`}>
          {!alerts ? (
            <p className="rp-status mono" role="status">{err ? replay.loadError : replay.loading}</p>
          ) : (
            <>
              <div className="rp-feed">
                <div className="rp-bar">
                  <span className="lbl mono"><span className={`live${run ? ' pulse' : ''}`} aria-hidden="true" />{replay.stream}</span>
                  <div className="rp-btns">
                    <button type="button" className="rp-btn solid" onClick={toggle} aria-pressed={!run}>{run ? replay.pause : replay.play}</button>
                    <button type="button" className="rp-btn line" onClick={jumpMiss}>{replay.jump}</button>
                  </div>
                </div>
                <div className="rp-counts mono">
                  <span className="seen"><b>{rpi + 1}</b> {replay.seen(d.nAlerts)}</span>
                  <span className="ok"><b>{counts.ok}</b> {replay.right}</span>
                  <span className="miss"><b>{counts.miss}</b> {replay.missed}</span>
                  <Src href={src('alerts')} />
                </div>
                <ul className="feed" aria-label={replay.feedLabel}>
                  {Array.from({ length: Math.min(FEED, rpi + 1) }, (_, k) => rpi - k).map((i) => {
                    const A = alerts[i];
                    const cur = (pin === null ? rpi : pin) === i;
                    return (
                      <li key={A.seq}>
                        <button
                          type="button"
                          className={`fitem${cur ? ' cur' : ''}${i === rpi ? (rpi % 2 ? ' inA' : ' inB') : ''}`}
                          style={{ opacity: 1 - (rpi - i) * FADE }}
                          aria-pressed={cur}
                          onClick={() => { setPin(i); setRun(false); }}
                        >
                          <span className="sq mono">#{pad3(A.seq)}</span>
                          <span className="pr">{A.predicted_family}</span>
                          <span className={`st mono ${A.correct ? 'ok' : 'miss'}`}>{A.correct ? replay.statusRight : replay.statusMissed(A.true_family)}</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>

              <div className="rp-why">
                <p className="h mono">{replay.why(pad3(sel.seq))} · <Src href={src('alerts')} /></p>
                <div className="row1">
                  <span className="pred disp">{sel.predicted_family}</span>
                  <span className={`verdict mono${sel.correct ? '' : ' miss'}`}>{sel.correct ? replay.verdictRight : replay.verdictMissed(sel.true_family)}</span>
                </div>
                <p className="conf mono">{replay.confidence} <b>{conf4(sel.confidence)}</b></p>
                <p className="rl mono">{replay.reasons}</p>
                <div className="shap">
                  {sel.top_features.map((x) => {
                    const w = (Math.abs(x.shap_value) / mx) * 50;
                    return (
                      <div key={x.name} className="shap-row">
                        <span className="nm" title={x.name}>{x.name}</span>
                        <div className="shap-track" aria-hidden="true">
                          <div className="zero" />
                          <div className={`bar ${x.shap_value >= 0 ? 'pos' : 'neg'}`} style={x.shap_value >= 0 ? { left: '50%', width: `${w}%` } : { left: `${50 - w}%`, width: `${w}%` }} />
                        </div>
                        <span className="val mono">{signed2(x.shap_value)}</span>
                      </div>
                    );
                  })}
                </div>
                <div className="shap-dir mono" aria-hidden="true"><span>{replay.away(sel.predicted_family)}</span><span>{replay.toward(sel.predicted_family)}</span></div>
                <div className="rp-note">
                  <p className="l mono">{replay.noteLabel}</p>
                  <p className="s note"><TypeOut text={sel.sentence} /></p>
                </div>
              </div>
            </>
          )}
        </div>
        <p className="rp-foot">{replay.foot(d)} {sourcesLabel} <Src href={src('alerts')}>{replay.footLinks[0]}</Src> · <Src href={src('servedModel')}>{replay.footLinks[1]}</Src></p>
      </div>
    </section>
  );
}
