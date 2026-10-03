import Rule from '../components/Rule';
import SectionHeader from '../components/SectionHeader';
import Subhead from '../components/Subhead';

// Source: PROJECT_INSTRUCTIONS.md, "Findings that limit what can be claimed"
// (not app_lib/sections.py -- sections.py's own Known-limitations block is
// thinner than what this project's claims actually require; see the
// decision note in this file's git history / session report for why
// PROJECT_INSTRUCTIONS.md is the source here instead).
//
// Every <li> below is PROJECT_INSTRUCTIONS.md's bullet, verbatim, translated
// from Markdown (**bold**, `code`) to JSX only -- no rephrasing, no added
// hedging or removed hedging. The silo-size item additionally carries the
// zero-order correlation (r=+0.46, p=0.011 at α=0.1; r=+0.07 at α=5.0) from
// docs/contribution_a_results.md §5, which that document states is the
// canonical, fuller write-up PROJECT_INSTRUCTIONS.md's own bullet compresses
// -- not a competing number, marked as its own sourced addendum below.
//
// Excluded: the Phase 1 Streamlit practical-ceiling note (no longer in
// PROJECT_INSTRUCTIONS.md) -- an engineering note about the old Streamlit app,
// not a measurement or claims limitation. docs/contribution_a_results.md
// excludes this same item from its own Limitations table for the same reason.
export default function MethodsLimits({ eyebrow, title, lede }) {
  return (
    <>
      <SectionHeader eyebrow={eyebrow} title={title} lede={lede} />
      <Rule />

      <Subhead title="Known limitations" />
      <div className="xf-source-note">Source: PROJECT_INSTRUCTIONS.md, "Findings that limit what can be claimed"; CPU-vs-GPU and family-level conflict items: configs/hotswap.yaml, data/README.md</div>

      <ul className="xf-limitations-list">
        <li>
          <b>Round lottery is real</b> — gap up to 0.118 between best-by-validation and
          final-round test numbers. Validation selection is not optional.
        </li>
        <li>
          <b>Bot/WebAttack near-duplication</b> (test-NN ≈ 0.0): the pre-registered
          inflation caveat was tested and <b>not</b> confirmed. State as
          tested-and-not-confirmed. Thin dataset support (Bot=3,527, WebAttack=1,542) is
          the likelier explanation.
        </li>
        <li>
          <b>PortScan is the genuine generalisation family</b> — 23× further test-NN
          distance; bimodal recall (0.9505 / 0.9506 / 0.9995).
        </li>
        <li>
          <b>Below-floor claim at α=0.1 is directional, not significant</b> —
          cluster-bootstrap CIs overlap ([0.250, 0.429] vs floor range [0.429, 0.484]).
          Never state as confirmed.
        </li>
        <li>
          <b>Silo size is a deterministic output of the label draw, not a separate
          cause</b> — under <code>dirichlet_assign()</code>, per-family proportions sum to
          1 over silos by construction, so size and heterogeneity can't be varied
          independently. Conditioning on log(size), KL-from-global still predicts
          agreement (r=−0.57 at α=0.1, −0.82/−0.87 at α=0.5) — heterogeneity's effect
          holds up, size alone doesn't explain it away.
          <div className="xf-source-note" style={{ margin: '0.4rem 0 0 0' }}>
            Addendum, docs/contribution_a_results.md §5 (the canonical write-up this
            bullet compresses): zero-order, silo size correlates with Jaccard@10 at
            α=0.1 (r=+0.46, p=0.011) but not at α=5.0 (r=+0.07) — consistent with size
            carrying signal that is really the label-skew effect. Heterogeneity is{' '}
            <b>not</b> the sole cause of that correlation: the KL-from-global partial
            correlation above is what isolates heterogeneity's own contribution once
            size is conditioned out.
          </div>
        </li>
        <li>
          <b>GradientExplainer, not DeepExplainer</b> — DeepExplainer fails on LayerNorm
          (additivity error 2.43 vs 0.01 tolerance), confirmed by probe not assumption.
        </li>
        <li>
          <b>CPU beats GPU for this SHAP workload</b> — GPU 3× slower, kernel-launch
          overhead dominates on a 19.5k-param model. Measured.
        </li>
        <li>
          <b>Family-level conflict detection</b> over raw-label — the raw-label approach
          silently destroyed 58,307 learnable rows.
        </li>
      </ul>

      <Rule />

      <div className="xf-caption">
        The α=0.1 floor-comparison chart (instability floor vs. federated agreement) lives
        in Explanation Agreement → "Is the α=0.1 agreement drop real, or seed noise?" — not
        duplicated here to avoid rendering the same chart twice in one app.
      </div>
    </>
  );
}
