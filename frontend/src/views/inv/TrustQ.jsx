import { useRef, useState } from 'react';
import { Sources } from '../../components/Src';
import { fixed, pct, signed } from '../../lib/format';
import { buildCleanVsAttackRows } from '../../lib/trust';
import { LIFT_HIGHLIGHT, conditionLabel, conditionSources, orgTone } from '../../lib/trust2';

const DECISIONS = ['trust', 'downweight', 'quarantine'];
const STATS = [
  ['update_norm', 'update norm'],
  ['cosine_to_global', 'cos → global'],
  ['cosine_to_peer_mean', 'cos → peer mean'],
  ['train_loss', 'train loss'],
  ['val_accuracy', 'val accuracy'],
];

// Locked ByzAgent claim, verbatim from PROJECT_INSTRUCTIONS.md.
const LOCKED_CLAIM =
  "Both effects are present. A real compositional confound saturates some silos' flag rates independent of any attack; real attack-responsive detection is also present and becomes visible where silos are not already saturated. Seed 42's apparent null was partly a ceiling artifact of that seed's unusually bimodal composition.";

export default function TrustQ({ trust, condIdx, onCond, org, onOrg }) {
  const cond = trust.conditions[condIdx];
  const rows = buildCleanVsAttackRows(cond.clean.per_silo, cond.attack.per_silo, cond.true_malicious_silos);
  const sel = rows.find((r) => r.silo === org) ?? rows[0];
  const tone = orgTone(sel);
  const rounds = cond.attack.decision_grid.rounds;
  const [round, setRound] = useState(null);
  const shownRound = round ?? rounds[rounds.length - 1];
  const pickerRef = useRef(null);

  const onPickerKey = (e) => {
    const i = rows.findIndex((r) => r.silo === sel.silo);
    let j = null;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') j = (i + 1) % rows.length;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') j = (i - 1 + rows.length) % rows.length;
    if (e.key === 'Home') j = 0;
    if (e.key === 'End') j = rows.length - 1;
    if (j == null) return;
    e.preventDefault();
    onOrg(rows[j].silo);
    pickerRef.current?.querySelectorAll('button')[j]?.focus();
  };

  const tag =
    tone === 'attack'
      ? 'POISONED · GROUND TRUTH, NEVER SHOWN TO THE AGENT'
      : tone === 'agent'
        ? 'CLEAN · FLAGGED EVEN WITHOUT AN ATTACK'
        : 'CLEAN';
  const note =
    tone === 'attack'
      ? 'The agent saw only five per-round statistics. Lift is the share of rounds flagged under attack minus the share flagged in the clean run.'
      : tone === 'agent'
        ? 'High flag rate in both runs: the compositional confound. A raw flag rate alone cannot tell this org apart from a poisoned one.'
        : 'Rarely flagged in either run.';

  const base = trust.baselines;
  const mkSlots = base.multikrum_exclusions.reduce((s, x) => s + x.n_malicious_slots, 0);
  const mkExcl = base.multikrum_exclusions.reduce((s, x) => s + x.n_excluded, 0);
  const p3 = trust.decision_variance.filter((c) => c.phase === '3' && c.mode === 'current_round');
  const p3Stable = p3.reduce((s, c) => s + c.n_exact_stable, 0);
  const p3Boundary = p3.reduce((s, c) => s + c.n_boundary_stable, 0);
  const p3N = p3.reduce((s, c) => s + c.n_silos, 0);
  const fid = trust.fidelity;

  const sevOf = (side) => cond[side].decision_grid.silos.find((s) => s.silo_id === sel.silo)?.severities ?? [];
  const textOf = (side) => cond[side].explanations.find((x) => x.silo_id === sel.silo && x.round === shownRound);
  const seriesOf = (side) => cond[side].stat_series.silos.find((s) => s.silo_id === sel.silo);

  return (
    <section id="q3" aria-labelledby="q3h" className={`q panel--focus tone-${tone}`}>
      <div className="q-head" style={{ alignItems: 'center' }}>
        <div>
          <span className="eyebrow">03 · Trust check</span>
          <h2 id="q3h" className="h2">Is anyone poisoning it?</h2>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-end' }}>
          <label className="sr-only" htmlFor="inv-cond">Attack condition</label>
          <select id="inv-cond" className="v-select" value={condIdx} onChange={(e) => onCond(Number(e.target.value))}>
            {trust.conditions.map((c, i) => (
              <option key={c.attack_tag} value={i}>{conditionLabel(c)}</option>
            ))}
          </select>
          <div role="group" aria-label="Organization" className="org-picker" ref={pickerRef} onKeyDown={onPickerKey}>
            {rows.map((r) => (
              <button
                key={r.silo}
                type="button"
                aria-pressed={r.silo === sel.silo}
                tabIndex={r.silo === sel.silo ? 0 : -1}
                className={`org-btn${r.malicious ? ' is-poisoned' : ''}`}
                aria-label={`Org ${r.silo}${r.malicious ? ', poisoned' : ''}`}
                onClick={() => onOrg(r.silo)}
              >
                {r.malicious ? '● ' : ''}
                {r.silo}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div className={`org-card tone-${tone}`}>
          <span className="org-tag">ORG {sel.silo} · {tag}</span>
          <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap' }}>
            <div><p className="small">flagged, clean run</p><p className="big-num">{fixed(sel.clean_flag_rate, 2)}</p></div>
            <div><p className="small">flagged, attack run</p><p className={`big-num${sel.lift >= LIFT_HIGHLIGHT ? ' is-high' : ''}`}>{fixed(sel.attack_flag_rate, 2)}</p></div>
            <div><p className="small">lift</p><p className={`big-num${sel.lift >= LIFT_HIGHLIGHT ? ' is-high' : ''}`}>{signed(sel.lift, 2)}</p></div>
          </div>
          <p className="small">{note}</p>
        </div>
        <div className="tiles-3">
          <div className="tile">
            <p className="small">Multi-Krum excluded a poisoned org</p>
            <p className="tile-num text-attack">{pct(mkExcl / mkSlots, 0)}</p>
            <p className="tiny">
              seed {base.seed}, told f exactly · {mkExcl} of {mkSlots} poisoned org-rounds
            </p>
          </div>
          <div className="tile">
            <p className="small">Cost with no attack</p>
            <p className="tile-num tile-num--sm">{base.defence_costs.map((c) => fixed(c.cost_pp, 1)).join(' / ')} pp</p>
            <p className="tiny">{base.defence_costs.map((c) => c.label).join(' / ')} · logged test macro-F1 vs clean FedAvg</p>
          </div>
          <div className="tile">
            <p className="small">Decision stability</p>
            <p className="tile-num">{p3Stable}/{p3N}</p>
            <p className="tiny">
              round {p3[0]?.round}, {p3[0]?.repeats}× repeats · trust-vs-flag {p3Boundary}/{p3N} · the LLM is nondeterministic
            </p>
          </div>
        </div>
      </div>

      <div>
        <div className="q-head" style={{ marginBottom: 8 }}>
          <h3 style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>Org {sel.silo}, round by round</h3>
          <div className="legend">
            <span><i className="sev-0" />trust</span>
            <span><i className="sev-1" />downweight</span>
            <span><i className="sev-2" />quarantine</span>
          </div>
        </div>
        <div className="scroll-x" tabIndex={0} role="region" aria-label="Per-round decisions for the selected org">
          <div role="group" aria-label={`Per-round decisions for org ${sel.silo}; choose a round to read its rationale`}>
            {['clean', 'attack'].map((side) => (
              <div key={side} className="strip" style={{ marginBottom: 4 }}>
                <span className="mono-mute">{side}</span>
                {sevOf(side).map((sev, k) => (
                  <button
                    key={k}
                    type="button"
                    className={`strip-cell sev-${sev ?? 'x'}`}
                    aria-pressed={rounds[k] === shownRound}
                    aria-label={`${side} run, round ${rounds[k]}: ${sev == null ? 'no decision' : DECISIONS[sev]}`}
                    title={`round ${rounds[k]} · ${sev == null ? 'no decision' : DECISIONS[sev]}`}
                    onClick={() => setRound(rounds[k])}
                  />
                ))}
              </div>
            ))}
            <div className="strip" aria-hidden="true">
              <span className="mono-mute">round</span>
              {rounds.map((r) => (
                <span key={r} className="mono-mute" style={{ textAlign: 'center', fontSize: 10 }}>{r}</span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="sparks">
        {STATS.map(([key, label]) => (
          <Spark key={key} label={label} clean={seriesOf('clean')?.[key]} attack={seriesOf('attack')?.[key]} rounds={rounds} round={shownRound} />
        ))}
      </div>

      <div className="rationale" aria-live="polite">
        <span className="eyebrow">Round {shownRound} · verbatim agent rationale · a rationale of measured fidelity</span>
        {['clean', 'attack'].map((side) => {
          const x = textOf(side);
          return (
            <p key={side}>
              <span className="mono-mute">{side} run · {x ? x.decision : 'no logged decision'}</span>
              <br />
              {x ? <>“{x.text}”</> : <span className="text-mute">No rationale logged for this org and round.</span>}
            </p>
          );
        })}
        <p className="tiny">{trust.nondeterminism_notice}</p>
      </div>

      <blockquote className="quote">“{LOCKED_CLAIM}”</blockquote>
      <p className="small">
        The agent produces decisions plus a rationale of measured fidelity; ~{fixed(fid.adjusted_error_rate_low * 100, 0)}–
        {fixed(fid.automated_error_rate * 100, 0)}% of its trend claims contradicted the data it was given ({fid.n_trend_claims} claims;
        range adjusted by a {fid.handcheck_n}-claim hand-check).
      </p>

      <details className="disc">
        <summary>All orgs, all rounds <span className="mono-mute">decision grids, clean and attack</span></summary>
        <div className="scroll-x" tabIndex={0} role="region" aria-label="Decision grids, all orgs">
          {['clean', 'attack'].map((side) => (
            <div key={side} style={{ marginBottom: 12 }}>
              <p className="eyebrow" style={{ marginBottom: 6 }}>{side} run · {cond[side].run_tag}</p>
              {cond[side].decision_grid.silos.map((s) => (
                <div key={s.silo_id} className="strip" style={{ marginBottom: 3 }}>
                  <span className={`mono-mute${cond.true_malicious_silos.includes(s.silo_id) ? ' text-attack' : ''}`}>
                    {cond.true_malicious_silos.includes(s.silo_id) ? '● ' : ''}org {s.silo_id}
                  </span>
                  {s.severities.map((sev, k) => (
                    <span key={k} className={`strip-cell sev-${sev ?? 'x'}`} style={{ cursor: 'default', height: 14 }} title={`round ${rounds[k]} · ${sev == null ? 'none' : DECISIONS[sev]}`} />
                  ))}
                </div>
              ))}
            </div>
          ))}
        </div>
      </details>

      <details className="disc">
        <summary>Decision stability by condition <span className="mono-mute">repeat the same round, compare decisions</span></summary>
        <div className="scroll-x" tabIndex={0} role="region" aria-label="Decision stability table">
          <table className="v-table">
            <thead>
              <tr><th>phase · mode</th><th>condition</th><th>round</th><th>exact</th><th>trust vs flag</th></tr>
            </thead>
            <tbody>
              {trust.decision_variance.map((c) => (
                <tr key={`${c.phase}${c.mode}${c.condition}`}>
                  <td className="txt">{c.phase} · {c.mode.replace('_', ' ')}</td>
                  <td className="txt">{c.condition}</td>
                  <td>{c.round}</td>
                  <td>{c.n_exact_stable}/{c.n_silos}</td>
                  <td>{c.n_boundary_stable == null ? '—' : `${c.n_boundary_stable}/${c.n_silos}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      <details className="disc">
        <summary>Oracle asymmetry <span className="mono-mute">what the baselines were told</span></summary>
        <p className="small" style={{ maxWidth: 760 }}>
          Krum, Multi-Krum and trimmed-mean were each given the true number of poisoned orgs (f) as an oracle; the agent was not.
          Multi-Krum still excluded {mkExcl} of {mkSlots} poisoned org-rounds at seed {base.seed}: its exclusions follow org size
          and composition, not the attack. Classical Krum keeps one org per round, so its exclusions are chance-level.
        </p>
      </details>
      <Sources
        paths={[
          ...conditionSources(cond),
          ...base.multikrum_exclusions.flatMap((x) => [x.source, x.attack_config]),
          base.clean_reference_source,
          ...base.defence_costs.map((c) => c.source),
          ...trust.decision_variance.map((c) => c.source),
          ...fid.sources,
        ]}
      />
      {trust.excluded_conditions.length > 0 && (
        <p className="tiny">
          Not shown: {trust.excluded_conditions.map((x) => `${x.attack_tag} (${x.reason})`).join('; ')}
        </p>
      )}
    </section>
  );
}

function Spark({ label, clean, attack, rounds, round }) {
  if (!clean || !attack) return null;
  const all = [...clean, ...attack].filter((v) => v != null);
  const lo = Math.min(...all);
  const hi = Math.max(...all);
  const W = 160;
  const H = 44;
  const x = (k) => (k / (rounds.length - 1)) * W;
  const y = (v) => H - 3 - ((v - lo) / (hi - lo || 1)) * (H - 6);
  const line = (vals) => vals.map((v, k) => (v == null ? null : `${x(k)},${y(v)}`)).filter(Boolean).join(' ');
  const k = rounds.indexOf(round);
  return (
    <div className="spark">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6 }}>
        <span className="eyebrow" style={{ fontSize: 10 }}>{label}</span>
        <span className="mono-mute" style={{ fontSize: 10 }}>{fixed(lo, 3)}–{fixed(hi, 3)}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label={`${label}: clean run and attack run over ${rounds.length} rounds, range ${fixed(lo, 3)} to ${fixed(hi, 3)}`} preserveAspectRatio="none">
        {k >= 0 && <line x1={x(k)} x2={x(k)} y1="0" y2={H} stroke="var(--line2)" strokeWidth="1" />}
        <polyline points={line(clean)} fill="none" stroke="var(--body)" strokeWidth="1.25" strokeDasharray="3 2" vectorEffect="non-scaling-stroke" />
        <polyline points={line(attack)} fill="none" stroke="var(--ink)" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="legend" style={{ fontSize: 10 }}>
        <span>– – clean</span>
        <span>— attack</span>
        {k >= 0 && <span className="text-mute">r{round}: {fixed(clean[k], 3)} / {fixed(attack[k], 3)}</span>}
      </div>
    </div>
  );
}
