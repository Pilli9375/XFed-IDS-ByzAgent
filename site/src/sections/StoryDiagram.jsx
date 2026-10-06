import { Fragment, useLayoutEffect, useRef, useState } from 'react';
import { story as copy } from '../copy.js';
import { d } from '../data.js';
import { f3 } from '../format.js';

// Coordinates from the design reference (wide); a portrait variant for phones.
const GEOM = {
  wide: { W: 760, H: 600, CX: 380, CY: 290, RX: 300, RY: 225, HUB: 46, R0: 12, R1: 30, LAB: 24 },
  narrow: { W: 440, H: 470, CX: 220, CY: 240, RX: 125, RY: 170, HUB: 36, R0: 9, R1: 22, LAB: 20 },
};
// Benign, DoS, DDoS, PortScan, other attacks
const PIE = ['var(--line)', 'var(--plum)', 'var(--terracotta)', 'var(--brass)', 'var(--olive)'];
const EASE = 'cubic-bezier(.2,.7,.2,1)';

const S = d.story;
const tmax = Math.max(...S.comp.map((c) => c[0]));

function geometry(G) {
  return S.comp.map((c, i) => {
    const ang = ((-90 + (360 / S.comp.length) * i) * Math.PI) / 180;
    const ox = G.CX + G.RX * Math.cos(ang);
    const oy = G.CY + G.RY * Math.sin(ang);
    const r = G.R0 + G.R1 * Math.sqrt(c[0] / tmax); // area ∝ training rows
    const dx = G.CX - ox;
    const dy = G.CY - oy;
    const dist = Math.hypot(dx, dy);
    const ux = dx / dist;
    const uy = dy / dist;
    return { ox, oy, r, ux, uy, len: dist - r - G.HUB, deg: (Math.atan2(uy, ux) * 180) / Math.PI };
  });
}

const pieStops = (c) => {
  let acc = 0;
  return PIE.map((col, k) => {
    const a0 = acc;
    acc += (c[k + 1] / c[0]) * 360;
    return `${col} ${a0.toFixed(2)}deg ${acc.toFixed(2)}deg`;
  }).join(', ');
};

export function Card({ step, style, className = '' }) {
  const c = step === 6 ? copy.agentCard(d) : copy.alertCard(d);
  return (
    <div className={`card ${className}`} style={style}>
      <p className="h mono">{c.head}</p>
      <p className="t disp" style={{ color: step === 6 ? 'var(--brass)' : 'var(--cream)' }}>{c.title}</p>
      <p className={`b ${step === 6 ? 'note' : 'mono'}`}>{c.body}</p>
    </div>
  );
}

export function Legend({ className = '' }) {
  return (
    <div className={`dg-legend mono ${className}`}>
      {copy.legend.map((t, k) => (
        <span key={t}><i style={{ background: PIE[k], border: k === 0 ? '1px solid var(--dark-muted)' : 0 }} />{t}</span>
      ))}
    </div>
  );
}

// Text equivalent of what the step's diagram shows (screen readers only).
function srText(b) {
  if (b === 3) return S.comp.map((c, i) => `${copy.org(i)}: ${copy.benignShare(c[1] / c[0])}`).join('; ');
  if (b === 5) return S.jac.map((j, i) => `${copy.org(i)}: ${f3(j)}`).join('; ');
  if (b === 6) return S.mal.map((i) => `${copy.org(i)}: ${copy.poisoned}`).join('; ');
  return '';
}

/**
 * step: 0 (nothing yet) … 7. narrow: portrait geometry. isStatic: no transitions.
 * cardBelow / legendBelow: render those outside the scaled box (small screens).
 * maxH: optional height budget for the scaled box (pinned layout).
 */
export default function StoryDiagram({ step: b, isStatic = false, maxH = Infinity, forceNarrow, overlay = false }) {
  const outer = useRef(null);
  const [w, setW] = useState(0);
  useLayoutEffect(() => {
    const el = outer.current;
    setW(el.getBoundingClientRect().width); // measure before first paint so the box never renders unscaled
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const narrow = forceNarrow ?? (w > 0 && w < 600);
  const G = narrow ? GEOM.narrow : GEOM.wide;
  const k = w ? Math.min(1, w / G.W, maxH / G.H) : 1;
  const below = !overlay && (narrow || k < 0.75); // pinned frame keeps the card on the diagram so nothing moves
  const ts = Math.max(1, 0.85 / k); // keep labels legible when the box shrinks
  const geo = geometry(G);
  const featured = S.featuredSilo;
  const tr = (s) => (isStatic ? 'none' : s);

  const cardOn = b === 4 || b === 6;
  const sr = srText(b);

  return (
    <div>
      <div ref={outer} className="dg-outer" style={{ height: G.H * k, maxWidth: G.W }}>
        <div className={`dg${isStatic ? ' static' : ''}`} style={{ width: G.W, height: G.H, transform: `scale(${k})` }} aria-hidden="true">
          {geo.map((g, i) => {
            const down = b >= 6 && i === featured;
            return (
              <div key={`e${i}`} className="edge" style={{
                left: g.ox + g.ux * g.r, top: g.oy + g.uy * g.r, width: g.len,
                borderTop: down ? '2px dashed var(--brass)' : '1.5px solid var(--cocoa)',
                transform: `rotate(${g.deg}deg) scaleX(${b >= 2 ? 1 : 0})`,
                opacity: b === 7 ? 0.25 : down ? 1 : 0.5,
                transition: tr(`transform 1s ${EASE} ${i * 0.07}s, opacity .6s`),
              }} />
            );
          })}

          {b >= 2 && b <= 5 && geo.map((g, i) => (
            <div key={`t${i}`} className="dot" style={{
              left: g.ox + g.ux * g.r - 3, top: g.oy + g.uy * g.r - 3,
              '--dx': `${(g.ux * g.len).toFixed(1)}px`, '--dy': `${(g.uy * g.len).toFixed(1)}px`,
              animationDelay: `${(i * 0.23).toFixed(2)}s`,
            }} />
          ))}

          <div className="hub" style={{
            left: G.CX - G.HUB, top: G.CY - G.HUB, width: 2 * G.HUB, height: 2 * G.HUB,
            background: b === 7 ? 'var(--plum)' : 'var(--sand)', color: b === 7 ? 'var(--cream)' : 'var(--plum)',
            transform: `scale(${b >= 2 ? (b === 7 ? 1.4 : 1) : 0})`,
            transition: tr(`transform .9s ${EASE}, background .6s, color .6s`),
          }}>
            <span className="mono">{b === 7 ? copy.hub.checks : copy.hub.shared}</span>
          </div>

          {geo.map((g, i) => {
            const c = S.comp[i];
            const bad = b >= 6 && S.mal.includes(i);
            const lr = g.r + G.LAB * ts;
            let val = '';
            if (b === 3) val = copy.benignShare(c[1] / c[0]);
            else if (b === 5) val = f3(S.jac[i]);
            else if (bad) val = copy.poisoned;
            const valColor = b === 5
              ? (S.jac[i] < S.lowJaccard ? 'var(--terracotta)' : 'var(--plum)')
              : (bad ? 'var(--terracotta)' : 'var(--cocoa)');
            return (
              <Fragment key={`o${i}`}>
                <div className="halo" style={{
                  left: g.ox - g.r - 12, top: g.oy - g.r - 12, width: 2 * g.r + 24, height: 2 * g.r + 24,
                  opacity: b === 6 && i === featured ? 1 : 0, transform: `scale(${b === 6 && i === featured ? 1 : 0.7})`,
                  transition: tr(`opacity .5s, transform .6s ${EASE}`),
                }} />
                <div className="org" style={{
                  left: g.ox - g.r, top: g.oy - g.r, width: 2 * g.r, height: 2 * g.r,
                  border: `1.5px solid ${bad ? 'var(--terracotta)' : 'var(--cocoa)'}`,
                  background: bad ? 'var(--blush)' : 'var(--cream)',
                  transform: `scale(${b >= 1 ? 1 : 0})`, opacity: b === 7 ? 0.45 : 1,
                  transition: tr(`transform .8s ${EASE} ${i * 0.06}s, opacity .6s, background .6s, border-color .6s`),
                }}>
                  <div className="pie" style={{ background: `conic-gradient(${pieStops(c)})`, opacity: b === 3 ? 1 : 0, transition: tr(`opacity .7s ${EASE}`) }} />
                </div>
                <div className="lab mono" style={{
                  left: g.ox - g.ux * lr, top: g.oy - g.uy * lr, fontSize: 11 * ts,
                  color: bad ? 'var(--terracotta)' : 'var(--muted)',
                  opacity: b >= 1 ? (b === 7 ? 0.45 : 1) : 0, transition: tr('opacity .6s'),
                }}>
                  {copy.org(i)}
                  <span className="v" style={{ fontSize: (b === 5 ? 15 : 11) * ts, color: valColor }}>{val}</span>
                </div>
              </Fragment>
            );
          })}

          {!below && (cardOn || !isStatic) && (
            <Card step={b} style={{
              left: G.CX, top: G.CY, opacity: cardOn ? 1 : 0,
              transform: `translate(-50%, -50%) scale(${cardOn ? 1 : 0.92})`,
              transition: tr(`opacity .5s, transform .6s ${EASE}`),
            }} />
          )}
          {!below && b === 3 && <Legend />}
        </div>
      </div>
      {below && b === 3 && <Legend className="legend-below" />}
      {below && cardOn && <Card step={b} className="card-below" />}
      {sr && <p className="sr-only">{sr}</p>}
    </div>
  );
}
