import { useRef } from 'react';
import { limits } from '../copy.js';
import { useInView } from '../motion.js';
import Rich from '../components/Rich.jsx';
import Reveal from '../components/Reveal.jsx';

export default function Limits() {
  const ref = useRef(null);
  const seen = useInView(ref);
  return (
    <section id="limits" className="limits" aria-labelledby="limits-title">
      <Reveal>
        <p className="kicker mono">{limits.kicker}</p>
        <h2 id="limits-title" className="h2 disp"><Rich parts={limits.title} /></h2>
      </Reveal>
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
