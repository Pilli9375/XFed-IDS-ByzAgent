import { useFaithfulness } from '../api/useFaithfulness';
import Callout from '../components/Callout';
import DataTable from '../components/DataTable';
import Pills from '../components/Pills';
import Rule from '../components/Rule';
import SectionHeader from '../components/SectionHeader';
import Subhead from '../components/Subhead';
import FaithfulnessAucChart from '../charts/FaithfulnessAucChart';
import { ALERT, POSITIVE, TEXT_FAINT, VIOLET } from '../theme/tokens';

const AUC_COLUMNS = [
  { key: 'model', label: 'Model', render: (r) => r.label },
  { key: 'deletion', label: 'Deletion AUC (lower = better)', render: (r) => r.deletion_auc.toFixed(3) },
  { key: 'insertion', label: 'Insertion AUC (higher = better)', render: (r) => r.insertion_auc.toFixed(3) },
];

function modelLabel(model) {
  return model === 'global' ? 'Global model' : model.replace('silo_', 'Silo ');
}

export default function Faithfulness({ eyebrow, title, lede }) {
  const status = useFaithfulness();

  return (
    <>
      <SectionHeader eyebrow={eyebrow} title={title} lede={lede} />
      <Rule />
      {status.state === 'loading' && <Callout tone={TEXT_FAINT}>Loading GET /faithfulness…</Callout>}
      {status.state === 'error' && (
        <Callout tone={ALERT}>Could not load GET /faithfulness: {status.error}</Callout>
      )}
      {status.state === 'ok' && <FaithfulnessBody data={status.data} />}
    </>
  );
}

function FaithfulnessBody({ data }) {
  const rows = data.auc.map((r) => ({ ...r, label: modelLabel(r.model) }));

  return (
    <>
      <Callout tone={VIOLET}>
        <b>Scope:</b> computed for one config only ({data.config_label}) and four models
        (global + silos 0–2). A project-scope decision, not a limitation of this app.
      </Callout>
      <div style={{ height: 'var(--sp-sm)' }} />

      <Subhead title="AUC summary" />
      <div style={{ height: 'var(--sp-sm)' }} />
      <Pills
        items={[
          ['↓ lower deletion AUC is better', ALERT],
          ['↑ higher insertion AUC is better', POSITIVE],
        ]}
      />
      <div style={{ height: 'var(--sp-sm)' }} />
      <DataTable columns={AUC_COLUMNS} rows={rows} getRowKey={(r) => r.model} />
      <div style={{ height: 'var(--sp-sm)' }} />
      <div className="xf-chart-card">
        <FaithfulnessAucChart data={rows} />
      </div>

      <Rule />

      <Subhead title="Curve shape" />
      <div className="xf-caption">
        No per-step data was persisted alongside the AUC summary above — only the final
        area-under-curve numbers. These are the precomputed curve images from the original
        run ({data.config_label}), embedded as-is rather than redrawn from a single number.
        Check legibility on a projector before the review — these were sized for a report
        page, not a demo screen.
      </div>
      <div style={{ height: 'var(--sp-md)' }} />

      <div className="xf-figure">
        <img src="/api/faithfulness/deletion_curve.png" alt="Deletion curve" />
        <div className="xf-figure-caption">Deletion curve — {data.config_label}</div>
      </div>
      <div className="xf-figure">
        <img src="/api/faithfulness/insertion_curve.png" alt="Insertion curve" />
        <div className="xf-figure-caption">Insertion curve — {data.config_label}</div>
      </div>
    </>
  );
}
