import { useRef } from 'react';
import { system } from '../copy.js';
import { d } from '../data.js';
import { useInView } from '../motion.js';
import SplitHeading, { Wipe } from '../components/SplitHeading.jsx';

export default function System() {
  const grid = useRef(null);
  const seen = useInView(grid);
  return (
    <section id="system" className="system" aria-labelledby="system-title">
      <Wipe className="kicker mono">{system.kicker}</Wipe>
      <SplitHeading id="system-title" className="h2 disp" parts={system.title} emClass="plum" />
      <ol ref={grid} className="stages" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {system.stages.map((s, i) => (
          <li key={s.n} className={`stage ${s.tone} rv lift${seen ? ' in' : ''}`} style={{ transitionDelay: `${i * 0.09}s` }}>
            <div className="n mono">{s.n}</div>
            <div className="t disp">{s.t}</div>
            <p>{s.d(d)}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
