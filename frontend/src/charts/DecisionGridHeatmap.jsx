import { useState } from 'react';
import { ALERT, BORDER, DECISION_COLORS, DECISION_NAME_BY_SEVERITY, TEXT_FAINT, TEXT_MUTED } from '../theme/tokens';

// Ports plots.py's decision_grid_heatmap(): silo x round grid, one cell per
// decision, malicious silos marked on their row label. Recharts has no
// heatmap primitive, so this is a hand-rolled SVG grid instead of a chart
// library component -- a plain viewBox-scaled table of colored <rect>s with
// a small hover tooltip, not a "computation," so nothing here recomputes
// flag rates or anything else backend/trust.py already serves in per_silo.

const CELL = 22;
const LABEL_W = 74;
const HEADER_H = 20;
const GAP = 2;

export default function DecisionGridHeatmap({ grid, maliciousSilos }) {
  const { rounds, silos } = grid;
  const [hover, setHover] = useState(null);
  const width = LABEL_W + rounds.length * CELL;
  const height = HEADER_H + silos.length * CELL;

  return (
    <div style={{ position: 'relative' }}>
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" style={{ display: 'block' }}>
        {rounds.map((r, ci) => (
          <text
            key={`h-${r}`}
            x={LABEL_W + ci * CELL + CELL / 2}
            y={HEADER_H - 7}
            fontSize={8}
            textAnchor="middle"
            fill={TEXT_FAINT}
          >
            {r}
          </text>
        ))}

        {silos.map((s, ri) => {
          const isMalicious = maliciousSilos.includes(s.silo_id);
          return (
            <g key={s.silo_id}>
              <text
                x={LABEL_W - 8}
                y={HEADER_H + ri * CELL + CELL / 2 + 3}
                fontSize={9}
                textAnchor="end"
                fill={isMalicious ? ALERT : TEXT_MUTED}
              >
                {`silo ${s.silo_id}${isMalicious ? '  ⚠' : ''}`}
              </text>
              {s.severities.map((sev, ci) => (
                <rect
                  key={ci}
                  x={LABEL_W + ci * CELL + GAP / 2}
                  y={HEADER_H + ri * CELL + GAP / 2}
                  width={CELL - GAP}
                  height={CELL - GAP}
                  fill={sev == null ? BORDER : DECISION_COLORS[sev]}
                  opacity={sev == null ? 0.4 : 1}
                  onMouseEnter={(e) => {
                    const wrapRect = e.currentTarget.ownerSVGElement.parentElement.getBoundingClientRect();
                    setHover({
                      x: e.clientX - wrapRect.left,
                      y: e.clientY - wrapRect.top,
                      silo: s.silo_id,
                      round: rounds[ci],
                      severity: sev,
                    });
                  }}
                  onMouseLeave={() => setHover(null)}
                />
              ))}
            </g>
          );
        })}
      </svg>

      {hover && (
        <div
          className="xf-chart-tooltip"
          style={{ position: 'absolute', left: hover.x + 12, top: hover.y + 12, pointerEvents: 'none', zIndex: 5 }}
        >
          <div className="xf-tt-title">
            silo {hover.silo}, round {hover.round}
          </div>
          <div className="xf-tt-row">
            decision: {hover.severity == null ? 'no data' : DECISION_NAME_BY_SEVERITY[hover.severity]}
          </div>
        </div>
      )}
    </div>
  );
}
