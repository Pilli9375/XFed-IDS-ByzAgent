import { useState } from 'react';

// A formatted value that ticks when it changes: each changed character rolls up and out while
// its replacement springs in from below. Only the old and the new text are ever drawn (no
// in-between values). Screen readers get the plain value; the rolling glyphs are hidden.
export default function Tick({ value, className }) {
  const [h, setH] = useState({ v: value, o: null, g: 0 });
  if (h.v !== value) setH({ v: value, o: h.v, g: h.g + 1 });
  const { v, o, g } = h.v === value ? h : { v: value, o: h.v, g: h.g + 1 };
  let n = 0;
  return (
    <div className={className}>
      <span className="tick" aria-hidden="true">
        {[...v].map((c, i) => {
          const was = o === null ? c : o[i];
          if (was === c) return <span key={`${i}-s`} className="tk">{c}</span>;
          const d = n++;
          return (
            <span key={`${i}-${g}`} className="tk tk-ch" style={{ '--d': `${d * 45}ms` }}>
              <span className="tk-in">{c}</span>
              {was !== undefined && <span className="tk-out">{was}</span>}
            </span>
          );
        })}
      </span>
      <span className="sr-only">{v}</span>
    </div>
  );
}
