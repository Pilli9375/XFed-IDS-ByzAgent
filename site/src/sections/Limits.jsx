import { useRef } from 'react';
import { limits } from '../copy.js';
import { useInView } from '../motion.js';
import SplitHeading, { Wipe } from '../components/SplitHeading.jsx';

export default function Limits() {
  const ref = useRef(null);
  const seen = useInView(ref);
  return (
    <section id="limits" className="limits" aria-labelledby="limits-title">
      <Wipe className="kicker mono">{limits.kicker}</Wipe>
      <SplitHeading id="limits-title" className="h2 disp" parts={limits.title} />
      <ol ref={ref} className="lims" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {limits.items.map((t, i) => (
          <li key={t} className={`lim rv${seen ? ' in' : ''}`} style={{ transitionDelay: `${i * 0.1}s` }}>
            <div className="n mono">0{i + 1}</div>
            <p>{t}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
