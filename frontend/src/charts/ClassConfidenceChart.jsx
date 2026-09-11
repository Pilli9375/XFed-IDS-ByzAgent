import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { BORDER_HI, TEXT_FAINT, TEXT_MUTED, familyColor } from '../theme/tokens';

// Ports plots.py's class_confidence(): horizontal confidence bars, one
// color per family, percentage label outside the bar. `probs` is a
// { className: probability } dict, straight from /predict's new
// `probabilities` field.

function ConfTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  return (
    <div className="xf-chart-tooltip">
      <div className="xf-tt-title">{d.name}</div>
      <div className="xf-tt-row">Confidence {(d.prob * 100).toFixed(1)}%</div>
    </div>
  );
}

export default function ClassConfidenceChart({ probs }) {
  // KNOWN ISSUE (pre-existing, reproduced on both dev and prod builds, not
  // a build-specific bug): with 9 classes and softmax outputs spanning down
  // to ~1e-17, Recharts renders only 8 of 9 bar shapes -- the smallest-value
  // class silently has no Cell/path in the DOM, though its y-axis label and
  // tooltip position are unaffected. Rounding the values to collapse several
  // to exactly 0 was tried and made it WORSE (only 1 shape rendered instead
  // of 8), so that is not the fix -- reverted. Filed as a follow-up rather
  // than shipping a guessed workaround; see the session's final-QA report.
  const data = Object.entries(probs)
    .map(([name, prob]) => ({ name, prob }))
    .sort((a, b) => b.prob - a.prob);

  return (
    <ResponsiveContainer width="100%" height={380}>
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 50, bottom: 24, left: 10 }}>
        <XAxis
          type="number"
          domain={[0, 1]}
          tickFormatter={(v) => `${Math.round(v * 100)}%`}
          stroke={BORDER_HI}
          tick={{ fill: TEXT_MUTED, fontSize: 12 }}
          label={{ value: 'Softmax confidence', position: 'insideBottom', offset: -14, fill: TEXT_FAINT, fontSize: 12 }}
        />
        <YAxis type="category" dataKey="name" width={90} stroke={BORDER_HI} tick={{ fill: TEXT_MUTED, fontSize: 12 }} />
        <Tooltip content={<ConfTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <Bar dataKey="prob" barSize={18} isAnimationActive={false}>
          {data.map((d) => (
            <Cell key={d.name} fill={familyColor(d.name)} />
          ))}
          <LabelList
            dataKey="prob"
            position="right"
            formatter={(v) => `${(Number(v) * 100).toFixed(1)}%`}
            fill={TEXT_MUTED}
            fontSize={12}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
