import { useRef } from 'react';
import { limits } from '../copy.js';
import { AFTER_CURTAIN, useCurtain, useInView } from '../motion.js';
import SplitHeading, { Wipe } from '../components/SplitHeading.jsx';

export default function Limits() {
  const ref = useRef(null);
  const secRef = useRef(null);
  const curtainRef = useRef(null);
  const seen = useInView(ref, { rootMargin: AFTER_CURTAIN });
  useCurtain(secRef, curtainRef);
  return (
    <section id="limits" ref={secRef} className="limits-sec" aria-labelledby="limits-title">
      <div ref={curtainRef} className="curtain curtain-cream" aria-hidden="true" />
      <div className="limits">
      <Wipe className="kicker mono" rootMargin={AFTER_CURTAIN}>{limits.kicker}</Wipe>
      <SplitHeading id="limits-title" className="h2 disp" parts={limits.title} rootMargin={AFTER_CURTAIN} />
      <ol ref={ref} className="lims" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {limits.items.map((t, i) => (
          <li key={t} className={`lim rv${seen ? ' in' : ''}`} style={{ transitionDelay: `${i * 0.1}s` }}>
            <div className="n mono">0{i + 1}</div>
            <p>{t}</p>
          </li>
        ))}
      </ol>
      </div>
    </section>
  );
}
