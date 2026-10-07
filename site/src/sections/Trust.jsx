import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { trust, sources as sourcesLabel } from '../copy.js';
import { d, loadLarge, src, srcAttack, srcByz } from '../data.js';
import { f2, f3, pctWhole, pp, signed2 } from '../format.js';
import { prefersReduced, useInView } from '../motion.js';
import Rich from '../components/Rich.jsx';
import Src from '../components/Src.jsx';
import Reveal from '../components/Reveal.jsx';
import SplitHeading, { Wipe } from '../components/SplitHeading.jsx';

const LABELS = ['trust', 'downweight', 'quarantine'];
const GLYPH = ['', '–', '×'];
const DEC_COLOR = ['var(--olive)', 'var(--brass)', 'var(--terracotta-light)'];
const DEFAULT_SEED = '1337';
const CLEAN = 'clean';
const ATTACK = 'f3_sudden';
// header reveals trigger only once they are above ~70% of the viewport, i.e. after the curtain has risen
const AFTER_CURTAIN = '0px 0px -30% 0px';

// byzagent_decisions.json -> per seed: a/b = [silo][round-1] -> decision record, exactly as stored
function shape(byz) {
  const out = {};
  for (const [seed, conds] of Object.entries(byz.by_seed)) {
    const grid = (cond) => {
      const g = Array.from({ length: byz.n_silos }, () => Array(byz.n_rounds).fill(null));
      cond.decisions.forEach((x) => { g[x.silo][x.round - 1] = { ...x, v: LABELS.indexOf(x.decision) }; });
      return g;
    };
    out[seed] = {
      a: grid(conds[CLEAN]),
      b: grid(conds[ATTACK]),
      mal: conds[ATTACK].true_malicious_silos,
      runA: conds[CLEAN].run_file,
      runB: conds[ATTACK].run_file,
      attack: conds[ATTACK].attack,
    };
  }
  return out;
}

function Cards() {
  const ref = useRef(null);
  const seen = useInView(ref);
  const cards = [
    { k: trust.cards.multiKrum, v: pctWhole(d.multiKrumExclusion), cls: 'v1', dot: true, href: src('multiKrum') },
    { k: trust.cards.krumCost, v: pp(d.krumCleanCost), cls: 'v2', href: src('krumCost') },
    { k: trust.cards.signal, v: trust.cards.signalValue, cls: 'v3', href: src('attackSignal') },
  ];
  return (
    <div ref={ref} className="tcards">
      {cards.map((c, i) => (
        <div key={c.k} className={`tcard rv lift${seen ? ' in' : ''}`} style={{ transitionDelay: `${i * 0.1}s` }}>
          <div className="k mono">{c.dot && <span className="pulse" aria-hidden="true" />}{c.k}</div>
          <div className={`v ${c.cls} disp`}>{c.v}</div>
          <Src href={c.href} />
        </div>
      ))}
    </div>
  );
}

function Grid({ T, seed, tr, sel, setSel }) {
  const cellRefs = useRef({});
  const nR = d.nRounds;
  const nS = d.nSilos;
  const key = (side, silo, round) => `${side}-${silo}-${round}`;

  const onKeyDown = (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    const col = (sel.side === 'a' ? 0 : nR) + sel.round - 1; // 0 .. 2nR-1 across both runs
    let r = sel.silo;
    let c = col;
    if (e.key === 'ArrowLeft') c -= 1;
    else if (e.key === 'ArrowRight') c += 1;
    else if (e.key === 'ArrowUp') r -= 1;
    else if (e.key === 'ArrowDown') r += 1;
    else if (e.key === 'Home') c = sel.side === 'a' ? 0 : nR;
    else if (e.key === 'End') c = sel.side === 'a' ? nR - 1 : 2 * nR - 1;
    else return;
    if (r < 0 || r >= nS || c < 0 || c >= 2 * nR) return; // edge: leave the key to the page
    e.preventDefault();
    const next = { side: c < nR ? 'a' : 'b', silo: r, round: (c % nR) + 1 };
    setSel(next);
    const el = cellRefs.current[key(next.side, next.silo, next.round)];
    if (el) { el.focus(); el.scrollIntoView({ block: 'nearest', inline: 'nearest' }); }
  };

  const fr = (side, silo) => T[side][silo].filter((x) => x.v > 0).length / nR;

  const cells = (side, silo) => T[side][silo].map((rec, r) => {
    const on = r < tr;
    const isSel = sel.side === side && sel.silo === silo && sel.round === r + 1;
    const pickIt = () => setSel({ side, silo, round: r + 1 });
    return (
      <button
        key={r}
        ref={(el) => { cellRefs.current[key(side, silo, r + 1)] = el; }}
        type="button"
        role="gridcell"
        tabIndex={isSel ? 0 : -1}
        aria-selected={isSel}
        aria-label={trust.cellLabel(silo, r + 1, side, trust.decisions[rec.decision])}
        className={`cell${on ? ` v${rec.v}` : ''}${isSel ? ' sel' : ''}`}
        onMouseEnter={pickIt}
        onFocus={pickIt}
        onClick={pickIt}
      >
        {on ? GLYPH[rec.v] : ''}
      </button>
    );
  });

  const ticks = [1, ...Array.from({ length: Math.floor(nR / 5) }, (_, i) => (i + 1) * 5)];
  const count = (side, pred) => {
    let n = 0; let k = 0;
    T[side].forEach((row, silo) => { if (pred(silo)) row.forEach((x) => { n += 1; if (x.v > 0) k += 1; }); });
    return [k, n];
  };
  const [ka, na] = count('a', () => true);
  const [km, nm] = count('b', (s) => T.mal.includes(s));
  const [kh, nh] = count('b', (s) => !T.mal.includes(s));

  return (
    <div className="tgrid-scroll">
      <div className="tgrid">
        <div className="thead mono">
          <div className="c-lab" style={{ border: 0 }} />
          <div className="c-side" style={{ display: 'block' }}>{trust.colClean} · <b>{trust.sumClean(ka, na)}</b> · <Src href={srcByz(T.runA)} /></div>
          <div className="c-side" style={{ display: 'block' }}>{trust.colAttack(T.mal.length, nS)} · <b>{trust.sumAttack(km, nm, kh, nh)}</b> · <Src href={srcByz(T.runB)} /></div>
          <div style={{ width: 120 }}>{trust.colFlag[0]}<br />{trust.colFlag[1]}</div>
        </div>
        <div role="grid" aria-label={trust.gridLabel(seed)} aria-rowcount={nS} onKeyDown={onKeyDown}>
          {T.a.map((_, silo) => {
            const bad = T.mal.includes(silo);
            const fa = fr('a', silo);
            const fb = fr('b', silo);
            const lift = fb - fa;
            return (
              <div key={silo} role="row" className="trow">
                <div role="rowheader" className={`c-lab mono${bad ? ' bad' : ''}`}>{trust.org(silo)}</div>
                <div className="c-side" role="presentation">{cells('a', silo)}</div>
                <div className="c-side" role="presentation">{cells('b', silo)}</div>
                <div className={`c-flag mono${bad ? (lift >= 0.3 ? ' lift' : ' bad') : ''}`} role="presentation">
                  {`${f2(fa)} → ${f2(fb)}${bad ? `  ${signed2(lift)}` : ''}`}
                </div>
              </div>
            );
          })}
        </div>
        <div className="taxis mono" aria-hidden="true">
          <div className="c-lab" style={{ border: 0, fontSize: 10, color: 'inherit' }}>{trust.roundAxis}</div>
          <div className="c-side">{ticks.map((t) => <span key={t}>{t}</span>)}</div>
          <div className="c-side">{ticks.map((t) => <span key={t}>{t}</span>)}</div>
        </div>
      </div>
    </div>
  );
}

function Detail({ T, seed, sel }) {
  const rec = T[sel.side][sel.silo][sel.round - 1];
  const bad = sel.side === 'b' && T.mal.includes(sel.silo);
  let truth = trust.truthHonest;
  if (sel.side === 'a') truth = trust.truthClean;
  else if (bad) truth = trust.truthPoisoned(rec.flip_fraction);
  return (
    <div className="tdet" aria-live="polite">
      <p className="h mono">{trust.detailHead(seed, sel.side, sel.silo, sel.round)}</p>
      <div className="row1">
        <span className="dec disp" style={{ color: DEC_COLOR[rec.v] }}>{trust.decisions[rec.decision]}</span>
        <span className={`truth${bad ? ' bad' : ''}`}>
          {truth}
          {sel.side === 'b' && <small> · {trust.truthHidden} · <Src href={srcAttack(seed, T.attack)} /></small>}
        </span>
      </div>
      <p className="rl mono">{trust.reasonLabel}</p>
      <p className="reason note">“{rec.explanation}”</p>
      <div className="stats mono">
        <span>{trust.stats.tl} <b>{f3(rec.stats.train_loss)}</b></span>
        <span>{trust.stats.un} <b>{f3(rec.stats.update_norm)}</b></span>
        <span>{trust.stats.cg} <b>{f3(rec.stats.cosine_to_global)}</b></span>
        <Src href={srcByz(sel.side === 'a' ? T.runA : T.runB)} />
      </div>
    </div>
  );
}

export default function Trust() {
  const secRef = useRef(null);
  const gridRef = useRef(null);
  const near = useInView(secRef, { rootMargin: '1200px 0px', threshold: 0 });
  const gridSeen = useInView(gridRef, { threshold: 0.18 });
  const [data, setData] = useState(null);
  const [err, setErr] = useState(false);
  const [seed, setSeed] = useState(DEFAULT_SEED);
  const [tr, setTr] = useState(0);
  const [sel, setSel] = useState({ side: 'b', silo: d.story.featuredSilo, round: 10 });
  const timer = useRef(0);

  useEffect(() => {
    if (!near) return;
    loadLarge('byzagent_decisions').then((j) => setData(shape(j)), () => setErr(true));
  }, [near]);

  // Cells fill round by round (110 ms per round) when the grid appears, on seed change and on Replay.
  const fill = useCallback(() => {
    clearInterval(timer.current);
    if (prefersReduced()) { setTr(d.nRounds); return; }
    setTr(0);
    timer.current = setInterval(() => {
      setTr((t) => {
        if (t + 1 >= d.nRounds) clearInterval(timer.current);
        return Math.min(d.nRounds, t + 1);
      });
    }, 110);
  }, []);
  useEffect(() => () => clearInterval(timer.current), []);
  useEffect(() => { if (data && gridSeen) fill(); }, [data, gridSeen, fill]);

  const T = data && data[seed];
  const fr = useMemo(() => (T ? (side, silo) => T[side][silo].filter((x) => x.v > 0).length / d.nRounds : null), [T]);
  const note = fr && trust.notes[seed] ? trust.notes[seed](fr) : null;

  return (
    <section id="trust" ref={secRef} className="trust dark" aria-labelledby="trust-title">
      <div className="wrap">
        <Wipe className="kicker mono" rootMargin={AFTER_CURTAIN}>{trust.kicker}</Wipe>
        <SplitHeading id="trust-title" className="h2 big disp" parts={trust.title} rootMargin={AFTER_CURTAIN} />
        <Reveal as="p" className="lede">{trust.body}</Reveal>

        <Cards />

        <div ref={gridRef} className={`tgrid-sec rv${gridSeen ? ' in' : ''}`}>
          <div className="tgrid-head">
            <div style={{ maxWidth: 660 }}>
              <h3 className="disp"><Rich parts={trust.gridTitle} /></h3>
              <p>{trust.gridBody({ mal: T ? T.mal : d.story.mal })}</p>
            </div>
            <div className="seedbar" role="group" aria-label={trust.seedGroup}>
              {d.seeds.map((s) => (
                <button key={s} type="button" className="seed" aria-pressed={s === seed} onClick={() => { setSeed(s); if (data) fill(); }}>{trust.seed(s)}</button>
              ))}
              <button type="button" className="seed ghost btn" onClick={fill}>{trust.replay} <span className="arr" aria-hidden="true">↻</span></button>
            </div>
          </div>

          <div className="tlegend mono">
            <span><span className="sw" style={{ background: 'var(--olive)' }} />{trust.legend.trust}</span>
            <span><span className="sw" style={{ background: 'var(--brass)' }}>–</span>{trust.legend.downweight}</span>
            <span><span className="sw" style={{ background: 'var(--terracotta-light)' }}>×</span>{trust.legend.quarantine}</span>
            <span><span className="sw rule" />{trust.legend.poisoned}</span>
          </div>

          {T ? (
            <>
              <Grid T={T} seed={seed} tr={tr} sel={sel} setSel={setSel} />
              <div className="tdetail">
                <Detail T={T} seed={seed} sel={sel} />
                <div className="tnote">
                  <p className="h mono">{note && note[0]}</p>
                  <p className="b">
                    {note && note[1]}{' '}
                    <span className="srcs">{sourcesLabel} <Src href={srcByz(T.runA)}>{trust.colClean.toLowerCase()}</Src> · <Src href={srcByz(T.runB)}>{trust.colAttack(T.mal.length, d.nSilos).toLowerCase()}</Src></span>
                  </p>
                  <p className="f">{trust.flagDef(d)} <Src href={src('trendRange')} /></p>
                </div>
              </div>
            </>
          ) : (
            <p className="tstatus mono" role="status">{err ? trust.loadError : trust.loading}</p>
          )}
        </div>

        <Reveal as="blockquote" className="claim note" style={{ marginLeft: 0, marginRight: 0 }}>
          "{d.lockedClaim}"
        </Reveal>
        <p className="claim-f">{trust.fidelity(d)} <Src href={src('trendRange')} /></p>
      </div>
    </section>
  );
}
