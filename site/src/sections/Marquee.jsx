import { Fragment, useLayoutEffect, useRef } from 'react';
import { marquee } from '../copy.js';
import { d } from '../data.js';
import { gsap, ScrollTrigger, useReducedMotion } from '../motion.js';
import Rich from '../components/Rich.jsx';

function Group({ items, star, hidden }) {
  return (
    <div className="grp" aria-hidden={hidden || undefined}>
      {items.map((t, i) => (
        <Fragment key={i}>
          <span>{Array.isArray(t) ? <Rich parts={t} /> : t}</span>
          <span className="star">{star}</span>
        </Fragment>
      ))}
    </div>
  );
}

// Two crossed bands drifting in opposite directions; scrolling speeds them up briefly.
// Decorative: the same facts appear with sources in the hero, so the bands are hidden from AT.
export default function Marquee() {
  const wrap = useRef(null);
  const a = useRef(null);
  const b = useRef(null);
  const reduced = useReducedMotion();

  useLayoutEffect(() => {
    if (reduced) return;
    const ctx = gsap.context(() => {
      const ta = gsap.fromTo(a.current, { xPercent: 0 }, { xPercent: -50, duration: 34, ease: 'none', repeat: -1 });
      const tb = gsap.fromTo(b.current, { xPercent: -50 }, { xPercent: 0, duration: 40, ease: 'none', repeat: -1 });
      const both = [ta, tb];
      ScrollTrigger.create({
        trigger: wrap.current,
        start: 'top bottom',
        end: 'bottom top',
        onToggle: (self) => both.forEach((t) => (self.isActive ? t.resume() : t.pause())),
        onUpdate: (self) => {
          const boost = 1 + Math.min(Math.abs(self.getVelocity()) / 250, 7);
          gsap.to(both, {
            timeScale: boost, duration: 0.15, overwrite: true,
            onComplete: () => gsap.to(both, { timeScale: 1, duration: 1.2, ease: 'power2.out', overwrite: true }),
          });
        },
      });
    }, wrap);
    return () => ctx.revert();
  }, [reduced]);

  const top = marquee.top(d);
  return (
    <div ref={wrap} className="marquees" aria-hidden="true">
      <div className="band band-a">
        <div ref={a} className="track disp"><Group items={top} star="✦" /><Group items={top} star="✦" hidden /></div>
      </div>
      <div className="band band-b">
        <div ref={b} className="track mono"><Group items={marquee.bottom} star="●" /><Group items={marquee.bottom} star="●" hidden /></div>
      </div>
    </div>
  );
}
