import { useCallback, useEffect, useState } from 'react';
import { hero } from '../copy.js';
import { d, src } from '../data.js';
import { f3, int } from '../format.js';
import { prefersReduced, useMedia } from '../motion.js';
import Rich from '../components/Rich.jsx';
import Src from '../components/Src.jsx';
import HeroFilm from '../components/HeroFilm.jsx';
import FilmDialog from '../components/FilmDialog.jsx';

// Count-up of the flow count once the loader has gone (1.8 s, ease-out cubic).
function useCount(target, start) {
  const [n, setN] = useState(() => (prefersReduced() ? target : 0));
  useEffect(() => {
    if (!start) return;
    if (prefersReduced()) { setN(target); return; }
    let raf = 0;
    const t0 = performance.now();
    const step = (t) => {
      const k = Math.min(1, (t - t0) / 1800);
      setN(Math.round(target * (1 - Math.pow(1 - k, 3))));
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, start]);
  return n;
}

export default function Hero({ play, count }) {
  const n = useCount(d.flows, count);
  const done = n === d.flows;
  // below 740 px the badge wraps under the lede; the loop then sits in the space beside it
  const compact = useMedia('(max-width: 740px)');
  const [film, setFilm] = useState(false);
  const closeFilm = useCallback(() => setFilm(false), []);
  return (
    <section id="top" className={`hero${play ? ' go' : ''}`} aria-labelledby="hero-title">
      {!compact && <HeroFilm start={count} />}

      <p className="hero-kicker mono fu">{hero.kicker}</p>
      <h1 id="hero-title" className="disp">
        <span className="line"><span>{hero.line1}</span></span>
        <span className="line"><span>
          {hero.line2.map((p, i) => (typeof p === 'string' ? p : (
            <em key={i}>{p.em}<span className="underl" aria-hidden="true" /></em>
          )))}
        </span></span>
      </h1>

      <div className="hero-row">
        {compact && <HeroFilm start={count} />}
        <p className="hero-lede fu fu1"><Rich parts={hero.lede} /></p>
        <div className="badge fu fu2" aria-hidden="true">
          <svg viewBox="0 0 150 150" width="150" height="150">
            <defs><path id="circ" d="M75,75 m-58,0 a58,58 0 1,1 116,0 a58,58 0 1,1 -116,0" /></defs>
            <text><textPath href="#circ">{hero.badge}</textPath></text>
          </svg>
          <div className="core">↗</div>
        </div>
      </div>

      <div className="hero-ctas fu fu3">
        <a className="cta cta-solid btn" href="#replay">{hero.ctaReplay} <span className="arr" aria-hidden="true">→</span></a>
        <a className="cta cta-line btn" href="#explain">{hero.ctaFindings} <span className="arr" aria-hidden="true">↓</span></a>
        <button type="button" id="film-btn" className="cta cta-film btn" data-cursor-label="play" aria-haspopup="dialog" onClick={() => setFilm(true)}>
          <span className="play" aria-hidden="true"><svg viewBox="0 0 10 12" width="10" height="12"><path d="M0 0L10 6L0 12Z" fill="currentColor" /></svg></span>
          {hero.ctaFilm}
        </button>
      </div>
      <FilmDialog open={film} onClose={closeFilm} labelledBy="film-btn" />

      <div className="hero-stats fu fu3">
        <div>
          <div className="mono" aria-hidden={!done}>{int(n)}</div>
          {!done && <span className="sr-only">{int(d.flows)}</span>}
          <div className="lbl">{hero.stats.flows} · <Src href={src('flows')} /></div>
        </div>
        <div>
          <div className="mono">{d.nOrgs}</div>
          <div className="lbl">{hero.stats.orgs} · <Src href={src('orgs')} /></div>
        </div>
        <div>
          <div className="mono">{f3(d.centralF1)}</div>
          <div className="lbl">{hero.stats.f1} · <Src href={src('centralF1')} /></div>
        </div>
        <div>
          <div className="mono">{d.nClasses}</div>
          <div className="lbl">{hero.stats.classes} · <Src href={src('classes')} /></div>
        </div>
      </div>
    </section>
  );
}
