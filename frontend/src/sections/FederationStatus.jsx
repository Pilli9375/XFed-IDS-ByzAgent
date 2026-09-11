import { useMemo, useState } from 'react';
import { useFederation } from '../api/useFederation';
import Callout from '../components/Callout';
import DataTable from '../components/DataTable';
import Expander from '../components/Expander';
import Pills from '../components/Pills';
import Rule from '../components/Rule';
import SectionHeader from '../components/SectionHeader';
import Stat from '../components/Stat';
import Subhead from '../components/Subhead';
import SiloHeatmap from '../charts/SiloHeatmap';
import { ACCENT, ALERT, POSITIVE, TEXT_FAINT, VIOLET, WARN, familyColor } from '../theme/tokens';

// Normalizes an alpha value (seen as both a JS number and a string across
// backend restarts of GET /federation) to the canonical string form every
// per-row record (silo_sizes, manifest_summaries, eligibility tables) uses
// -- "0.1"/"0.5"/"5.0" -- so equality filtering works regardless of which
// type shape.alphas itself happens to be this time.
function alphaKey(a) {
  return Number(a).toFixed(1);
}

const MANIFEST_COLUMNS = [
  { key: 'alpha', label: 'α', render: (r) => r.alpha },
  { key: 'seed', label: 'Seed', render: (r) => r.seed },
  { key: 'tag', label: 'Config', render: (r) => r.tag },
  { key: 'best_round', label: 'Best Round (of 20)', render: (r) => r.best_round },
  { key: 'val', label: 'Val Macro-F1 (headline)', render: (r) => r.val_macro_f1_headline.toFixed(4) },
  { key: 'test', label: 'Test Macro-F1 (headline)', render: (r) => r.test_macro_f1_headline.toFixed(4) },
];

const SILO_EXCLUDED_COLUMNS = [
  { key: 'alpha', label: 'α', render: (r) => r.alpha },
  { key: 'seed', label: 'Seed', render: (r) => r.seed },
  { key: 'silo', label: 'Silo', render: (r) => r.silo },
  { key: 'total_flows', label: 'Total flows', render: (r) => r.total_flows.toLocaleString() },
];

const ELIGIBILITY_COLUMNS = [
  { key: 'alpha', label: 'α', render: (r) => r.alpha },
  { key: 'seed', label: 'Seed', render: (r) => r.seed },
  { key: 'family', label: 'Family', render: (r) => r.family },
  { key: 'eligible_silos', label: 'Eligible Silos (of 10)', render: (r) => r.eligible_silos },
  { key: 'included', label: 'Included in Agreement Analysis', render: (r) => (r.family_included ? 'Yes' : 'No') },
];

const SILO_SIZE_COLUMNS = [
  { key: 'alpha', label: 'α', render: (r) => r.alpha },
  { key: 'seed', label: 'Seed', render: (r) => r.seed },
  { key: 'silo', label: 'Silo', render: (r) => r.silo },
  { key: 'family', label: 'Family', render: (r) => r.family },
  { key: 'n', label: 'Flows', render: (r) => r.n.toLocaleString() },
];

export default function FederationStatus({ eyebrow, title, lede }) {
  const status = useFederation();

  return (
    <>
      <SectionHeader eyebrow={eyebrow} title={title} lede={lede} />
      <Rule />
      {status.state === 'loading' && <Callout tone={TEXT_FAINT}>Loading GET /federation…</Callout>}
      {status.state === 'error' && (
        <Callout tone={ALERT}>Could not load GET /federation: {status.error}</Callout>
      )}
      {status.state === 'ok' && <FederationBody data={status.data} />}
    </>
  );
}

function FederationBody({ data }) {
  const { shape, label_vocab: vocab, manifest_summaries: manifest, silo_total_eligibility: siloTotal, family_eligibility: familyElig, silo_sizes: siloSizes } = data;

  // Every per-row record (silo_sizes, manifest_summaries, eligibility
  // tables) serializes alpha as a string ("0.1", "0.5", "5.0"). shape.alphas
  // itself has been observed as BOTH numbers and strings across backend
  // restarts during this project -- alphaKey() normalizes either to the
  // canonical row-matching string instead of assuming one or the other.
  const [hmAlpha, setHmAlpha] = useState(alphaKey(shape.alphas[0]));
  const [hmSeed, setHmSeed] = useState(shape.seeds[0]);

  const heatmapRows = useMemo(
    () => siloSizes.filter((r) => r.alpha === hmAlpha && r.seed === hmSeed),
    [siloSizes, hmAlpha, hmSeed],
  );
  const allFamilies = useMemo(
    () => [...new Set(siloSizes.map((r) => r.family))].sort(),
    [siloSizes],
  );

  const siloExcluded = siloTotal.table.filter((r) => r.below_floor);
  const eligExcluded = familyElig.matrix.filter((r) => !r.family_included);

  return (
    <>
      <div className="xf-grid-4">
        <Stat label="Silos" value={String(shape.n_silos)} sub="Simulated organizations" tone={ACCENT} />
        <Stat
          label="Dirichlet α"
          value={shape.alphas.join(', ')}
          sub="Lower α = more heterogeneous"
          tone={VIOLET}
          small
        />
        <Stat
          label="Seeds"
          value={shape.seeds.join(', ')}
          sub="Every result indexed by (α, seed)"
          tone={POSITIVE}
          small
        />
        <Stat
          label="Headline families"
          value={String(vocab.headline_classes.length)}
          sub={`Plus ${vocab.below_floor_classes.length} below-floor, per-class only`}
          tone={WARN}
        />
      </div>

      <Rule />

      <Subhead
        title="Per-config results"
        lede="Each row is one (α, seed) federated run. <b>Best Round</b> is the
          validation-selected checkpoint actually used — not necessarily the final round.
          Selecting on validation rather than test is what keeps these numbers unbiased."
      />
      <div style={{ height: 'var(--sp-sm)' }} />
      <DataTable columns={MANIFEST_COLUMNS} rows={manifest} getRowKey={(r) => r.tag} />

      <Rule />

      <Subhead title="Headline taxonomy" />
      <div style={{ height: 'var(--sp-sm)' }} />
      <div className="xf-caption" style={{ margin: '0 0 0.5rem 0' }}>
        Headline macro-F1 families ({vocab.headline_classes.length})
      </div>
      <Pills items={vocab.headline_classes.map((f) => [f, familyColor(f)])} />
      <div style={{ height: 'var(--sp-sm)' }} />
      <div className="xf-caption" style={{ margin: '0 0 0.5rem 0' }}>
        Below the 1,000-flow floor — reported per-class only, excluded from headline macro-F1
      </div>
      <Pills items={vocab.below_floor_classes.map((f) => [f, TEXT_FAINT])} />

      <Rule />

      <Subhead
        title="Silo size floor"
        lede={`Independent of the per-family rule below: a silo whose <b>total</b> flow
          count across every family falls under ${siloTotal.threshold_flows} is excluded
          here. This is the source of the 1-of-90 figure.`}
      />
      <div style={{ height: 'var(--sp-sm)' }} />
      <div className="xf-grid-2">
        <Stat
          label="Excluded on total size"
          value={`${siloTotal.n_excluded} / ${siloTotal.n_total}`}
          sub={`Floor: ${siloTotal.threshold_flows} flows`}
          tone={WARN}
        />
        <Stat
          label="Silos training"
          value={String(siloTotal.n_total)}
          sub="All silos train regardless of size — exclusion applies only to
            explanation analysis (locked decision 5)"
          tone={POSITIVE}
        />
      </div>
      {siloExcluded.length > 0 && (
        <>
          <div style={{ height: 'var(--sp-sm)' }} />
          <Expander title="Excluded silo(s) (detail)">
            <DataTable columns={SILO_EXCLUDED_COLUMNS} rows={siloExcluded} getRowKey={(r) => `${r.alpha}-${r.seed}-${r.silo}`} />
          </Expander>
        </>
      )}

      <Rule />

      <Subhead title="Explanation-eligibility (per family)" />
      <div className="xf-caption">
        A silo counts as eligible for a family if it has ≥{familyElig.threshold_flows} flows
        of that family. A family is included in cross-silo explanation-agreement analysis for
        a given (α, seed) only if ≥{familyElig.min_eligible_silos} silos clear that bar.
        Computed live from silo_sizes.csv — not a separate stored artifact.
      </div>
      <div style={{ height: 'var(--sp-sm)' }} />
      <div className="xf-grid-2">
        <Stat
          label="Excluded combinations"
          value={`${familyElig.n_excluded} / ${familyElig.n_total}`}
          sub="(family, α, seed) triples below the bar"
          tone={WARN}
        />
        <Stat
          label="Eligibility rule"
          value={`≥${familyElig.threshold_flows} flows · ≥${familyElig.min_eligible_silos} silos`}
          sub="Per family, per (α, seed)"
          tone={ACCENT}
          small
        />
      </div>
      <div style={{ height: 'var(--sp-sm)' }} />
      <Expander title="Full eligibility matrix">
        <DataTable columns={ELIGIBILITY_COLUMNS} rows={familyElig.matrix} getRowKey={(r) => `${r.alpha}-${r.seed}-${r.family}`} />
      </Expander>
      {eligExcluded.length > 0 && (
        <>
          <div style={{ height: 'var(--sp-sm)' }} />
          <Expander title="Excluded combinations (detail)">
            <DataTable columns={ELIGIBILITY_COLUMNS} rows={eligExcluded} getRowKey={(r) => `${r.alpha}-${r.seed}-${r.family}`} />
          </Expander>
        </>
      )}

      {siloSizes.length > 0 && (
        <>
          <Rule />
          <Subhead
            title="Label skew across silos"
            lede="Flow counts per silo per family, log-scaled. This is what Dirichlet α
              actually does to the data — at α=0.1 a silo may hold almost none of a family
              the next silo is saturated with."
          />
          <div style={{ height: 'var(--sp-md)' }} />
          <div className="xf-grid-2" style={{ maxWidth: 420 }}>
            <div>
              <div className="xf-field-label">α</div>
              <select className="xf-select" value={hmAlpha} onChange={(e) => setHmAlpha(e.target.value)}>
                {shape.alphas.map((a) => (
                  <option key={a} value={alphaKey(a)}>
                    {a}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <div className="xf-field-label">Seed</div>
              <select className="xf-select" value={hmSeed} onChange={(e) => setHmSeed(Number(e.target.value))}>
                {shape.seeds.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div style={{ height: 'var(--sp-md)' }} />
          <div className="xf-chart-card">
            <SiloHeatmap rows={heatmapRows} families={allFamilies} nSilos={shape.n_silos} />
          </div>
          <div style={{ height: 'var(--sp-sm)' }} />
          <Expander title="Silo sizes (raw table)">
            <DataTable columns={SILO_SIZE_COLUMNS} rows={siloSizes} getRowKey={(r, i) => `${r.alpha}-${r.seed}-${r.silo}-${r.family}-${i}`} />
          </Expander>
        </>
      )}
    </>
  );
}
