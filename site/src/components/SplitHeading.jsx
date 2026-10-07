import { useRef } from 'react';
import { useInView } from '../motion.js';

// Copy segments ('text' | {em} | {note}) -> words. A word that runs across segments with no space
// between them ("wrong" + ".") stays one unit so it can never break across lines.
function toWords(parts) {
  const out = [];
  (typeof parts === 'string' ? [parts] : parts).forEach((p) => {
    const kind = typeof p === 'string' ? null : (p.em !== undefined ? 'em' : 'note');
    const text = typeof p === 'string' ? p : (p.em !== undefined ? p.em : p.note);
    text.split(/(\s+)/).forEach((t, k) => {
      if (!t) return;
      if (/^\s+$/.test(t)) { out.push({ space: t }); return; }
      const last = out[out.length - 1];
      if (k === 0 && last && last.segs) last.segs.push({ t, kind });
      else out.push({ segs: [{ t, kind }] });
    });
  });
  return out;
}

// Section headline that rises word by word out of a mask the first time it is in view.
// The words are real text and the spaces between them plain text nodes, so the heading reads,
// selects and copies as one line.
export default function SplitHeading({ as: Tag = 'h2', parts, emClass, className = '', rootMargin, ...rest }) {
  const ref = useRef(null);
  const inView = useInView(ref, { threshold: 0.35, rootMargin });
  let i = 0;
  return (
    <Tag ref={ref} className={`${className} split${inView ? ' in' : ''}`} {...rest}>
      {toWords(parts).map((w, k) => {
        if (w.space) return w.space;
        const n = i++;
        return (
          <span key={k} className="w">
            <span className="wi" style={{ '--i': n }}>
              {w.segs.map((s, j) => {
                if (!s.kind) return s.t;
                return <em key={j} className={s.kind === 'note' ? 'note' : emClass}>{s.t}</em>;
              })}
            </span>
          </span>
        );
      })}
    </Tag>
  );
}

// Mono kicker revealed by a left-to-right wipe (no fade), so it reads before the headline lands.
// The clip sits on an inner span: IntersectionObserver counts the target's own clip-path.
export function Wipe({ as: Tag = 'p', className = '', rootMargin, children, ...rest }) {
  const ref = useRef(null);
  const inView = useInView(ref, { threshold: 0.5, rootMargin });
  return <Tag ref={ref} className={`${className} wipe${inView ? ' in' : ''}`} {...rest}><span className="wipe-i">{children}</span></Tag>;
}
