import { useEffect, useState } from 'react';
import { useReducedMotion } from '../motion.js';

const MAX_MS = 1100; // a whole note types within one replay tick (1.7 s)
const PER_CHAR_MS = 22;

// Types its text out character by character whenever the text changes; instant under reduced
// motion. The full text is laid out invisibly underneath so nothing below moves while it types,
// and screen readers get the whole sentence at once.
export default function TypeOut({ text }) {
  const reduced = useReducedMotion();
  const [n, setN] = useState(reduced ? text.length : 0);

  useEffect(() => {
    if (reduced) { setN(text.length); return undefined; }
    setN(0);
    const per = Math.min(PER_CHAR_MS, MAX_MS / Math.max(1, text.length));
    const t0 = performance.now();
    let raf = 0;
    const step = (t) => {
      const k = Math.min(text.length, Math.floor((t - t0) / per) + 1);
      setN(k);
      if (k < text.length) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [text, reduced]);

  if (n >= text.length) return text;
  return (
    <span className="typeout">
      <span className="typeout-ghost" aria-hidden="true">{text}</span>
      <span className="typeout-live" aria-hidden="true">{text.slice(0, n)}</span>
      <span className="sr-only">{text}</span>
    </span>
  );
}
