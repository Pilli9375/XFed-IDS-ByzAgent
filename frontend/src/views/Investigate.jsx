import { useEffect, useState } from 'react';
import {
  getAccuracy,
  getAgreement,
  getAgreementSummary,
  getFaithfulness,
  getFederation,
  getFigures,
  getTrust,
} from '../api/client';
import Ambient from '../components/Ambient';
import Header from '../components/Header';
import HotSwapBanner from '../components/HotSwapBanner';
import { useLoadingGate } from '../hooks/useLoadingGate';
import { useResource } from '../hooks/useResource';
import { useTheme } from '../hooks/useTheme';
import { buildCleanVsAttackRows } from '../lib/trust';
import { conditionLabel, orgTone } from '../lib/trust2';
import AccuracyQ from './inv/AccuracyQ';
import AgreementQ from './inv/AgreementQ';
import EfficiencyQ from './inv/EfficiencyQ';
import TrustQ from './inv/TrustQ';

const TOC = [
  ['03', 'Is anyone poisoning it?', 'q3'],
  ['01', 'Is it accurate?', 'q1'],
  ['02', 'Do the orgs agree on why?', 'q2'],
  ['04', 'What does it cost?', 'q4'],
];
const SKELETON_GLOWS = ['attack', 'ok', 'agent', 'ok'];

export default function Investigate({ hs }) {
  const { epoch } = useTheme();
  const trust = useResource('trust', getTrust);
  const accuracy = useResource('accuracy', getAccuracy);
  const agreement = useResource('agreement', getAgreement);
  const summary = useResource('agreement-summary', getAgreementSummary);
  const faith = useResource('faithfulness', getFaithfulness);
  const figures = useResource('figures', getFigures);
  const federation = useResource('federation', getFederation);
  const all = [trust, accuracy, agreement, summary, faith, figures, federation];
  const loading = useLoadingGate(all.every((r) => r.status !== 'loading'), epoch);
  const failed = all.some((r) => r.status === 'error');

  const [condIdx, setCondIdx] = useState(0);
  const [org, setOrg] = useState(null);
  const [active, setActive] = useState('q3');

  const cond = trust.data?.conditions[condIdx];
  const rows = cond ? buildCleanVsAttackRows(cond.clean.per_silo, cond.attack.per_silo, cond.true_malicious_silos) : [];
  // Until an org is picked, show the condition's poisoned org with the
  // largest lift (attack-run flag rate minus clean-run flag rate).
  const topPoisoned = rows.filter((r) => r.malicious).sort((a, b) => b.lift - a.lift)[0];
  const orgId = org ?? topPoisoned?.silo ?? rows[0]?.silo ?? 0;
  const selRow = rows.find((r) => r.silo === orgId);
  const tone = selRow ? orgTone(selRow) : 'ok';

  useEffect(() => {
    if (loading) return undefined;
    const els = TOC.map(([, , id]) => document.getElementById(id)).filter(Boolean);
    const io = new IntersectionObserver(
      (entries) => {
        const vis = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (vis[0]) setActive(vis[0].target.id);
      },
      { rootMargin: '-80px 0px -55% 0px' },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [loading]);

  return (
    <div className={`v-page v-page--investigate${loading ? ' is-loading' : ''}`}>
      <Ambient tone={tone} bFactor={0.4} loading={loading} />
      <div className="v-layer">
        <Header>{cond && <span className="mono-mute">{conditionLabel(cond)}</span>}</Header>
        <HotSwapBanner hs={hs} />
        <div className="inv-wrap">
          <aside className="inv-aside">
            <nav aria-label="Questions" className="inv-toc">
              {TOC.map(([n, label, id]) => (
                <a key={id} href={`#${id}`} aria-current={active === id ? 'true' : undefined}>
                  <span className="n">{n}</span>
                  {label}
                </a>
              ))}
            </nav>
          </aside>
          <main id="main" className="inv-main">
            <h1 className="sr-only">Investigate</h1>
            {loading ? (
              <div aria-busy="true" aria-label="Loading results" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                {SKELETON_GLOWS.map((g, k) => (
                  <div key={k} className={`bloom g-${g}`} style={{ padding: '22px 24px', gap: 16, animationDelay: `${k * 0.25}s` }}>
                    <div className="shim" style={{ height: 22, width: '32%' }} />
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0,1fr))', gap: 12 }}>
                      <div className="shim" style={{ height: 84 }} />
                      <div className="shim" style={{ height: 84 }} />
                      <div className="shim" style={{ height: 84 }} />
                    </div>
                    <div className="shim" style={{ height: 12, width: '70%' }} />
                  </div>
                ))}
                <p className="foot" role="status">Reading results files…</p>
              </div>
            ) : failed ? (
              <div className="q" role="alert">
                <p className="note text-attack">
                  Could not load{' '}
                  {['/trust', '/accuracy', '/agreement', '/agreement/summary', '/faithfulness', '/figures', '/federation']
                    .filter((_, i) => all[i].status === 'error')
                    .join(', ')}
                  . Is the backend running?
                </p>
              </div>
            ) : (
              <div className="v-fade" style={{ gap: 20 }}>
                <TrustQ
                  trust={trust.data}
                  condIdx={condIdx}
                  onCond={(i) => {
                    setCondIdx(i);
                    setOrg(null);
                  }}
                  org={orgId}
                  onOrg={setOrg}
                />
                <AccuracyQ acc={accuracy.data} federation={federation.data} />
                <AgreementQ agreement={agreement.data} summary={summary.data} faith={faith.data} federation={federation.data} />
                <EfficiencyQ f={figures.data} />
                <p className="foot">
                  Every figure links to the results file it was read from. Explanation check and trust check are separate
                  experiments; their results are not combined.
                </p>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
