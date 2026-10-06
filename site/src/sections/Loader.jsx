import { useEffect, useState } from 'react';
import { loader } from '../copy.js';

// Counter 000 -> 100, then the panel slides up. Once per session; never under
// reduced motion (index.html decides before first paint via html.with-loader).
export default function Loader({ phase, setPhase }) {
  const [pct, setPct] = useState(0);

  useEffect(() => {
    try { sessionStorage.setItem('xfed-loader-seen', '1'); } catch (e) { /* storage blocked: loader may show again */ }
    const root = document.documentElement;
    root.style.overflow = 'hidden';
    let raf = 0;
    let t1 = 0;
    const t0 = performance.now();
    const step = (t) => {
      const k = Math.min(1, (t - t0) / 1400);
      setPct(Math.round(100 * (1 - Math.pow(1 - k, 2))));
      if (k < 1) raf = requestAnimationFrame(step);
      else {
        setPhase('leaving');
        t1 = setTimeout(() => {
          root.classList.remove('with-loader');
          root.style.overflow = '';
          setPhase('done');
        }, 900);
      }
    };
    raf = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(t1);
      root.style.overflow = '';
    };
  }, [setPhase]);

  return (
    <div className={`loader${phase === 'leaving' ? ' out' : ''}`} aria-hidden="true">
      <div className="note">{loader.line1}<br /><span>{loader.line2}</span></div>
      <div className="mono">{String(pct).padStart(3, '0')}</div>
    </div>
  );
}
