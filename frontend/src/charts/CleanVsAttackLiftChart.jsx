import {
  CartesianGrid,
  ComposedChart,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
  useXAxisScale,
  useYAxisScale,
} from 'recharts';
import { ACCENT, ALERT, BG, BORDER, BORDER_HI, TEXT_FAINT, TEXT_MUTED } from '../theme/tokens';

// Ports plots.py's clean_vs_attack_lift(): a dumbbell -- one line per silo
// from its clean-run flag rate to its attack-condition flag rate, with the
// lift value printed beside the attack-side marker. Recharts has no
// built-in dumbbell/connector primitive, so the connecting line is drawn by
// a plain child component that reads the chart's already-computed pixel
// scales via useXAxisScale/useYAxisScale (Recharts 3.8+) rather than
// recomputing them.

function Connectors({ rows }) {
  const xScale = useXAxisScale();
  const yScale = useYAxisScale();
  if (!xScale || !yScale) return null;
  return (
    <g>
      {rows.map((r) => (
        <line
          key={r.silo}
          x1={xScale(r.clean_flag_rate)}
          x2={xScale(r.attack_flag_rate)}
          y1={yScale(r.label)}
          y2={yScale(r.label)}
          stroke={r.malicious ? ALERT : BORDER_HI}
          strokeWidth={2}
        />
      ))}
    </g>
  );
}

function CleanDot({ cx, cy }) {
  if (cx == null || cy == null) return null;
  return <circle cx={cx} cy={cy} r={6} fill={TEXT_MUTED} stroke={BG} strokeWidth={1} />;
}

function AttackDot({ cx, cy, payload }) {
  if (cx == null || cy == null) return null;
  const color = payload.malicious ? ALERT : ACCENT;
  const s = 7;
  const points = `${cx},${cy - s} ${cx + s},${cy} ${cx},${cy + s} ${cx - s},${cy}`;
  const liftText = `lift ${payload.lift >= 0 ? '+' : ''}${payload.lift.toFixed(2)}`;
  return (
    <g>
      <polygon points={points} fill={color} stroke={BG} strokeWidth={1} />
      <text x={cx + 13} y={cy + 4} fontSize={11} fill={TEXT_MUTED}>
        {liftText}
      </text>
    </g>
  );
}

function LiftTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  return (
    <div className="xf-chart-tooltip">
      <div className="xf-tt-title">{d.label}</div>
      <div className="xf-tt-row">Clean flag rate {d.clean_flag_rate.toFixed(2)}</div>
      <div className="xf-tt-row">Attack flag rate {d.attack_flag_rate.toFixed(2)}</div>
      <div className="xf-tt-row">
        Lift {d.lift >= 0 ? '+' : ''}
        {d.lift.toFixed(2)}
      </div>
    </div>
  );
}

export default function CleanVsAttackLiftChart({ rows }) {
  return (
    <ResponsiveContainer width="100%" height={60 + 40 * rows.length}>
      <ComposedChart data={rows} layout="vertical" margin={{ top: 8, right: 70, bottom: 24, left: 10 }}>
        <CartesianGrid stroke={BORDER} horizontal={false} />
        <XAxis
          type="number"
          domain={[-0.05, 1.35]}
          tickFormatter={(v) => `${Math.round(v * 100)}%`}
          stroke={BORDER_HI}
          tick={{ fill: TEXT_MUTED, fontSize: 12 }}
          label={{
            value: 'Flag rate (downweight | quarantine)',
            position: 'insideBottom',
            offset: -14,
            fill: TEXT_FAINT,
            fontSize: 12,
          }}
        />
        <YAxis type="category" dataKey="label" width={80} stroke={BORDER_HI} tick={{ fill: TEXT_MUTED, fontSize: 12 }} />
        <Tooltip content={<LiftTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <Connectors rows={rows} />
        <Scatter dataKey="clean_flag_rate" data={rows} shape={<CleanDot />} isAnimationActive={false} />
        <Scatter dataKey="attack_flag_rate" data={rows} shape={<AttackDot />} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
