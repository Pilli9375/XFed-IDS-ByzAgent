import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ALERT, BORDER, BORDER_HI, POSITIVE, TEXT_FAINT, TEXT_MUTED } from '../theme/tokens';

// Ports plots.py's faithfulness_auc(): grouped bars, deletion (ALERT,
// lower-better) and insertion (POSITIVE, higher-better) per model.

function AucTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="xf-chart-tooltip">
      <div className="xf-tt-title">{label}</div>
      {payload.map((p) => (
        <div className="xf-tt-row" key={p.dataKey}>
          {p.name}: {p.value.toFixed(3)}
        </div>
      ))}
    </div>
  );
}

export default function FaithfulnessAucChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={340}>
      <BarChart data={data} margin={{ top: 10, right: 10, bottom: 10, left: 4 }} barGap={4} barCategoryGap="28%">
        <CartesianGrid stroke={BORDER} vertical={false} />
        <XAxis dataKey="label" stroke={BORDER_HI} tick={{ fill: TEXT_MUTED, fontSize: 12 }} />
        <YAxis stroke={BORDER_HI} tick={{ fill: TEXT_MUTED, fontSize: 12 }} label={{ value: 'AUC', angle: -90, position: 'insideLeft', fill: TEXT_FAINT, fontSize: 12 }} />
        <Tooltip content={<AucTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <Legend wrapperStyle={{ fontSize: 12, color: TEXT_MUTED }} />
        <Bar dataKey="deletion_auc" name="Deletion AUC (lower better)" fill={ALERT} isAnimationActive={false} />
        <Bar dataKey="insertion_auc" name="Insertion AUC (higher better)" fill={POSITIVE} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}
