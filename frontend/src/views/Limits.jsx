import { Fragment } from 'react';
import { getFederation, getLimits } from '../api/client';
import Ambient from '../components/Ambient';
import Header from '../components/Header';
import HotSwapBanner from '../components/HotSwapBanner';
import Src from '../components/Src';
import { useLoadingGate } from '../hooks/useLoadingGate';
import { useResource } from '../hooks/useResource';
import { useTheme } from '../hooks/useTheme';

// Methods & Limits, re-styled. The text is not retyped here: GET /limits
// serves PROJECT_INSTRUCTIONS.md's "Findings that limit what can be
// claimed" section and test-set paragraphs as written, plus two verbatim
// engineering excerpts, so wording and numbers always match the file.
export default function Limits({ hs }) {
  const { epoch } = useTheme();
  const limits = useResource('limits', getLimits);
  const federation = useResource('federation', getFederation);
  const loading = useLoadingGate(limits.status !== 'loading' && federation.status !== 'loading', epoch);
  const L = limits.data;
  const fed = federation.data;

  return (
    <div className={`v-page v-page--limits${loading ? ' is-loading' : ''}`}>
      <Ambient tone="agent" bFactor={0.4} loading={loading} strength={0.6} />
      <div className="v-layer">
        <Header />
        <HotSwapBanner hs={hs} />
        <main id="main" className="v-main" style={{ maxWidth: 1100 }}>
          <div>
            <span className="eyebrow">Disclosure</span>
            <h1 className="h2" style={{ fontSize: 28 }}>Methods &amp; limits</h1>
            <p className="small" style={{ maxWidth: 720, marginTop: 8 }}>
              What the results can and cannot support, stated up front. The explanation check and the trust check are separate
              experiments, each with its own evidence.
            </p>
          </div>
          {loading ? (
            <div aria-busy="true" aria-label="Loading limits" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              {['ok', 'agent', 'attack'].map((g, k) => (
                <div key={g} className={`bloom g-${g}`} style={{ animationDelay: `${k * 0.25}s` }}>
                  <div className="shim" style={{ height: 18, width: '30%' }} />
                  {[90, 76, 84, 62].map((w) => <div key={w} className="shim" style={{ height: 12, width: `${w}%` }} />)}
                </div>
              ))}
              <p className="foot" role="status">Reading PROJECT_INSTRUCTIONS.md…</p>
            </div>
          ) : limits.status === 'error' ? (
            <div className="q" role="alert"><p className="note text-attack">Could not load GET /limits. Is the backend running?</p></div>
          ) : (
            <div className="v-fade">
              {fed && (
                <section className="q" aria-labelledby="setup-h">
                  <h2 id="setup-h" style={{ margin: 0, fontSize: 16 }}>Setup</h2>
                  <div className="grid-line">
                    <div className="cell"><span className="eyebrow">Organizations</span><span className="num" style={{ fontSize: 24 }}>{fed.shape.n_silos}</span><span className="small">each trains on its own traffic; none is shared</span></div>
                    <div className="cell"><span className="eyebrow">Label skew</span><span className="num" style={{ fontSize: 18 }}>α ∈ {'{'}{fed.shape.alphas.join(', ')}{'}'}</span><span className="small">Dirichlet partition, lower is more skewed</span></div>
                    <div className="cell"><span className="eyebrow">Seeds</span><span className="num" style={{ fontSize: 18 }}>{fed.shape.seeds.join(', ')}</span><span className="small">every configuration runs once per seed</span></div>
                    <div className="cell"><span className="eyebrow">Families</span><span className="num" style={{ fontSize: 24 }}>{fed.label_vocab.headline_classes.length}<span className="kpi-unit">+ {fed.label_vocab.below_floor_classes.length} per class only</span></span><span className="small">{fed.label_vocab.below_floor_classes.join(', ')} reported per class only</span></div>
                  </div>
                  <span className="src-list"><Src path="configs/data.yaml" /><Src path="results/inspection/best_rounds_manifest.json" /></span>
                </section>
              )}
              {L.claims.groups.map((g) => (
                <section key={g.title} className="q" aria-labelledby={`lim-${g.title}`}>
                  <div className="q-head">
                    <h2 id={`lim-${g.title}`} style={{ margin: 0, fontSize: 16 }}>{g.title}</h2>
                    <Src path={L.claims.source} label={`${L.claims.source} · ${L.claims.title}`} />
                  </div>
                  <ul className="lim-list">
                    {g.items.map((it, i) => <li key={i}><Md text={it} /></li>)}
                  </ul>
                </section>
              ))}
              <section className="q" aria-labelledby="lim-test">
                <div className="q-head">
                  <h2 id="lim-test" style={{ margin: 0, fontSize: 16 }}>Test-set use</h2>
                  <Src path={L.test_set.source} />
                </div>
                {L.test_set.paragraphs.map((p, i) => <p key={i} className="small" style={{ maxWidth: 900, fontSize: 13.5 }}><Md text={p} /></p>)}
              </section>
              <section className="q" aria-labelledby="lim-eng">
                <h2 id="lim-eng" style={{ margin: 0, fontSize: 16 }}>Engineering notes</h2>
                {L.excerpts.map((e) => (
                  <div key={e.title} className="rationale">
                    <span className="eyebrow">{e.title}</span>
                    <p className="text-body"><Md text={e.text} /></p>
                    <Src path={e.source} />
                  </div>
                ))}
              </section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

// **bold** and `code` only: the subset the source file uses.
function Md({ text }) {
  const parts = text.split(/(\*\*.+?\*\*|`[^`]+`)/g);
  return parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) return <b key={i}><Md text={p.slice(2, -2)} /></b>;
    if (p.startsWith('`') && p.endsWith('`')) return <code key={i}>{p.slice(1, -1)}</code>;
    return <Fragment key={i}>{p}</Fragment>;
  });
}
