// S5 · Do they agree on why? Per-org Jaccard@10 on the seed-1337 network, then the α chart
// against the centralized-seed floor (all seeds). Numbers only from N (src/numbers.js).
import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, F } from '../theme';
import { bf, spring, on, TL } from '../motion';
import { useFmt, Fmt } from '../layout';
import { N, RAW, COPY } from '../data';
import { Network } from '../Network';
import { Bg, Col, Title, Body, Note, Tag, sizes, settled } from '../ui';
import { Tx, LineUp, monoStyle } from '../Text';

const E = TL.ev.s5;
const S = 48;
const b = (beat: number) => bf(beat) - bf(S);

export const Question: React.FC<{ fmt: Fmt; p: number }> = ({ fmt, p }) => (
  <Title fmt={fmt}><LineUp p={p}>Do they agree on <em style={{ color: C.plum, fontStyle: 'italic' }}>why</em>?</LineUp></Title>
);

const DEF = 'Each number is how much an organization’s own model shares the shared model’s top-10 reasons (Jaccard@10, where 1 means identical).';

export const S5Agree: React.FC = () => {
  const f = useCurrentFrame();
  const fmt = useFmt();
  const { width, height } = useVideoConfig();
  if (f >= b(E.chart)) return <AlphaChart f={f} fmt={fmt} />;

  const st = settled();
  const drop = spring(f, b(E.drop), 'ui');
  const low = (i: number) => RAW.lows.includes(i);
  const orgs = st.orgs.map((o, i) => ({ ...o, dy: low(i) ? 18 * drop : 0 }));
  const labels = st.labels.map((l, i) => ({
    ...l,
    value: on(f, b(E.values + i * E.valueStep)) ? N[`jac${i}`] : undefined,
    valueColor: low(i) && drop > 0.01 ? C.terracottaText : C.plum,
  }));
  const caption = `Orgs ${RAW.lows.join(' and ')}, with little or no Benign traffic, share only ${N.jacLow}. The middle org sits at ${N.jacMedian}.`;
  const showCap = on(f, b(E.drop));
  return (
    <AbsoluteFill>
      <Bg color={C.cream} />
      <Network fmt={fmt} width={width} height={height} orgs={orgs} labels={labels} edge={st.edge} hub={st.hub} />
      <Col fmt={fmt} slot="top">
        <Tag fmt={fmt} style={{ marginBottom: 22 }}>{`Jaccard@10 per org · α = ${N.storyAlpha} · seed ${N.storySeed}`}</Tag>
        <Question fmt={fmt} p={spring(f, 0, 'type')} />
        {fmt === 'wide' && (
          <>
            <Body fmt={fmt} show={on(f, b(E.def))} style={{ marginTop: 30 }}>{DEF}</Body>
            <Body fmt={fmt} show={showCap} color={C.cocoa} style={{ marginTop: 26 }}>{caption}</Body>
          </>
        )}
      </Col>
      {fmt === 'tall' && (
        <Col fmt={fmt} slot="bottom">
          {showCap ? <Body fmt={fmt} color={C.cocoa}>{caption}</Body> : <Body fmt={fmt} show={on(f, b(E.def))}>{DEF}</Body>}
        </Col>
      )}
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ α chart
const ROWS = [
  { a: '5.0', at: E.bar5 },
  { a: '0.5', at: E.bar05 },
  { a: '0.1', at: E.bar01 },
];

const AlphaChart: React.FC<{ f: number; fmt: Fmt }> = ({ f, fmt }) => {
  const wide = fmt === 'wide';
  const s = sizes(fmt);
  const x0 = wide ? 115 : 64;
  const W = wide ? 1480 : 790;
  const X = (v: number) => x0 + v * W;
  const ys = wide ? [480, 650, 820] : [760, 980, 1200];
  const th = wide ? 24 : 26;
  const top = ys[0] - (wide ? 90 : 100);
  const bottom = ys[2] + (wide ? 40 : 46);
  const [flo, fhi] = RAW.floor;
  const [clo, chi] = RAW.ci;
  const t0 = b(E.chart);
  const band = spring(f, t0, 'type');
  const ci = spring(f, b(E.ci), 'type');
  const labels = COPY.explain.alphas as { key: string; label: string }[];
  const noteX = wide ? 1060 : 64;
  const noteY = wide ? 900 : 1300;
  return (
    <AbsoluteFill>
      <Bg color={C.cream} />
      <Col fmt={fmt} slot="top" style={{ width: wide ? 1200 : undefined }} top={wide ? 90 : undefined}>
        <Tag fmt={fmt} style={{ marginBottom: 22 }}>{`median Jaccard@10 · seeds ${N.agreeSeeds}`}</Tag>
        <Question fmt={fmt} p={1} />
      </Col>

      {/* floor band label */}
      <div style={{ position: 'absolute', left: X((flo + fhi) / 2) - 400, width: 800, top: top - (wide ? 96 : 150), textAlign: 'center', opacity: on(f, t0) }}>
        <div style={monoStyle(s.tag, C.terracottaText)}>{`seed-noise floor ${N.floorLo}–${N.floorHi}`}</div>
        <div style={{ fontFamily: F.body, fontSize: s.tag, color: C.muted, marginTop: 4 }}>centralized models that differ only by seed</div>
      </div>

      <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0 }}>
        {/* tracks */}
        {ys.map((y) => <rect key={y} x={x0} y={y - th / 2} width={W} height={th} rx={th / 2} fill={C.line} />)}
        {/* floor band (site .agree-floor) */}
        <g opacity={band}>
          <rect x={X(flo)} y={top} width={X(fhi) - X(flo)} height={(bottom - top) * band} fill="rgba(168,95,63,.20)" />
          <line x1={X(flo)} x2={X(flo)} y1={top} y2={top + (bottom - top) * band} stroke={C.terracotta} strokeWidth={2} strokeDasharray="6 6" />
          <line x1={X(fhi)} x2={X(fhi)} y1={top} y2={top + (bottom - top) * band} stroke={C.terracotta} strokeWidth={2} strokeDasharray="6 6" />
        </g>
        {/* bars */}
        {ROWS.map((r, k) => {
          const p = spring(f, b(r.at), 'type');
          return <rect key={r.a} x={x0} y={ys[k] - th / 2} width={Math.max(0, RAW.agree[r.a] * W * p)} height={th} rx={th / 2} fill={C.plum} />;
        })}
        {/* chance tick */}
        {on(f, b(E.chance)) > 0 && ys.map((y) => <line key={`c${y}`} x1={X(RAW.chance)} x2={X(RAW.chance)} y1={y - th} y2={y + th} stroke={C.cocoa} strokeWidth={2.5} strokeDasharray="4 4" />)}
        {/* 95% interval at α 0.1 */}
        {ci > 0 && (() => {
          const y = ys[2];
          const xa = X(clo); const xb = X(clo + (chi - clo) * ci);
          return (
            <g stroke={C.cocoa} strokeWidth={3}>
              <line x1={xa} x2={xb} y1={y} y2={y} />
              <line x1={xa} x2={xa} y1={y - 18} y2={y + 18} />
              {ci > 0.98 && <line x1={X(chi)} x2={X(chi)} y1={y - 18} y2={y + 18} />}
            </g>
          );
        })()}
        {/* hand rule from the note to the overlap */}
        {wide && on(f, b(E.ci)) > 0 && (
          <path d={wide
            ? `M ${noteX - 18} ${noteY + 30} C ${noteX - 140} ${noteY + 20}, ${X(chi) + 60} ${ys[2] + 90}, ${X(chi) + 6} ${ys[2] + 24}`
            : `M ${noteX + 300} ${noteY - 14} C ${noteX + 320} ${noteY - 80}, ${X(chi) + 80} ${ys[2] + 90}, ${X(chi) + 6} ${ys[2] + 26}`}
            fill="none" stroke={C.inkSoft} strokeWidth={2} strokeLinecap="round" opacity={spring(f, b(E.ci), 'type')}
            strokeDasharray={600} strokeDashoffset={600 * (1 - spring(f, b(E.ci) + 3, 'type'))} />
        )}
      </svg>

      {/* row labels and values */}
      {ROWS.map((r, k) => {
        const lab = labels.find((x) => x.key === r.a)!.label;
        const shown = spring(f, b(r.at), 'type') > 0.97;
        return (
          <React.Fragment key={r.a}>
            <div style={{ position: 'absolute', left: x0, top: ys[k] - (wide ? 62 : 70), ...monoStyle(s.tag + 2, C.inkSoft) }}><Tx>{lab}</Tx></div>
            <div style={{ position: 'absolute', left: x0 + W + (wide ? 28 : 20), top: ys[k] - (wide ? 30 : 30), ...monoStyle(wide ? 46 : 44, C.plum), opacity: shown ? 1 : 0 }}>{N[`agree_${r.a}`]}</div>
          </React.Fragment>
        );
      })}
      <div style={{ position: 'absolute', left: X(RAW.chance) - 12, top: wide ? bottom + 14 : top - 44, ...monoStyle(s.tag, C.muted), opacity: on(f, b(E.chance)) }}>{`chance ${N.chance}`}</div>
      <div style={{ position: 'absolute', ...(wide ? { left: X(fhi) + 30, top: ys[2] - 60 } : { left: x0, top: ys[2] + 34 }), ...monoStyle(s.tag, C.cocoa), opacity: on(f, b(E.ci)) }}>{`95% interval ${N.ciLo}–${N.ciHi}`}</div>
      <div style={{ position: 'absolute', left: noteX, top: noteY, width: wide ? 760 : 952, opacity: on(f, b(E.ci)) }}>
        <Note fmt={fmt} color={C.inkSoft} style={{ fontSize: s.note + 4 }}><Tx>{`directional, not significant at α = ${N.ciAlpha}`}</Tx></Note>
      </div>
    </AbsoluteFill>
  );
};
