import { Bar, BarChart, CartesianGrid, Cell, ErrorBar, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ACCENT, ALERT, BORDER, BORDER_HI, TEXT_FAINT, TEXT_MUTED } from '../theme/tokens';
import { fmt3 } from '../lib/agreement';

// Ports plots.py's floor_comparison(): horizontal bars with asymmetric IQR
// error bars. `data` entries carry { label, value (median), errorRange:
// [value-q25, q75-value], q25, q75 } -- Recharts' ErrorBar takes that
// [low, high] array directly for asymmetric bars (same convention as
// Plotly's array/arrayminus that plots.py uses).
const COLORS = [ALERT, ACCENT];

function FloorTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  return (
    <div className="xf-chart-tooltip">
      <div className="xf-tt-title">{d.label.replace('<br>', ' ')}</div>
      <div className="xf-tt-row">Median {fmt3(d.value)}</div>
      <div className="xf-tt-row">
        IQR {fmt3(d.q25)} – {fmt3(d.q75)}
      </div>
    </div>
  );
}

export default function FloorComparisonChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={60 + 90 * data.length}>
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 40, bottom: 24, left: 10 }}>
        <CartesianGrid stroke={BORDER} horizontal={false} />
        <XAxis
          type="number"
          domain={[0, 1]}
          stroke={BORDER_HI}
          tick={{ fill: TEXT_MUTED, fontSize: 12 }}
          label={{
            value: 'Jaccard@10 (median, IQR bars)',
            position: 'insideBottom',
            offset: -14,
            fill: TEXT_FAINT,
            fontSize: 12,
          }}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={210}
          stroke={BORDER_HI}
          tick={{ fill: TEXT_MUTED, fontSize: 12 }}
        />
        <Tooltip content={<FloorTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <Bar dataKey="value" barSize={30} isAnimationActive={false}>
          {data.map((d, i) => (
            <Cell key={d.label} fill={COLORS[i % COLORS.length]} />
          ))}
          <ErrorBar dataKey="errorRange" direction="x" width={7} strokeWidth={1.6} stroke={TEXT_FAINT} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
