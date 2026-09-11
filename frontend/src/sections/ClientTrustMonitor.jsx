import { useMemo, useState } from 'react';
import { useTrust } from '../api/useTrust';
import Callout from '../components/Callout';
import DataTable from '../components/DataTable';
import Expander from '../components/Expander';
import Pills from '../components/Pills';
import Rule from '../components/Rule';
import SectionHeader from '../components/SectionHeader';
import Subhead from '../components/Subhead';
import CleanVsAttackLiftChart from '../charts/CleanVsAttackLiftChart';
import DecisionGridHeatmap from '../charts/DecisionGridHeatmap';
import { buildCleanVsAttackRows, formatConditionLabel } from '../lib/trust';
import { ALERT, POSITIVE, TEXT_FAINT, WARN } from '../theme/tokens';

const LIFT_COLUMNS = [
  { key: 'silo', label: 'Silo', render: (r) => `silo ${r.silo}${r.malicious ? ' (malicious)' : ''}` },
  { key: 'clean', label: 'Clean flag rate', render: (r) => r.clean_flag_rate.toFixed(2) },
  { key: 'attack', label: 'Attack flag rate', render: (r) => r.attack_flag_rate.toFixed(2) },
  { key: 'lift', label: 'Lift', render: (r) => `${r.lift >= 0 ? '+' : ''}${r.lift.toFixed(2)}` },
];

const DECISION_VARIANCE_COLUMNS = [
  { key: 'phase', label: 'Phase', render: (r) => r.phase },
  { key: 'mode', label: 'Mode', render: (r) => r.mode },
  { key: 'condition', label: 'Condition', render: (r) => r.condition },
  { key: 'round', label: 'Round', render: (r) => r.round },
  { key: 'repeats', label: 'Repeats', render: (r) => r.repeats },
  { key: 'n_silos', label: 'Silos', render: (r) => r.n_silos },
  {
    key: 'exact',
    label: 'Exact-match stability',
    render: (r) => `${r.n_exact_stable}/${r.n_silos} (${Math.round(r.exact_stability_rate * 100)}%)`,
  },
  {
    key: 'boundary',
    label: 'Trust/flagged boundary stability',
    render: (r) =>
      r.boundary_stability_rate != null
        ? `${r.n_boundary_stable}/${r.n_silos} (${Math.round(r.boundary_stability_rate * 100)}%)`
        : '—',
  },
];

export default function ClientTrustMonitor({ eyebrow, title, lede }) {
  const status = useTrust();

  return (
    <>
      <SectionHeader eyebrow={eyebrow} title={title} lede={lede} />
      <Rule />
      {status.state === 'loading' && <Callout tone={TEXT_FAINT}>Loading GET /trust…</Callout>}
      {status.state === 'error' && <Callout tone={ALERT}>Could not load GET /trust: {status.error}</Callout>}
      {status.state === 'ok' && <TrustBody data={status.data} />}
    </>
  );
}

function TrustBody({ data }) {
  const { conditions, excluded_conditions: excludedConditions, decision_variance: decisionVariance, nondeterminism_notice: nondeterminismNotice } = data;
  // The selector is built directly from `conditions`, which GET /trust
  // already restricts to clean+attack pairs -- there is no "clean" entry in
  // this list to ever offer on its own.
  const [idx, setIdx] = useState(0);
  const condition = conditions.length > 0 ? conditions[Math.min(idx, conditions.length - 1)] : null;
  const rows = useMemo(
    () =>
      condition
        ? buildCleanVsAttackRows(condition.clean.per_silo, condition.attack.per_silo, condition.true_malicious_silos)
        : [],
    [condition],
  );

  if (!condition) {
    return (
      <Callout tone={WARN}>
        No paired clean/attack conditions available from GET /trust — nothing to show.
      </Callout>
    );
  }

  const nSilos = condition.clean.per_silo.length;

  return (
    <>
      {/* Verbatim from trust_monitor.py's render_trust_monitor() -- the
          load-bearing framing callout for this whole section. */}
      <Callout tone={WARN}>
        <b>This is not a demonstration of a working Byzantine detector.</b> ByzAgent's
        malicious-silo flag rate is confounded by compositional extremity: some silos are
        flagged at high rates with <b>zero attack present</b>, because the agent's stats key
        on the same low-Benign-share axis this project's worst-case attacker selection also
        selects on. Genuine attack-responsive detection is also present, visible mainly where
        a silo's clean-run rate isn't already near 1.00. Both are true at once — see{' '}
        <code>docs/contribution_b_results.md</code> §§4-7. Every flag rate below is shown next
        to its own clean-run baseline so this is visible on screen, not left to a caveat.
      </Callout>
      <div style={{ height: 'var(--sp-sm)' }} />

      <Expander title="ByzAgent vs. the classical baselines — the oracle asymmetry">
        Multi-Krum, classical Krum, and FedTrimmedAvg (Phase 2) were all given the{' '}
        <b>true</b> number of malicious silos (<code>f</code>) as an oracle. ByzAgent was
        given <b>neither</b> <code>f</code> nor any malicious-silo identity — it decides from
        behavioral stats alone. This is documented in prose in{' '}
        <code>docs/contribution_b_results.md</code> and{' '}
        <code>results/agents/PHASE3_SUMMARY.md</code>, not in a machine-readable config: no{' '}
        <code>agent_config.json</code> exists on disk, despite earlier phase-summary text
        claiming one is written per run — both documents now carry a dated correction note
        about that discrepancy. It changes no result; the asymmetry itself is real and
        unaffected.
      </Expander>
      <div style={{ height: 'var(--sp-md)' }} />

      <div>
        <div className="xf-field-label">Attack condition</div>
        <select
          className="xf-select"
          value={idx}
          onChange={(e) => setIdx(Number(e.target.value))}
        >
          {conditions.map((c, i) => (
            <option key={c.attack_tag} value={i}>
              {formatConditionLabel(c)}
            </option>
          ))}
        </select>
      </div>

      {excludedConditions.length > 0 && (
        <div className="xf-caption">
          {excludedConditions.length} condition(s) excluded by the API because no paired
          clean+attack run exists — reasons, verbatim from GET /trust:
          {excludedConditions.map((e) => (
            <div key={e.attack_tag}>
              · <code>{e.attack_tag}</code> — {e.reason}
            </div>
          ))}
        </div>
      )}

      <Rule />

      <Subhead
        title="Ground truth for this condition"
        lede={`Read from <code>results/attacks/${condition.attack_tag}/attack_config.json</code> — never hardcoded.`}
      />
      <Pills
        items={[
          ...condition.true_malicious_silos.map((s) => [`malicious: silo ${s}`, ALERT]),
          ...Array.from({ length: nSilos }, (_, s) => s)
            .filter((s) => !condition.true_malicious_silos.includes(s))
            .map((s) => [`clean: silo ${s}`, TEXT_FAINT]),
        ]}
      />

      <Rule />

      <Subhead
        title="Per-round decisions"
        lede="Rows = silos, columns = rounds. The attack-condition grid and its clean-run
          counterpart are shown together — a silo flagged in nearly every clean-run round is
          not attack-responsive detection."
      />
      <Pills
        items={[
          ['trust', POSITIVE],
          ['downweight', WARN],
          ['quarantine', ALERT],
          ['⚠ = malicious under this condition', TEXT_FAINT],
        ]}
      />
      <div style={{ height: 'var(--sp-sm)' }} />
      <Callout tone={WARN}>
        <b>These decisions are LLM-generated, not deterministic</b> — the grid renders one
        sampled outcome per cell, not a fixed function of the stats. Stability was
        spot-checked, not assumed, at round 10 only (3× independent repeats, not every round):
        90% of decisions matched exactly, and every disagreement was a downweight↔quarantine
        wobble — the trust/flagged boundary itself was 100% stable (
        <code>results/agents/PHASE3_SUMMARY.md</code>, decision-variance stability).
      </Callout>
      <div style={{ height: 'var(--sp-sm)' }} />
      {/* Clean and attack always render together, side by side -- never as
          tabs or a toggle -- so a flag pattern can never be read without its
          clean-run companion beside it. */}
      <div className="xf-grid-2">
        <div className="xf-chart-card">
          <div className="xf-caption" style={{ marginTop: 0, marginBottom: '0.6rem' }}>
            Attack condition — {formatConditionLabel(condition)}
          </div>
          <DecisionGridHeatmap
            grid={condition.attack.decision_grid}
            maliciousSilos={condition.true_malicious_silos}
          />
        </div>
        <div className="xf-chart-card">
          <div className="xf-caption" style={{ marginTop: 0, marginBottom: '0.6rem' }}>
            Clean run (no attack) — same silos, same decision log ({condition.clean.decision_log})
          </div>
          <DecisionGridHeatmap
            grid={condition.clean.decision_grid}
            maliciousSilos={condition.true_malicious_silos}
          />
        </div>
      </div>

      <Rule />

      <Subhead
        title="Clean-vs-attack flag rate, and lift"
        lede="Lift (attack flag rate − clean flag rate) is the only honest detection measure
          here — a raw flag rate alone cannot tell attack-response apart from a silo the agent
          always flags."
      />
      <div className="xf-chart-card">
        <CleanVsAttackLiftChart rows={rows} />
      </div>
      <div style={{ height: 'var(--sp-sm)' }} />
      <DataTable columns={LIFT_COLUMNS} rows={rows} getRowKey={(r) => r.silo} />

      <Rule />

      <Subhead
        title="Decision variance & nondeterminism"
        lede="GET /trust's own repeat-decision stability measurements, derived from the Phase
          3 and Phase 4 gate-analysis artifacts — not shown in the original Streamlit panel,
          which only linked out to the underlying summary docs."
      />
      {/* Verbatim, per the hard requirement -- not rephrased or shortened. */}
      <Callout tone={WARN}>{nondeterminismNotice}</Callout>
      <div style={{ height: 'var(--sp-sm)' }} />
      <DataTable
        columns={DECISION_VARIANCE_COLUMNS}
        rows={decisionVariance}
        getRowKey={(r, i) => `${r.phase}-${r.mode}-${r.condition}-${i}`}
      />
    </>
  );
}
