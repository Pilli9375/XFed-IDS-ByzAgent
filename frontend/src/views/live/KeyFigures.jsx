import Src from '../../components2/Src';
import { fixed, int, meanSd, signed } from '../../lib/format';

// Four figures from GET /figures. Each value and sub-line is formatted from
// the endpoint's fields; the source link names the file each was read from.
export default function KeyFigures({ figures: f }) {
  const m = f.fedavgm_test_macro_f1;
  const b = f.fedavg_test_macro_f1;
  const lat = f.latency;
  const up = f.upload;
  const tr = f.traffic;
  const items = [
    {
      label: (
        <>
          Macro-F1 · <span className="keep">α={m.alpha}</span>
        </>
      ),
      key: 'f1',
      value: fixed(m.mean, 4),
      unit: `± ${fixed(m.std, 4)}`,
      sub: `FedAvgM, preregistered test, n=${m.n} · FedAvg ${meanSd(b.mean, b.std)}`,
      src: [m.source, b.source],
    },
    {
      label: 'Per-flow latency',
      value: fixed(lat.serving_p50_us, 1),
      unit: 'µs',
      sub: `ONNX fp32 p50 · PyTorch ${fixed(lat.reference_p50_us, 1)} µs · ${lat.n_sessions} sessions`,
      src: [lat.source],
    },
    {
      label: 'Upload per round',
      value: signed(-up.bytes_up_saved_pct, 0),
      unit: '%',
      sub: `${up.scheme} updates · mean Δ ${signed(up.delta_mean, 4)}, n=${up.n_seeds}`,
      src: [up.source],
    },
    {
      label: 'Traffic per round',
      value: int(tr.per_round_bytes),
      unit: 'B',
      sub: `${tr.n_silos} orgs, both directions`,
      src: [tr.source],
    },
  ];
  return (
    <section aria-label="Key figures" className="kpis">
      {items.map((k) => (
        <div key={k.key ?? k.label} className="kpi">
          <span className="eyebrow">{k.label}</span>
          <span className="kpi-value">
            {k.value}
            <span className="kpi-unit">{k.unit}</span>
          </span>
          <span className="small">{k.sub}</span>
          <span className="src-list">
            {[...new Set(k.src)].map((p) => (
              <Src key={p} path={p} />
            ))}
          </span>
        </div>
      ))}
    </section>
  );
}
