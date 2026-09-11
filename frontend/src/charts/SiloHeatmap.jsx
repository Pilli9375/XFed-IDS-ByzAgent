import { useMemo, useState } from 'react';
import { ACCENT, ACCENT_DIM, SURFACE, TEXT_FAINT, TEXT_MUTED } from '../theme/tokens';

// Ports plots.py's silo_heatmap(): per-silo per-family flow counts,
// log10-scaled, 3-stop colorscale (SURFACE -> ACCENT_DIM at 0.35 -> ACCENT
// at 1.0, matching theme.py's colorscale exactly). Recharts has no heatmap,
// so this is the same hand-rolled SVG grid approach as DecisionGridHeatmap,
// but with a continuous color instead of a fixed 3-severity palette.

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
function lerp(a, b, t) {
  return a + (b - a) * t;
}
function lerpColor(hexA, hexB, t) {
  const [ar, ag, ab] = hexToRgb(hexA);
  const [br, bg, bb] = hexToRgb(hexB);
  return `rgb(${lerp(ar, br, t).toFixed(0)}, ${lerp(ag, bg, t).toFixed(0)}, ${lerp(ab, bb, t).toFixed(0)})`;
}
function colorScale(t) {
  if (t <= 0.35) return lerpColor(SURFACE, ACCENT_DIM, t / 0.35);
  return lerpColor(ACCENT_DIM, ACCENT, (t - 0.35) / 0.65);
}

const CELL = 40;
const LABEL_W = 60;
const HEADER_H = 60;
const GAP = 2;

export default function SiloHeatmap({ rows, families, nSilos }) {
  const [hover, setHover] = useState(null);

  const grid = useMemo(() => {
    const bySilo = new Map();
    for (let s = 0; s < nSilos; s += 1) bySilo.set(s, new Map());
    for (const r of rows) {
      bySilo.get(r.silo)?.set(r.family, r.n);
    }
    const cells = [];
    let zMin = Infinity;
    let zMax = -Infinity;
    for (let s = 0; s < nSilos; s += 1) {
      for (const fam of families) {
        const n = bySilo.get(s)?.get(fam) ?? 0;
        const z = Math.log10(n + 1);
        zMin = Math.min(zMin, z);
        zMax = Math.max(zMax, z);
        cells.push({ silo: s, family: fam, n, z });
      }
    }
    return { cells, zMin, zMax };
  }, [rows, families, nSilos]);

  const width = LABEL_W + families.length * CELL;
  const height = HEADER_H + nSilos * CELL;
  const span = grid.zMax - grid.zMin || 1;

  return (
    <div style={{ position: 'relative' }}>
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" style={{ display: 'block' }}>
        {families.map((fam, ci) => (
          <text
            key={fam}
            x={LABEL_W + ci * CELL + CELL / 2}
            y={HEADER_H - 8}
            fontSize={10}
            textAnchor="end"
            fill={TEXT_FAINT}
            transform={`rotate(-40, ${LABEL_W + ci * CELL + CELL / 2}, ${HEADER_H - 8})`}
          >
            {fam}
          </text>
        ))}
        {Array.from({ length: nSilos }, (_, s) => (
          <text key={s} x={LABEL_W - 8} y={HEADER_H + s * CELL + CELL / 2 + 4} fontSize={11} textAnchor="end" fill={TEXT_MUTED}>
            {`Silo ${s}`}
          </text>
        ))}
        {grid.cells.map((c) => {
          const ri = c.silo;
          const ci = families.indexOf(c.family);
          const t = (c.z - grid.zMin) / span;
          return (
            <rect
              key={`${c.silo}-${c.family}`}
              x={LABEL_W + ci * CELL + GAP / 2}
              y={HEADER_H + ri * CELL + GAP / 2}
              width={CELL - GAP}
              height={CELL - GAP}
              fill={colorScale(Number.isFinite(t) ? t : 0)}
              onMouseEnter={(e) => {
                const wrapRect = e.currentTarget.ownerSVGElement.parentElement.getBoundingClientRect();
                setHover({ x: e.clientX - wrapRect.left, y: e.clientY - wrapRect.top, ...c });
              }}
              onMouseLeave={() => setHover(null)}
            />
          );
        })}
      </svg>

      {hover && (
        <div
          className="xf-chart-tooltip"
          style={{ position: 'absolute', left: hover.x + 12, top: hover.y + 12, pointerEvents: 'none', zIndex: 5 }}
        >
          <div className="xf-tt-title">
            Silo {hover.silo}, {hover.family}
          </div>
          <div className="xf-tt-row">{hover.n.toLocaleString()} flows</div>
        </div>
      )}
    </div>
  );
}
