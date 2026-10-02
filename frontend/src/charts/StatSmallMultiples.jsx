import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ACCENT, ALERT, BORDER, BORDER_HI, TEXT_MUTED } from '../theme/tokens';

// Ports plots.py's stat_small_multiples(): the 5 behavioral stats over rounds
// for one silo, one small panel per stat (they live on wildly different
// scales, so never overlaid on one axis). Unlike the Streamlit original, which
// drew one run at a time, every panel here draws clean AND attack together --
// an attack series never appears without its clean companion.
export const STATS = ['update_norm', 'cosine_to_global', 'cosine_to_peer_mean', 'train_loss', 'val_accuracy'];

// Values are served already aligned 1:1 with `rounds` (null = missing round);
// this only zips the two sides for Recharts, it computes nothing.
function zip(rounds, cleanSeries, attackSeries, stat) {
  return rounds.map((round, i) => ({
    round,
    clean: cleanSeries?.[stat]?.[i] ?? null,
    attack: attackSeries?.[stat]?.[i] ?? null,
  }));
}

function StatTooltip({ active, payload, label, stat }) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  const fmt = (v) => (v == null ? 'missing' : v.toFixed(4));
  return (
    <div className="xf-chart-tooltip">
      <div className="xf-tt-title">
        round {label} · {stat}
      </div>
      <div className="xf-tt-row">Clean {fmt(d.clean)}</div>
      <div className="xf-tt-row">Attack {fmt(d.attack)}</div>
    </div>
  );
}

function StatPanel({ stat, rounds, cleanSeries, attackSeries, attackColor }) {
  const data = zip(rounds, cleanSeries, attackSeries, stat);
  return (
    <div className="xf-chart-card" data-stat-panel={stat}>
      <div className="xf-caption" style={{ marginTop: 0, marginBottom: '0.4rem' }}>
        {stat}
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 18, left: 0 }}>
          <CartesianGrid stroke={BORDER} vertical={false} />
          <XAxis
            dataKey="round"
            stroke={BORDER_HI}
            tick={{ fill: TEXT_MUTED, fontSize: 10 }}
            label={{ value: 'round', position: 'insideBottom', offset: -10, fill: TEXT_MUTED, fontSize: 11 }}
          />
          <YAxis
            stroke={BORDER_HI}
            width={48}
            tick={{ fill: TEXT_MUTED, fontSize: 10 }}
            domain={['auto', 'auto']}
            tickFormatter={(v) => Number(v.toPrecision(3))}
          />
          <Tooltip content={<StatTooltip stat={stat} />} cursor={{ stroke: BORDER_HI }} />
          <Legend verticalAlign="top" height={20} iconSize={10} wrapperStyle={{ fontSize: 11, color: TEXT_MUTED }} />
          <Line
            type="monotone"
            dataKey="clean"
            name="Clean run"
            stroke={TEXT_MUTED}
            strokeWidth={2}
            dot={{ r: 2.5 }}
            connectNulls={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="attack"
            name="Attack condition"
            stroke={attackColor}
            strokeWidth={2}
            dot={{ r: 2.5 }}
            connectNulls={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function StatSmallMultiples({ cleanStats, attackStats, siloId, malicious }) {
  const cleanSeries = cleanStats.silos.find((s) => s.silo_id === siloId);
  const attackSeries = attackStats.silos.find((s) => s.silo_id === siloId);
  if (!cleanSeries && !attackSeries) return null;
  // Same convention as CleanVsAttackLiftChart: attack marker is ALERT for a
  // truly malicious silo, ACCENT otherwise.
  const attackColor = malicious ? ALERT : ACCENT;
  return (
    <div className="xf-grid-stats">
      {STATS.map((stat) => (
        <StatPanel
          key={stat}
          stat={stat}
          rounds={attackStats.rounds}
          cleanSeries={cleanSeries}
          attackSeries={attackSeries}
          attackColor={attackColor}
        />
      ))}
    </div>
  );
}
