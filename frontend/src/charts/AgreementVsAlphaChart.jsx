import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ACCENT, ALERT, BG, BORDER, BORDER_HI, TEXT, TEXT_FAINT, TEXT_MUTED } from '../theme/tokens';
import { fmt3 } from '../lib/agreement';

// Ports plots.py's agreement_vs_alpha(): median line + IQR ribbon (25th-75th
// percentile across all eligible (silo, sample) pairs -- a real spread from
// the data, not a fitted CI) + one scatter dot per seed's own median at that
// alpha. The ribbon is built the standard Recharts way: two stacked Areas,
// the first (q25) invisible as a baseline, the second (the q75-q25 span)
// visibly filled on top of it.

const RIBBON_FILL = 'rgba(76, 201, 240, 0.14)'; // ACCENT at 14% -- same literal plots.py hardcodes

function AgreementTooltip({ active, payload, alphaLabels }) {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload.find((p) => p.dataKey === 'median')?.payload;
  const seedPoints = payload.filter((p) => p.dataKey === 'y');
  if (!point && seedPoints.length === 0) return null;

  return (
    <div className="xf-chart-tooltip">
      {point && (
        <>
          <div className="xf-tt-title">{alphaLabels[point.x]}</div>
          <div className="xf-tt-row">Median {fmt3(point.median)}</div>
          <div className="xf-tt-row">
            IQR {fmt3(point.q25)} – {fmt3(point.q75)}
          </div>
        </>
      )}
      {seedPoints.map((p) => (
        <div className="xf-tt-row" key={p.payload.seed}>
          Seed {p.payload.seed}: {fmt3(p.payload.y)}
        </div>
      ))}
    </div>
  );
}

export default function AgreementVsAlphaChart({ chartData, scatterData, alphaLabels, yLabel, chance }) {
  return (
    <ResponsiveContainer width="100%" height={380}>
      <ComposedChart data={chartData} margin={{ top: 12, right: 24, bottom: 8, left: 4 }}>
        <CartesianGrid stroke={BORDER} vertical={false} />
        <XAxis
          dataKey="x"
          type="number"
          domain={[-0.5, chartData.length - 0.5]}
          ticks={chartData.map((d) => d.x)}
          tickFormatter={(i) => alphaLabels[i]}
          stroke={BORDER_HI}
          tick={{ fill: TEXT_MUTED, fontSize: 12 }}
        />
        <YAxis
          domain={[0, 1]}
          stroke={BORDER_HI}
          tick={{ fill: TEXT_MUTED, fontSize: 12 }}
          width={70}
          label={{ value: yLabel, angle: -90, position: 'insideLeft', fill: TEXT_FAINT, fontSize: 12 }}
        />
        <Tooltip content={<AgreementTooltip alphaLabels={alphaLabels} />} cursor={{ stroke: BORDER_HI }} />
        <Area
          dataKey="q25"
          stackId="iqr"
          stroke="none"
          fill="transparent"
          isAnimationActive={false}
          legendType="none"
          activeDot={false}
        />
        <Area
          dataKey="iqrRange"
          stackId="iqr"
          stroke="none"
          fill={RIBBON_FILL}
          isAnimationActive={false}
          legendType="none"
          activeDot={false}
        />
        <Line
          dataKey="median"
          stroke={ACCENT}
          strokeWidth={3}
          dot={{ r: 5, fill: ACCENT, stroke: BG, strokeWidth: 2 }}
          activeDot={{ r: 6, fill: ACCENT, stroke: BG, strokeWidth: 2 }}
          isAnimationActive={false}
        />
        <Scatter data={scatterData} dataKey="y" fill={TEXT} fillOpacity={0.75} isAnimationActive={false} />
        {chance != null && (
          <ReferenceLine
            y={chance}
            stroke={ALERT}
            strokeWidth={1.6}
            strokeDasharray="6 4"
            label={{ value: `chance ≈ ${fmt3(chance)}`, position: 'insideBottomRight', fill: ALERT, fontSize: 12 }}
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
