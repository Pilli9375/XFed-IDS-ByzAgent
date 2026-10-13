import { useMemo, useState } from 'react';
import Src from '../../components/Src';
import { int } from '../../lib/format';

const SIZES_SRC = 'results/inspection/silo_sizes.csv';

// Folded in from the old Federation Status page. The label-skew heatmap is
// fixed (inventory 5.4): column labels sit above the grid, unrotated, and a
// log colour scale is drawn under it. Cell shade is neutral (ink over the
// surface), so no signal colour is borrowed for it.
export default function DataEligibility({ federation: fed }) {
  const alphas = fed.shape.alphas.map(String);
  const seeds = fed.shape.seeds;
  const [alpha, setAlpha] = useState(alphas[0]);
  const [seed, setSeed] = useState(seeds[0]);
  const families = [...fed.label_vocab.headline_classes, ...fed.label_vocab.below_floor_classes];

  const grid = useMemo(() => {
    const rows = fed.silo_sizes.filter((r) => String(r.alpha) === alpha && r.seed === seed);
    const silos = [...new Set(rows.map((r) => r.silo))].sort((a, b) => a - b);
    const get = (s, f) => rows.find((r) => r.silo === s && r.family === f)?.n ?? 0;
    const max = Math.max(1, ...rows.map((r) => r.n));
    return { silos, get, max };
  }, [fed, alpha, seed]);

  const decades = Math.ceil(Math.log10(grid.max + 1));
  const shade = (n) => (n <= 0 ? 0 : (Math.log10(n + 1) / decades) * 100);
  const ticks = Array.from({ length: decades + 1 }, (_, i) => i);

  const ste = fed.silo_total_eligibility;
  const fe = fed.family_eligibility;
  const excludedSilos = ste.table.filter((r) => r.below_floor);
  const configs = alphas.flatMap((a) => seeds.map((s) => [a, s]));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center' }}>
        <h3 style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>Label skew: flows per org and family</h3>
        <label className="small">
          α{' '}
          <select className="v-select" value={alpha} onChange={(e) => setAlpha(e.target.value)}>
            {alphas.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </label>
        <label className="small">
          seed{' '}
          <select className="v-select" value={seed} onChange={(e) => setSeed(Number(e.target.value))}>
            {seeds.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
      </div>
      <div className="heat-wrap" tabIndex={0} role="region" aria-label="Label-skew heatmap, scrollable">
        <table style={{ borderCollapse: 'separate', borderSpacing: 3, minWidth: 640 }}>
          <caption className="sr-only">Flows per org and family, α={alpha}, seed {seed}</caption>
          <thead>
            <tr>
              <th scope="col" className="mono-mute" style={{ textAlign: 'left', fontWeight: 400 }}>org</th>
              {families.map((f) => (
                <th key={f} scope="col" className="mono-mute" style={{ fontWeight: 400, fontSize: 10.5, padding: '0 2px 4px', textAlign: 'center', whiteSpace: 'nowrap' }}>
                  {f}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {grid.silos.map((s) => (
              <tr key={s}>
                <th scope="row" className="mono-mute" style={{ textAlign: 'left', fontWeight: 400, paddingRight: 6 }}>{s}</th>
                {families.map((f) => {
                  const n = grid.get(s, f);
                  return (
                    <td
                      key={f}
                      title={`org ${s} · ${f}: ${int(n)} flows`}
                      style={{
                        height: 22,
                        minWidth: 64,
                        borderRadius: 3,
                        background: `color-mix(in srgb, var(--ink) ${shade(n)}%, var(--s2))`,
                      }}
                    >
                      <span className="sr-only">{int(n)}</span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ maxWidth: 420 }} aria-label="Colour scale: flows, log scale">
        <div style={{ height: 10, borderRadius: 3, background: 'linear-gradient(90deg, var(--s2), var(--ink))', border: '1px solid var(--line2)' }} />
        <div style={{ display: 'flex', justifyContent: 'space-between' }} className="mono-mute">
          {ticks.map((i) => <span key={i}>{int(10 ** i)}</span>)}
        </div>
        <p className="tiny">flows per cell, log scale · max {int(grid.max)}</p>
      </div>
      <Src path={SIZES_SRC} />

      <div className="tiles" style={{ flex: 'none' }}>
        <div className="tile">
          <p className="small">Org size floor ({int(ste.threshold_flows)} flows)</p>
          <p className="tile-num tile-num--sm">{ste.n_excluded} / {ste.n_total} org-configs below</p>
          <p className="tiny">
            All orgs still train; the floor only gates explanation eligibility.
            {excludedSilos.length > 0 && ` Below: ${excludedSilos.map((r) => `α=${r.alpha} seed ${r.seed} org ${r.silo} (${int(r.total_flows)})`).join('; ')}.`}
          </p>
        </div>
        <div className="tile">
          <p className="small">Family eligibility (≥{fe.threshold_flows} flows in ≥{fe.min_eligible_silos} orgs)</p>
          <p className="tile-num tile-num--sm">{fe.n_excluded} / {fe.n_total} excluded</p>
          <p className="tiny">(family, α, seed) triples left out of agreement</p>
        </div>
      </div>

      <div className="scroll-x" tabIndex={0} role="region" aria-label="Family eligibility table">
        <table className="v-table">
          <caption className="sr-only">Orgs eligible per family and configuration</caption>
          <thead>
            <tr>
              <th>config</th>
              {families.filter((f) => fe.matrix.some((m) => m.family === f)).map((f) => <th key={f}>{f}</th>)}
            </tr>
          </thead>
          <tbody>
            {configs.map(([a, s]) => (
              <tr key={`${a}-${s}`}>
                <td className="txt">α={a} · seed {s}</td>
                {families.filter((f) => fe.matrix.some((m) => m.family === f)).map((f) => {
                  const m = fe.matrix.find((x) => String(x.alpha) === a && x.seed === s && x.family === f);
                  return (
                    <td key={f} className={m && !m.family_included ? 'text-mute' : ''}>
                      {m ? `${m.eligible_silos}${m.family_included ? '' : ' ✗'}` : '—'}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="tiny">Cells: orgs eligible for that family. ✗ = family excluded for that configuration.</p>
      <Src path={SIZES_SRC} />
    </div>
  );
}
