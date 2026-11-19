import { useEffect, useRef } from 'react';
import { source } from '../copy.js';
import { useMedia, useReducedMotion } from '../motion.js';

const INTERACTIVE = 'a, button, [role="gridcell"]';
const DRAG = '[data-cursor="drag"]';
const LABELS = { play: 'play', drag: 'drag', source: `${source} ↗` };

// Which label (if any) the ring shows over an interactive element.
function labelFor(el) {
  if (el.dataset.cursorLabel) return LABELS[el.dataset.cursorLabel] || '';
  if (el.matches(DRAG)) return LABELS.drag;
  if (el.tagName === 'A' && el.target === '_blank') return LABELS.source;
  return '';
}

// A small cocoa dot that trails the pointer on a spring and opens into a labelled ring over
// interactive things. Fine pointers only, never under reduced motion; the native cursor stays.
function CursorDot() {
  const ref = useRef(null);
  const lab = useRef(null);

  useEffect(() => {
    const el = ref.current;
    let tx = 0; let ty = 0; let x = 0; let y = 0; let vx = 0; let vy = 0;
    let raf = 0; let shown = false; let over = null;
    const K = 0.2; // pull toward the pointer per frame
    const D = 0.64; // velocity kept per frame (a small overshoot, then settle)

    const step = () => {
      vx = (vx + (tx - x) * K) * D;
      vy = (vy + (ty - y) * K) * D;
      x += vx; y += vy;
      el.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      if (Math.abs(tx - x) + Math.abs(ty - y) + Math.abs(vx) + Math.abs(vy) > 0.2) raf = requestAnimationFrame(step);
      else raf = 0;
    };
    const setOver = (t) => {
      if (t === over) return;
      over = t;
      const text = t ? labelFor(t) : '';
      lab.current.textContent = text;
      el.classList.toggle('ring', !!t);
      el.classList.toggle('lbl', !!text);
    };
    const onMove = (e) => {
      if (e.pointerType && e.pointerType !== 'mouse') return;
      tx = e.clientX; ty = e.clientY;
      if (!shown) { x = tx; y = ty; shown = true; el.classList.add('on'); }
      const target = e.target instanceof Element ? e.target : null;
      el.classList.toggle('on-dark', !!(target && target.closest('.dark')));
      setOver(target ? (target.closest(DRAG) || target.closest(INTERACTIVE)) : null);
      if (!raf) raf = requestAnimationFrame(step);
    };
    const onLeave = () => { shown = false; el.classList.remove('on'); setOver(null); };
    const onDown = () => el.classList.add('press');
    const onUp = () => el.classList.remove('press');

    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerdown', onDown, { passive: true });
    window.addEventListener('pointerup', onUp, { passive: true });
    document.documentElement.addEventListener('pointerleave', onLeave);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerdown', onDown);
      window.removeEventListener('pointerup', onUp);
      document.documentElement.removeEventListener('pointerleave', onLeave);
    };
  }, []);

  return (
    <div ref={ref} className="cursor" aria-hidden="true">
      <span className="cursor-shape" />
      <span ref={lab} className="cursor-lbl mono" />
    </div>
  );
}

export default function Cursor() {
  const fine = useMedia('(hover: hover) and (pointer: fine)');
  const reduced = useReducedMotion();
  return fine && !reduced ? <CursorDot /> : null;
}
