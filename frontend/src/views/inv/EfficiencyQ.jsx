import { Sources } from '../../components/Src';
import { fixed, int, signed } from '../../lib/format';

// 04: four tiles from GET /figures, plus what was tested and dropped.
export default function EfficiencyQ({ f }) {
  const lat = f.latency;
  const up = f.upload;
  const up2 = f.upload_alt;
  const tr = f.traffic;
  const rt = f.round_time;
  const pre = f.prescreen;
  const tiles = [
    {
      label: 'Per-flow latency',
      value: `${fixed(lat.serving_p50_us, 1)} µs`,
      sub: `ONNX fp32 p50 vs ${fixed(lat.reference_p50_us, 1)} µs PyTorch; prediction agreement ${fixed(lat.prediction_agreement * 100, 0)}%`,
      kind: `${lat.n_sessions} sessions · batch ${int(lat.throughput_batch_size)}: PyTorch ${lat.reference_rows_per_sec > lat.serving_rows_per_sec ? 'faster' : 'slower'}`,
      src: [lat.source],
    },
    {
      label: 'Upload size',
      value: `${signed(-up.bytes_up_saved_pct, 0)}% / ${signed(-up2.bytes_up_saved_pct, 1)}%`,
      sub: `${up.scheme} / ${up2.scheme} updates; mean Δ val macro-F1 ${signed(up.delta_mean, 4)} / ${signed(up2.delta_mean, 4)}`,
      kind: `${up.n_seeds} seeds · no detectable effect`,
      src: [up.source],
    },
    {
      label: 'Traffic per round',
      value: `${int(tr.per_round_bytes)} B`,
      sub: `${int(tr.n_parameters)} params × ${tr.n_silos} orgs × ${tr.directions_per_round} directions`,
      kind: tr.matches_logs ? 'computed · matches logs' : 'computed · differs from logs',
      src: [tr.source],
    },
    {
      label: 'Time per round',
      value: `${fixed(rt.median_s, 1)} s`,
      sub: `median over ${rt.n_runs} runs, CPU`,
      kind: 'existing runs',
      src: [rt.source],
    },
  ];
  const s1337 = pre.transfer.find((t) => t.seed !== pre.selection_seed);
  return (
    <section id="q4" aria-labelledby="q4h" className="q">
      <div>
        <span className="eyebrow">04 · Efficiency</span>
        <h2 id="q4h" className="h2">What does it cost to run?</h2>
      </div>
      <div className="grid-line">
        {tiles.map((t) => (
          <div key={t.label} className="cell">
            <span className="eyebrow">{t.label}</span>
            <span className="num" style={{ fontSize: 24, letterSpacing: '-0.03em' }}>{t.value}</span>
            <span className="small">{t.sub}</span>
            <span className="eyebrow" style={{ fontSize: 10, marginTop: 4 }}>{t.kind}</span>
          </div>
        ))}
      </div>
      <p className="small">
        Tested and dropped: int8 inference ({signed(f.int8_inference.delta_val_macro_f1, 4)} val macro-F1) and a train_loss
        pre-screen for the agent, chosen on seed {pre.selection_seed}, which did not transfer
        {s1337 && (
          <>
            {' '}(seed {s1337.seed} poisoned flag rate {fixed(s1337.flag_rate_poisoned_replay, 3)} vs logged{' '}
            {fixed(s1337.flag_rate_poisoned_logged, 3)})
          </>
        )}
        .
      </p>
      <Sources paths={[...tiles.flatMap((t) => t.src), f.int8_inference.source, pre.source]} />
    </section>
  );
}
