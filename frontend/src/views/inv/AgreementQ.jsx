import { useMemo } from 'react';
import { faithfulnessFigureUrl } from '../../api/client';
import Src, { Srcs } from '../../components/Src';
import { computeHeadlineAgreement, computePerFamilyAgreement } from '../../lib/agreement';
import { alphaStr, fixed } from '../../lib/format';
import { medianSorted, sortedNums } from '../../lib/stats';
import DataEligibility from './DataEligibility';

const AGREEMENT_SRC = 'results/inspection/agreement_metrics.csv';
const ROUNDWISE_SRC = 'results/inspection/round_wise_agreement.csv';
const FAITH_SRC = ['results/inspection/deletion_auc.csv', 'results/inspection/insertion_auc.csv'];

// 02: silo-vs-global explanation agreement against alpha, the seed-noise
// floor (null control) and chance. Medians are computed client-side by
// lib/agreement.js exactly as before (verified to reproduce the headline).
export default function AgreementQ({ agreement, summary, faith, federation }) {
  const headline = useMemo(() => computeHeadlineAgreement(agreement.agreement_metrics), [agreement]);
  const perFamily = useMemo(() => computePerFamilyAgreement(agreement.agreement_metrics), [agreement]);
  const roundWise = useMemo(() => medianByRound(agreement.round_wise_agreement), [agreement]);
  const chance = summary.chance.value;
  const floor = summary.floor;
  const ci = summary.ci;
  const jac = headline.map((h) => h.jaccard_at_10_median);
  const multiples = jac.map((v) => v / chance);
  const global = faith.auc.find((r) => r.model === 'global');
  const alphas = headline.map((h) => alphaStr(h.alpha));
  const families = [...new Set(perFamily.map((r) => r.family))];

  return (
    <section id="q2" aria-labelledby="q2h" className="q">
      <div className="q-head">
        <div>
          <span className="eyebrow">02 · Explanation check</span>
          <h2 id="q2h" className="h2">Do the orgs agree on why?</h2>
        </div>
        <span className="mono-mute">Jaccard@10 vs global model · median</span>
      </div>
      <div className="scroll-x" tabIndex={0} role="region" aria-label="Agreement number line">
        <div
          className="numline"
          role="img"
          aria-label={`Jaccard at 10: ${headline.map((h) => `${fixed(h.jaccard_at_10_median)} at alpha ${h.alpha}`).join(', ')}; seed-noise floor ${fixed(floor.low)} to ${fixed(floor.high)}; chance ${fixed(chance)}`}
        >
          <div className="numline-axis" />
          <div className="numline-band" style={{ left: `${floor.low * 100}%`, width: `${(floor.high - floor.low) * 100}%` }} />
          <span className="numline-label text-agent" style={{ left: `${floor.high * 100}%`, top: 0, paddingLeft: 8 }}>
            seed-noise floor {fixed(floor.low)}–{fixed(floor.high)}
          </span>
          <div className="numline-chance" style={{ left: `${chance * 100}%` }} />
          <span className="numline-label text-mute" style={{ left: `${chance * 100}%`, top: 8, paddingLeft: 6 }}>
            chance {fixed(chance)}
          </span>
          {headline.map((h) => (
            <div key={h.alpha} className="numline-pt" style={{ left: `${h.jaccard_at_10_median * 100}%` }}>
              <span className="num" style={{ fontSize: 13, fontWeight: 600 }}>{fixed(h.jaccard_at_10_median)}</span>
              <span className="numline-dot" style={{ background: 'var(--ink)' }} />
              <span className="mono-mute">α={alphaStr(h.alpha)}</span>
            </div>
          ))}
        </div>
      </div>
      <p className="small">
        {fixed(Math.min(...multiples), 1)}×–{fixed(Math.max(...multiples), 1)}× chance. The floor is how much rankings differ
        between centralized models that differ only by random seed (median {fixed(floor.median)}, range over seed pairs).
      </p>
      <Srcs paths={[AGREEMENT_SRC, floor.source, summary.chance.source]} />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
        <div className="tile">
          <p className="eyebrow">Weighted <span className="keep">τ</span></p>
          <p className="tile-num tile-num--sm">{headline.map((h) => fixed(h.tau_median)).join(' → ')}</p>
          <p className="tiny">median, α = {alphas.join(' / ')}</p>
          <Src path={AGREEMENT_SRC} />
        </div>
        <div className="tile">
          <p className="eyebrow"><span className="keep">α={ci.alpha}</span> CI vs floor</p>
          <p className="tile-num tile-num--sm">
            [{fixed(ci.low)}, {fixed(ci.high)}] · [{fixed(floor.low)}, {fixed(floor.high)}]
          </p>
          <p className="small text-agent" style={{ marginTop: 4 }}>
            {summary.overlap ? 'Overlapping — directional, not significant' : 'Not overlapping'}
          </p>
          <p className="tiny">cluster bootstrap by silo, {ci.n_boot.toLocaleString('en-US')} resamples, {ci.n_clusters} silos</p>
          <Srcs paths={[ci.source, floor.source]} />
        </div>
        <div className="tile">
          <p className="eyebrow">Faithfulness · global</p>
          <p className="tile-num tile-num--sm">deletion {fixed(global.deletion_auc)} · insertion {fixed(global.insertion_auc)}</p>
          <p className="tiny">{faith.config_label} spot check, not a gate</p>
          <Srcs paths={FAITH_SRC} />
        </div>
      </div>

      <details className="disc">
        <summary>Per-family breakdown <span className="mono-mute">median per α, eligible rows</span></summary>
        <div className="scroll-x" tabIndex={0} role="region" aria-label="Per-family agreement table">
          <table className="v-table">
            <thead>
              <tr>
                <th>family</th>
                {alphas.map((a) => <th key={`j${a}`}>J@10 α={a}</th>)}
                {alphas.map((a) => <th key={`t${a}`}>τ α={a}</th>)}
              </tr>
            </thead>
            <tbody>
              {families.map((f) => (
                <tr key={f}>
                  <td className="txt">{f}</td>
                  {alphas.map((a) => {
                    const r = perFamily.find((x) => x.family === f && alphaStr(x.alpha) === a);
                    return <td key={`j${a}`}>{r ? fixed(r.jaccard_at_10_median) : '—'}</td>;
                  })}
                  {alphas.map((a) => {
                    const r = perFamily.find((x) => x.family === f && alphaStr(x.alpha) === a);
                    return <td key={`t${a}`}>{r ? fixed(r.tau_median) : '—'}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="tiny">— = family not eligible at that α (too few flows in too few orgs).</p>
        <Src path={AGREEMENT_SRC} />
      </details>

      <details className="disc">
        <summary>Round-wise agreement <span className="mono-mute">median Jaccard@10 across orgs and seeds, by round</span></summary>
        <RoundWise data={roundWise} />
        <p className="tiny">Directional; computed at reduced SHAP fidelity (see Limits).</p>
        <Src path={ROUNDWISE_SRC} />
      </details>

      <details className="disc">
        <summary>Faithfulness detail <span className="mono-mute">{faith.config_label}, deletion and insertion AUC</span></summary>
        <div className="scroll-x" tabIndex={0} role="region" aria-label="Faithfulness AUC table">
          <table className="v-table" style={{ maxWidth: 520 }}>
            <thead><tr><th>model</th><th>deletion AUC (lower is better)</th><th>insertion AUC (higher is better)</th></tr></thead>
            <tbody>
              {faith.auc.map((r) => (
                <tr key={r.model}><td className="txt">{r.model}</td><td>{fixed(r.deletion_auc)}</td><td>{fixed(r.insertion_auc)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="img-pair" style={{ marginTop: 12 }}>
          <img src={faithfulnessFigureUrl('deletion')} alt="Deletion curves: model confidence as top-ranked features are removed" loading="lazy" width="640" height="420" />
          <img src={faithfulnessFigureUrl('insertion')} alt="Insertion curves: model confidence as top-ranked features are reinserted" loading="lazy" width="640" height="420" />
        </div>
        <Srcs paths={FAITH_SRC} />
      </details>

      {federation && (
        <details className="disc">
          <summary>Data &amp; eligibility <span className="mono-mute">label skew per org, size floor, explanation eligibility</span></summary>
          <DataEligibility federation={federation} />
        </details>
      )}
    </section>
  );
}

function medianByRound(rows) {
  const groups = new Map();
  for (const r of rows) {
    const k = `${r.alpha}|${r.round}`;
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(r.jaccard_at_10);
  }
  const out = [...groups.entries()].map(([k, vals]) => {
    const [alpha, round] = k.split('|');
    return { alpha: alphaStr(alpha), round: Number(round), median: medianSorted(sortedNums(vals)), n: vals.length };
  });
  out.sort((a, b) => a.round - b.round);
  return out;
}

function RoundWise({ data }) {
  const alphas = [...new Set(data.map((d) => d.alpha))].sort((a, b) => Number(a) - Number(b));
  const rounds = [...new Set(data.map((d) => d.round))].sort((a, b) => a - b);
  const W = 520;
  const H = 180;
  const P = 32;
  const x = (r) => P + ((r - rounds[0]) / (rounds[rounds.length - 1] - rounds[0] || 1)) * (W - 2 * P);
  const y = (v) => H - P - v * (H - 2 * P);
  const dash = ['', '6 3', '2 3'];
  return (
    <div className="scroll-x" tabIndex={0} role="region" aria-label="Round-wise agreement">
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} role="img" aria-label="Median Jaccard at 10 by round for each alpha">
        <line x1={P} x2={W - P} y1={y(0)} y2={y(0)} stroke="var(--line2)" />
        {[0, 0.5, 1].map((v) => (
          <text key={v} x={P - 6} y={y(v) + 4} textAnchor="end" fontSize="10" fill="var(--mute)">{fixed(v, 1)}</text>
        ))}
        {rounds.map((r) => (
          <text key={r} x={x(r)} y={H - P + 14} textAnchor="middle" fontSize="10" fill="var(--mute)">r{r}</text>
        ))}
        {alphas.map((a, i) => {
          const pts = data.filter((d) => d.alpha === a);
          const last = pts[pts.length - 1];
          return (
            <g key={a}>
              <polyline points={pts.map((d) => `${x(d.round)},${y(d.median)}`).join(' ')} fill="none" stroke="var(--ink)" strokeWidth="1.5" strokeDasharray={dash[i % 3]} />
              {pts.map((d) => <circle key={d.round} cx={x(d.round)} cy={y(d.median)} r="2.5" fill="var(--ink)" />)}
              <text x={x(last.round) + 6} y={y(last.median) + 4} fontSize="10" fill="var(--body)">α={a}</text>
            </g>
          );
        })}
      </svg>
      <table className="v-table" style={{ maxWidth: 520 }}>
        <thead><tr><th>α</th>{rounds.map((r) => <th key={r}>r{r}</th>)}</tr></thead>
        <tbody>
          {alphas.map((a) => (
            <tr key={a}>
              <td className="txt">{a}</td>
              {rounds.map((r) => {
                const d = data.find((z) => z.alpha === a && z.round === r);
                return <td key={r}>{d ? fixed(d.median) : '—'}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
