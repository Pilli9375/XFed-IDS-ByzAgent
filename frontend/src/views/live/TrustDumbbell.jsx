import Src from '../../components2/Src';
import { CONFOUND_CLEAN_RATE, LIFT_HIGHLIGHT, conditionLabel, conditionSources } from '../../lib/trust2';
import { buildCleanVsAttackRows } from '../../lib/trust';
import { fixed, signed } from '../../lib/format';

// Clean ○ → attack ● flag rate per org for one /trust condition, with lift.
// Replaces the misplotted Recharts lift chart (inventory item 5.3).
export default function TrustDumbbell({ trust, condIdx, onCond }) {
  const cond = trust.conditions[condIdx];
  const rows = buildCleanVsAttackRows(cond.clean.per_silo, cond.attack.per_silo, cond.true_malicious_silos);
  const confound = rows.filter((r) => !r.malicious && r.clean_flag_rate >= CONFOUND_CLEAN_RATE).map((r) => r.silo);
  return (
    <section aria-labelledby="trust-h" className="panel p-trust">
      <div className="panel-head panel-head--col">
        <h2 id="trust-h">Trust check</h2>
        <label className="sr-only" htmlFor="live-cond">Attack condition</label>
        <select id="live-cond" className="v-select" value={condIdx} onChange={(e) => onCond(Number(e.target.value))}>
          {trust.conditions.map((c, i) => (
            <option key={c.attack_tag} value={i}>{conditionLabel(c)}</option>
          ))}
        </select>
      </div>
      <div style={{ padding: '10px 16px 8px', display: 'flex', flexDirection: 'column' }}>
        <div role="table" aria-label="Share of rounds flagged per org, clean run and attack run">
          <div role="row" className="sr-only">
            <span role="columnheader">Org</span>
            <span role="columnheader">Clean and attack flag rate</span>
            <span role="columnheader">Lift</span>
          </div>
          {rows.map((r) => {
            const lo = Math.min(r.clean_flag_rate, r.attack_flag_rate);
            const hi = Math.max(r.clean_flag_rate, r.attack_flag_rate);
            return (
              <div role="row" key={r.silo} className="db-row">
                <span role="rowheader" className={`db-lab${r.malicious ? ' is-poisoned' : ''}`}>
                  {r.malicious ? '● ' : ''}Org {r.silo}
                  {r.malicious && <span className="sr-only"> (poisoned)</span>}
                </span>
                <span role="cell" className="db-track">
                  <span className="sr-only">
                    clean {fixed(r.clean_flag_rate, 2)}, attack {fixed(r.attack_flag_rate, 2)}
                  </span>
                  <span className="db-seg" style={{ left: `${lo * 100}%`, width: `${(hi - lo) * 100}%` }} />
                  <span className="db-c" style={{ left: `${r.clean_flag_rate * 100}%` }} />
                  <span className="db-a" style={{ left: `${r.attack_flag_rate * 100}%` }} />
                </span>
                <span role="cell" className={`db-lift${r.lift >= LIFT_HIGHLIGHT ? ' is-high' : ''}`}>{signed(r.lift, 2)}</span>
              </div>
            );
          })}
        </div>
        <div className="db-axis" aria-hidden="true">
          <span />
          <span><span>{fixed(0, 0)}</span><span>share of rounds flagged</span><span>{fixed(1, 0)}</span></span>
          <span />
        </div>
      </div>
      <div className="trust-foot">
        <span>○ clean run · <span className="text-agent">●</span> attack run · lift = attack − clean</span>
        <span>
          <span className="text-attack">●</span> poisoned (ground truth, never shown to the agent).{' '}
          {confound.length > 0
            ? `Org${confound.length > 1 ? 's' : ''} ${confound.join(', ')} ${confound.length > 1 ? 'are' : 'is'} flagged in at least ${fixed(CONFOUND_CLEAN_RATE * 100, 0)}% of rounds with no attack at all: the compositional confound.`
            : `No clean org is flagged in ${fixed(CONFOUND_CLEAN_RATE * 100, 0)}% or more of rounds without an attack in this condition.`}
        </span>
        <span className="src-list">
          {conditionSources(cond).map((p) => <Src key={p} path={p} />)}
        </span>
      </div>
    </section>
  );
}
