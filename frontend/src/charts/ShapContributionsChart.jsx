import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ACCENT, ALERT, BORDER, BORDER_HI, TEXT_FAINT, TEXT_MUTED } from '../theme/tokens';

// Ports plots.py's shap_contributions(): diverging horizontal bars, ALERT
// for positive (pushes toward the class), ACCENT for negative (pushes
// away). `data`: [{ name, value, raw }], raw nullable (the "Other N
// features" bucket has no single raw value).

function ContribTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  return (
    <div className="xf-chart-tooltip">
      <div className="xf-tt-title">{d.name}</div>
      <div className="xf-tt-row">
        SHAP {d.value >= 0 ? '+' : ''}
        {d.value.toFixed(4)} (logit)
      </div>
      <div className="xf-tt-row">Raw value {d.raw == null ? '—' : d.raw.toLocaleString()}</div>
    </div>
  );
}

export default function ShapContributionsChart({ data }) {
  const sorted = [...data].sort((a, b) => a.value - b.value);
  // Explicit domain: values are negative-and-positive (diverging), and
  // Recharts' auto domain was unreliable for that here.
  const maxAbs = Math.max(...sorted.map((d) => Math.abs(d.value)), 0.001);
  const domain = [-maxAbs * 1.15, maxAbs * 1.15];

  return (
    <ResponsiveContainer width="100%" height={60 + 32 * sorted.length}>
      <BarChart data={sorted} layout="vertical" margin={{ top: 8, right: 24, bottom: 24, left: 10 }}>
        <CartesianGrid stroke={BORDER} horizontal={false} />
        <XAxis
          type="number"
          domain={domain}
          tickFormatter={(v) => v.toFixed(1)}
          stroke={BORDER_HI}
          tick={{ fill: TEXT_MUTED, fontSize: 12 }}
          label={{ value: 'SHAP contribution (logit)', position: 'insideBottom', offset: -14, fill: TEXT_FAINT, fontSize: 12 }}
        />
        <YAxis type="category" dataKey="name" width={170} stroke={BORDER_HI} tick={{ fill: TEXT_MUTED, fontSize: 11 }} />
        <Tooltip content={<ContribTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <ReferenceLine x={0} stroke={BORDER_HI} strokeWidth={1.4} />
        <Bar dataKey="value" barSize={16} isAnimationActive={false}>
          {sorted.map((d) => (
            <Cell key={d.name} fill={d.value > 0 ? ALERT : ACCENT} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
