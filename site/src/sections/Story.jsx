import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { story as copy, sources as sourcesLabel } from '../copy.js';
import { d, src, srcAttack, srcByz } from '../data.js';
import { ScrollTrigger, scrollToY, useInView, useMedia, useReducedMotion } from '../motion.js';
import Src from '../components/Src.jsx';
import SplitHeading from '../components/SplitHeading.jsx';
import StoryDiagram from './StoryDiagram.jsx';

const STEPS = copy.steps;
const N = STEPS.length;
const PIN_LENGTH = 3.5; // viewport heights of scroll mapped to steps 1–7

function Foot() {
  const links = [
    src('composition'),
    src('perSilo'),
    srcByz(d.story.runFile),
    srcAttack(d.story.seed, d.story.attack),
    src('alerts'),
    src('macroF1'),
  ];
  return (
    <p className="story-foot">
      {copy.foot(d)} {sourcesLabel}{' '}
      {copy.footLinks.map((label, i) => (
        <span key={label}>{i > 0 && ' · '}<Src href={links[i]}>{label}</Src></span>
      ))}
    </p>
  );
}

// Reduced motion and small screens: the seven steps as a plain list, one static diagram each.
function StoryList() {
  return (
    <ol className="story-list">
      {STEPS.map((s, i) => (
        <li key={s.t}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '24px 48px', alignItems: 'flex-start' }}>
            <div style={{ flex: '1 1 300px', maxWidth: 420, minWidth: 0 }}>
              <div className="head">
                <span className="num mono" aria-hidden="true">0{i + 1}</span>
                <div>
                  <h3 className="disp">{s.t}</h3>
                  <p className="d">{s.d(d)}</p>
                  <p className="m note">{s.m(d)}</p>
                </div>
              </div>
            </div>
            <figure className="fig" style={{ flex: '999 1 420px', minWidth: 0, margin: 0 }} aria-label={copy.diagramLabel(i + 1, s.t)}>
              <StoryDiagram step={i + 1} isStatic />
            </figure>
          </div>
        </li>
      ))}
    </ol>
  );
}

// Pinned for ~350vh; scroll progress picks the step and fills the progress segments.
function StoryPinned({ sectionRef }) {
  const pinRef = useRef(null);
  const segRefs = useRef([]);
  const stRef = useRef(null);
  const [step, setStep] = useState(0);
  const [maxH, setMaxH] = useState(600);
  const entered = useInView(sectionRef, { threshold: 0.2 });

  useLayoutEffect(() => {
    const st = ScrollTrigger.create({
      trigger: pinRef.current,
      start: 'top top',
      end: () => '+=' + Math.round(window.innerHeight * PIN_LENGTH),
      pin: true,
      invalidateOnRefresh: true,
      onUpdate: (self) => {
        const x = self.progress * N;
        segRefs.current.forEach((el, k) => { if (el) el.style.width = Math.max(0, Math.min(1, x - k)) * 100 + '%'; });
        setStep((prev) => (prev === 0 && self.progress === 0 ? 0 : Math.min(N, Math.floor(x) + 1)));
      },
    });
    stRef.current = st;
    // height budget for the diagram: viewport minus everything above it in the pinned frame and the foot below
    const fit = () => {
      const pin = pinRef.current;
      const fig = pin.querySelector('.dg-outer');
      const foot = pin.querySelector('.story-foot');
      const above = fig.getBoundingClientRect().top - pin.getBoundingClientRect().top;
      const footH = foot.getBoundingClientRect().height + parseFloat(getComputedStyle(foot).marginTop);
      setMaxH(Math.max(260, window.innerHeight - above - footH - 16));
    };
    fit();
    window.addEventListener('resize', fit);
    // fonts change the layout height above the story; recompute pin positions once they land
    document.fonts?.ready.then(() => { fit(); ScrollTrigger.refresh(); });
    return () => { window.removeEventListener('resize', fit); st.kill(); stRef.current = null; };
  }, []);

  useEffect(() => { if (entered) setStep((s) => Math.max(1, s)); }, [entered]);

  const go = (k) => {
    const st = stRef.current;
    if (!st) return;
    scrollToY(st.start + (st.end - st.start) * ((k - 0.5) / N));
  };

  const b = step;
  return (
    <div ref={pinRef} className="pin">
      <div className="story-in">
        <div className="story-steps">
          <SplitHeading className="story-kicker mono" parts={copy.kicker} />
          <div className="steps">
            {STEPS.map((s, i) => {
              const k = i + 1;
              const on = k === b || (b === 0 && k === 1);
              return (
                <button key={s.t} type="button" className={`step${on ? ' on' : ''}`} aria-current={on ? 'step' : undefined} onClick={() => go(k)}>
                  <span className="num mono">0{k}</span>
                  <span className="body">
                    <span className="ttl disp">{s.t}</span>
                    {on && (
                      <>
                        <span className="d">{s.d(d)}</span>
                        <span className="m note">{s.m(d)}</span>
                      </>
                    )}
                  </span>
                </button>
              );
            })}
          </div>
          <div className="segs" aria-hidden="true">
            {STEPS.map((s, k) => <div key={s.t} className="seg"><div ref={(el) => { segRefs.current[k] = el; }} /></div>)}
          </div>
        </div>
        <figure className="story-fig" style={{ margin: 0 }} aria-label={copy.diagramLabel(Math.max(1, b), STEPS[Math.max(1, b) - 1].t)}>
          <StoryDiagram step={b} maxH={maxH} forceNarrow={false} overlay />
          <Foot />
        </figure>
      </div>
    </div>
  );
}

export default function Story() {
  const ref = useRef(null);
  const reduced = useReducedMotion();
  const roomy = useMedia('(min-width: 1000px) and (min-height: 640px)');
  const pinned = !reduced && roomy;
  return (
    <section id="story" ref={ref} className={`story${pinned ? ' pinned' : ''}`}>
      {pinned ? <StoryPinned sectionRef={ref} /> : (
        <div className="story-in" style={{ display: 'block' }}>
          <SplitHeading className="story-kicker mono" parts={copy.kicker} />
          <StoryList />
          <Foot />
        </div>
      )}
    </section>
  );
}
