import { useMemo } from 'react';
import { useAgreement } from '../api/useAgreement';
import Callout from '../components/Callout';
import DataTable from '../components/DataTable';
import Rule from '../components/Rule';
import SectionHeader from '../components/SectionHeader';
import Stat from '../components/Stat';
import Subhead from '../components/Subhead';
import Tabs from '../components/Tabs';
import AgreementVsAlphaChart from '../charts/AgreementVsAlphaChart';
import FloorComparisonChart from '../charts/FloorComparisonChart';
import PerFamilyGroupedChart from '../charts/PerFamilyGroupedChart';
import {
  CHANCE_LEVEL_JACCARD_AT_10,
  computeHeadlineAgreement,
  computeInstabilityFloorSummary,
  computePerFamilyAgreement,
  computePerSeedAgreement,
  fmt3,
  formatAlpha,
  shapeAgreementSeries,
} from '../lib/agreement';
import { ACCENT, ALERT, POSITIVE, TEXT_FAINT, VIOLET, WARN } from '../theme/tokens';

// Bot/WebAttack near-duplication was tested, not confirmed -- see
// PROJECT_INSTRUCTIONS.md "Known findings" and [[feedback_claim_sourcing_hierarchy]].
const CAVEAT_FAMILIES = new Set(['Bot', 'WebAttack']);

const PER_FAMILY_COLUMNS = [
  { key: 'alpha', label: 'α', render: (r) => r.alpha },
  { key: 'family', label: 'Family', render: (r) => r.family },
  { key: 'jaccard', label: 'Jaccard@10 (median)', render: (r) => fmt3(r.jaccard_at_10_median) },
  { key: 'tau', label: 'Weighted τ (median)', render: (r) => fmt3(r.tau_median) },
  { key: 'n_rows', label: 'Eligible rows', render: (r) => r.n_rows },
  {
    key: 'note',
    label: 'Note',
    render: (r) =>
      r.family === 'PortScan'
        ? '✅ generalization signal'
        : CAVEAT_FAMILIES.has(r.family)
          ? '⚠️ tested, not confirmed'
          : '',
  },
];

const HEADLINE_COLUMNS = [
  { key: 'alpha', label: 'α', render: (h) => h.alpha },
  { key: 'jaccard_median', label: 'Jaccard@10 (median)', render: (h) => fmt3(h.jaccard_at_10_median) },
  {
    key: 'jaccard_iqr',
    label: 'Jaccard@10 IQR',
    render: (h) => `${fmt3(h.jaccard_at_10_q25)} – ${fmt3(h.jaccard_at_10_q75)}`,
  },
  { key: 'tau_median', label: 'Weighted τ (median)', render: (h) => fmt3(h.tau_median) },
  { key: 'tau_iqr', label: 'Weighted τ IQR', render: (h) => `${fmt3(h.tau_q25)} – ${fmt3(h.tau_q75)}` },
  { key: 'n_rows', label: 'Eligible rows', render: (h) => h.n_rows },
];

export default function ExplanationAgreement({ eyebrow, title, lede }) {
  const status = useAgreement();

  return (
    <>
      <SectionHeader eyebrow={eyebrow} title={title} lede={lede} />
      <Rule />
      {status.state === 'loading' && <Callout tone={TEXT_FAINT}>Loading GET /agreement…</Callout>}
      {status.state === 'error' && (
        <Callout tone={ALERT}>Could not load GET /agreement: {status.error}</Callout>
      )}
      {status.state === 'ok' && <AgreementBody data={status.data} />}
    </>
  );
}

function AgreementBody({ data }) {
  const headline = useMemo(() => computeHeadlineAgreement(data.agreement_metrics), [data]);
  const perSeed = useMemo(() => computePerSeedAgreement(data.agreement_metrics), [data]);
  const perFamily = useMemo(() => computePerFamilyAgreement(data.agreement_metrics), [data]);
  const floorSummary = useMemo(
    () => computeInstabilityFloorSummary(data.centralized_instability_floor),
    [data],
  );

  if (headline.length === 0) {
    return (
      <Callout tone={WARN}>
        No family_eligible rows found in agreement_metrics -- nothing to show.
      </Callout>
    );
  }

  const alphaLabels = headline.map((h) => formatAlpha(h.alpha));
  const jLo = headline[0].jaccard_at_10_median;
  const jHi = headline[headline.length - 1].jaccard_at_10_median;
  const tLo = headline[0].tau_median;
  const tHi = headline[headline.length - 1].tau_median;

  const jaccardSeries = shapeAgreementSeries(headline, perSeed, 'jaccard_at_10');
  const tauSeries = shapeAgreementSeries(headline, perSeed, 'tau');

  return (
    <>
      <Subhead
        title="Agreement vs. heterogeneity"
        lede="Lower α means more heterogeneous silos. The shaded band is the 25th–75th
          percentile across all eligible (silo, sample) pairs — a real spread from the
          data, <b>not</b> a fitted confidence interval. White dots are per-seed medians."
      />
      <div style={{ height: 'var(--sp-md)' }} />

      <div className="xf-grid-3">
        <Stat
          label="Jaccard@10 range"
          value={`${fmt3(jLo)} → ${fmt3(jHi)}`}
          sub="α = 0.1 → 5.0"
          tone={ACCENT}
          small
        />
        <Stat
          label="Weighted τ range"
          value={`${fmt3(tLo)} → ${fmt3(tHi)}`}
          sub="α = 0.1 → 5.0"
          tone={VIOLET}
          small
        />
        <Stat
          label="Above chance"
          value={`${(jLo / CHANCE_LEVEL_JACCARD_AT_10).toFixed(1)}× – ${(jHi / CHANCE_LEVEL_JACCARD_AT_10).toFixed(1)}×`}
          sub={`Chance Jaccard@10 ≈ ${fmt3(CHANCE_LEVEL_JACCARD_AT_10)}`}
          tone={POSITIVE}
          small
        />
      </div>
      <div style={{ height: 'var(--sp-md)' }} />

      <div className="xf-grid-2">
        <div className="xf-chart-card">
          <AgreementVsAlphaChart
            chartData={jaccardSeries.chartData}
            scatterData={jaccardSeries.scatterData}
            alphaLabels={alphaLabels}
            yLabel="Jaccard@10"
            chance={CHANCE_LEVEL_JACCARD_AT_10}
          />
        </div>
        <div className="xf-chart-card">
          <AgreementVsAlphaChart
            chartData={tauSeries.chartData}
            scatterData={tauSeries.scatterData}
            alphaLabels={alphaLabels}
            yLabel="Weighted Kendall's τ"
            chance={null}
          />
        </div>
      </div>

      <Rule />

      <Subhead title="Headline numbers" />
      <div style={{ height: 'var(--sp-sm)' }} />
      <DataTable columns={HEADLINE_COLUMNS} rows={headline} getRowKey={(h) => h.alpha} />
      <div className="xf-caption">
        Chance-level Jaccard@10 ≈ {fmt3(CHANCE_LEVEL_JACCARD_AT_10)} (random top-10 overlap out of 82
        features). Even at α=0.1, agreement sits {(jLo / CHANCE_LEVEL_JACCARD_AT_10).toFixed(1)}× above
        chance — silos disagree relative to α=5.0, but not randomly.
      </div>

      <Rule />

      <PerFamilySection perFamily={perFamily} />

      <Rule />

      <FloorSection headline={headline} floorSummary={floorSummary} />
    </>
  );
}

function PerFamilySection({ perFamily }) {
  const alphas = [...new Set(perFamily.map((r) => r.alpha))].sort((a, b) => a - b);
  const families = [...new Set(perFamily.map((r) => r.family))].sort();

  const shape = (metricKey) =>
    families.map((family) => {
      const row = { family };
      for (const a of alphas) {
        const rec = perFamily.find((r) => r.family === family && r.alpha === a);
        row[`a_${a}`] = rec ? rec[metricKey] : null;
      }
      return row;
    });

  return (
    <>
      <Subhead title="Per-family breakdown" />
      <div style={{ height: 'var(--sp-sm)' }} />
      {/* PortScan framing: verbatim from sections.py -- no supersession.
          Bot/WebAttack framing: CORRECTED per project precedence
          (docs/contribution_a_results.md > PROJECT_INSTRUCTIONS.md >
          sections.py). sections.py's original wording frames this as a
          live, unresolved caveat ("may reflect near-duplicate rows rather
          than genuine model fidelity"); PROJECT_INSTRUCTIONS.md's later
          finding says the pre-registered caveat was tested and NOT
          confirmed. Using the corrected framing here, not sections.py's. */}
      <Callout tone={WARN}>
        <b>PortScan is the family that actually tests explanation generalization.</b> Bot
        and WebAttack were flagged for a pre-registered near-duplication caveat (train/test
        rows nearly identical for these families) — <b>tested, and not confirmed</b>: thin
        dataset support (Bot=3,527, WebAttack=1,542 rows) is the likelier explanation.
        Reported, not suppressed.
      </Callout>
      <div style={{ height: 'var(--sp-sm)' }} />

      <div className="xf-chart-card">
        <Tabs
          items={[
            { label: 'Jaccard@10', content: <PerFamilyGroupedChart data={shape('jaccard_at_10_median')} alphas={alphas} /> },
            { label: 'Weighted τ', content: <PerFamilyGroupedChart data={shape('tau_median')} alphas={alphas} /> },
          ]}
        />
      </div>
      <div style={{ height: 'var(--sp-sm)' }} />

      <DataTable
        columns={PER_FAMILY_COLUMNS}
        rows={perFamily}
        getRowKey={(r) => `${r.alpha}-${r.family}`}
      />
    </>
  );
}

function FloorSection({ headline, floorSummary }) {
  const alpha01 = headline.find((h) => h.alpha === 0.1);

  return (
    <>
      <Subhead title="Is the α=0.1 agreement drop real, or seed noise?" />
      <div style={{ height: 'var(--sp-sm)' }} />

      {floorSummary == null ? (
        <Callout tone={WARN}>results/inspection/centralized_instability_floor.csv not found.</Callout>
      ) : alpha01 == null ? (
        <Callout tone={ACCENT}>No α=0.1 rows found in the headline agreement table.</Callout>
      ) : (
        <>
          <div className="xf-grid-2">
            <Stat
              label="Instability floor — Jaccard@10"
              value={fmt3(floorSummary.jaccard_at_10_median)}
              sub="Centralized seed-pairs, no federation involved"
              tone={ALERT}
            />
            <Stat
              label="Federated agreement — Jaccard@10"
              value={fmt3(alpha01.jaccard_at_10_median)}
              sub="α = 0.1"
              tone={ACCENT}
            />
          </div>
          <div style={{ height: 'var(--sp-md)' }} />

          <div className="xf-chart-card">
            <FloorComparisonChart
              data={[
                {
                  label: 'Instability floor (centralized seed-pairs)',
                  value: floorSummary.jaccard_at_10_median,
                  q25: floorSummary.jaccard_at_10_q25,
                  q75: floorSummary.jaccard_at_10_q75,
                  errorRange: [
                    floorSummary.jaccard_at_10_median - floorSummary.jaccard_at_10_q25,
                    floorSummary.jaccard_at_10_q75 - floorSummary.jaccard_at_10_median,
                  ],
                },
                {
                  label: 'Federated α=0.1',
                  value: alpha01.jaccard_at_10_median,
                  q25: alpha01.jaccard_at_10_q25,
                  q75: alpha01.jaccard_at_10_q75,
                  errorRange: [
                    alpha01.jaccard_at_10_median - alpha01.jaccard_at_10_q25,
                    alpha01.jaccard_at_10_q75 - alpha01.jaccard_at_10_median,
                  ],
                },
              ]}
            />
          </div>

          {/* Verbatim from app_lib/sections.py's render_methods() callout --
              do not rephrase: this is the directional-not-significant caveat. */}
          <Callout tone={WARN}>
            <b>Directional observation, not a statistical test.</b> The IQR bands above
            overlap — federated α=0.1 agreement sits close to, not clearly below, the
            seed-to-seed instability floor measured from centralized models alone. No
            significance test has been run. Reported as directional, never claimed as
            significant.
          </Callout>
        </>
      )}
    </>
  );
}
