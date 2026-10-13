import Src, { Srcs } from '../../components/Src';
import { fixed, meanSd } from '../../lib/format';

// 01: FedAvg (aggregated CSV) vs FedAvgM (the one preregistered test
// evaluation) per alpha, with the non-federated references.
export default function AccuracyQ({ acc, federation }) {
  const c = acc.centralized;
  const x = acc.xgboost;
  return (
    <section id="q1" aria-labelledby="q1h" className="q">
      <div className="q-head">
        <div>
          <span className="eyebrow">01 · Detection</span>
          <h2 id="q1h" className="h2">Is it accurate?</h2>
        </div>
        <span className="mono-mute">test macro-F1 · mean ± sd · {acc.per_alpha[0].fedavg.n} seeds</span>
      </div>
      <div className="grid-line">
        {acc.per_alpha.map((p) => (
          <div key={p.alpha} className="cell">
            <span className="eyebrow"><span className="keep">α = {p.alpha}</span></span>
            <div className="bar-row text-body"><span>FedAvg</span><span className="num">{meanSd(p.fedavg.mean, p.fedavg.std)}</span></div>
            <div className="bar-track" role="presentation"><div className="bar-fill" style={{ width: `${p.fedavg.mean * 100}%`, background: 'var(--away)' }} /></div>
            <div className="bar-row" style={{ marginTop: 4 }}><span>FedAvgM β={acc.fedavgm_momentum}</span><span className="num" style={{ fontWeight: 600 }}>{meanSd(p.fedavgm.mean, p.fedavgm.std, 4)}</span></div>
            <div className="bar-track" role="presentation"><div className="bar-fill" style={{ width: `${p.fedavgm.mean * 100}%`, background: 'var(--ok)' }} /></div>
          </div>
        ))}
      </div>
      <p className="small">
        Without federation: centralized MLP <span className="num">{meanSd(c.mean, c.std, 4)}</span> · XGBoost{' '}
        <span className="num">{meanSd(x.mean, x.std, 4)}</span>. FedAvgM: {acc.fedavgm_kind}; chosen on validation from{' '}
        {acc.selection.n_candidates_compared} candidates compared ({acc.selection.n_dropped_by_budget_guard} more dropped by the budget guard).
      </p>
      <Srcs paths={[acc.fedavg_source, acc.fedavgm_source, acc.selection.source, c.source, x.source]} />

      <details className="disc">
        <summary>Per-class F1 <span className="mono-mute">test, mean over seeds</span></summary>
        <div className="scroll-x" tabIndex={0} role="region" aria-label="Per-class F1 table">
          <table className="v-table">
            <thead>
              <tr>
                <th>family</th>
                {acc.per_alpha.map((p) => <th key={`a${p.alpha}`}>FedAvg α={p.alpha}</th>)}
                {acc.per_alpha.map((p) => <th key={`m${p.alpha}`}>FedAvgM α={p.alpha}</th>)}
              </tr>
            </thead>
            <tbody>
              {acc.per_class.map((r) => {
                const only = acc.per_class_only.includes(r.family);
                return (
                  <tr key={r.family}>
                    <td className="txt">
                      {r.family}
                      {only && <span className="mono-mute"> · per class only</span>}
                    </td>
                    {acc.per_alpha.map((p) => <td key={`a${p.alpha}`}>{fixed(r.fedavg[p.alpha].mean)}</td>)}
                    {acc.per_alpha.map((p) => <td key={`m${p.alpha}`}>{fixed(r.fedavgm[p.alpha].mean)}</td>)}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="tiny">
          Headline macro-F1 averages {acc.headline_classes.join(', ')}. {acc.per_class_only.join(' and ')} are reported per class
          only.
        </p>
        <Srcs paths={acc.per_class_sources} />
      </details>

      {federation && (
        <details className="disc">
          <summary>Per-run FedAvg results <span className="mono-mute">{federation.manifest_summaries.length} runs, best-by-validation round</span></summary>
          <div className="scroll-x" tabIndex={0} role="region" aria-label="Per-run results table">
            <table className="v-table">
              <thead>
                <tr><th>run</th><th>best round</th><th>val macro-F1</th><th>test macro-F1</th></tr>
              </thead>
              <tbody>
                {federation.manifest_summaries.map((m) => (
                  <tr key={m.tag}>
                    <td className="txt mono">{m.tag}</td>
                    <td>{m.best_round}</td>
                    <td>{fixed(m.val_macro_f1_headline, 4)}</td>
                    <td>{fixed(m.test_macro_f1_headline, 4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Src path="results/inspection/best_rounds_manifest.json" />
        </details>
      )}
    </section>
  );
}
