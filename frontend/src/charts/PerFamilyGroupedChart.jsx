import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { BORDER, BORDER_HI, SERIES, TEXT_MUTED } from '../theme/tokens';
import { formatAlpha } from '../lib/agreement';

// Ports plots.py's per_family_grouped(): grouped bars, family on x, one
// series per alpha, same theme.SERIES palette by alpha index.

function FamilyTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="xf-chart-tooltip">
      <div className="xf-tt-title">{label}</div>
      {payload.map((p) => (
        <div className="xf-tt-row" key={p.dataKey}>
          {p.name}: {p.value != null ? p.value.toFixed(3) : '—'}
        </div>
      ))}
    </div>
  );
}

export default function PerFamilyGroupedChart({ data, alphas }) {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={data} margin={{ top: 10, right: 10, bottom: 40, left: 4 }} barGap={4} barCategoryGap="18%">
        <CartesianGrid stroke={BORDER} vertical={false} />
        <XAxis
          dataKey="family"
          stroke={BORDER_HI}
          tick={{ fill: TEXT_MUTED, fontSize: 11 }}
          angle={-25}
          textAnchor="end"
          interval={0}
          height={55}
        />
        <YAxis domain={[0, 1]} stroke={BORDER_HI} tick={{ fill: TEXT_MUTED, fontSize: 12 }} />
        <Tooltip content={<FamilyTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <Legend wrapperStyle={{ fontSize: 12, color: TEXT_MUTED }} />
        {alphas.map((a, i) => (
          <Bar key={a} dataKey={`a_${a}`} name={formatAlpha(a)} fill={SERIES[i % SERIES.length]} isAnimationActive={false} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
