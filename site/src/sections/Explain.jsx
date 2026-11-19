import { useRef, useState } from 'react';
import { explain } from '../copy.js';
import { d, src } from '../data.js';
import { f3 } from '../format.js';
import { useInView } from '../motion.js';
import SplitHeading, { Wipe } from '../components/SplitHeading.jsx';
import Tick from '../components/Tick.jsx';
import Src from '../components/Src.jsx';

export default function Explain() {
  const [pick, setPick] = useState('0.5');
  const aRef = useRef(null);
  const bRef = useRef(null);
  const seenA = useInView(aRef);
  const seenB = useInView(bRef);

  const opt = explain.alphas.find((x) => x.key === pick);
  const ag = d.agreement[pick];
  const width = seenB ? ag.j * 100 : 0;

  return (
    <section id="explain" className="explain" aria-labelledby="explain-title">
      <div className="explain-in">
        <div ref={aRef} className="explain-a">
          <Wipe className="kicker mono">{explain.kicker}</Wipe>
          <SplitHeading id="explain-title" className="h2 disp" parts={explain.title} emClass="plum" />
          <p className={`body rv${seenA ? ' in' : ''}`}>{explain.body(d)} <Src href={src('macroF1')} /></p>
          <p className={`margin note rv${seenA ? ' in' : ''}`} style={{ transitionDelay: '.1s' }}>{explain.margin}</p>
        </div>

        <div ref={bRef} className={`explain-b rv${seenB ? ' in' : ''}`}>
          <p className="q" id="alpha-q">{explain.question}</p>
          <div className="pills" role="group" aria-labelledby="alpha-q">
            {explain.alphas.map((a) => (
              <button key={a.key} type="button" className="pill" aria-pressed={a.key === pick} onClick={() => setPick(a.key)}>{a.label}</button>
            ))}
          </div>

          <div className="metric-cards" aria-live="polite">
            <div className="metric lift">
              <div className="k mono">{explain.cards.f1}</div>
              <Tick className="v mono" value={f3(d.fedF1[pick])} />
              <Src href={src('macroF1')} />
            </div>
            <div className="metric lift">
              <div className="k mono">{explain.cards.j}</div>
              <Tick className="v mono plum" value={f3(ag.j)} />
              <Src href={src('agreement')} />
            </div>
            <div className="metric lift">
              <div className="k mono">{explain.cards.t}</div>
              <Tick className="v mono" value={f3(ag.t)} />
              <Src href={src('agreement')} />
            </div>
          </div>

          <div className="agree">
            <div className="agree-track" role="img" aria-label={explain.barLabel(d, pick)}>
              <div className="agree-floor" style={{ left: `${d.floor[0] * 100}%`, width: `${(d.floor[1] - d.floor[0]) * 100}%` }} />
              <div className="agree-chance" style={{ left: `${d.chance * 100}%` }} />
              <div className="agree-bar" style={{ width: `${width}%` }} />
            </div>
            <div className="agree-axis mono">
              <span>{explain.axisZero}</span>
              <span className="fl">{explain.floor(d)} · <Src href={src('floor')} /></span>
              <span>{explain.chance(d)} · <Src href={src('chance')} /></span>
            </div>
          </div>

          <p className="note-p">
            {opt.note(d)}
            {opt.ci && <> <Src href={src('ci')} /></>}
          </p>
        </div>
      </div>
    </section>
  );
}
