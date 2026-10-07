// S6 · Can they be trusted? Poisoned orgs on the network, then the agent's calls round by round
// (seed 1337, clean vs attack), org 5's verbatim reason, and the Multi-Krum stamp (seed 42).
import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, F, STATE } from '../theme';
import { bf, spring, on, seg, TL } from '../motion';
import { useFmt, Fmt } from '../layout';
import { N, RAW, COPY } from '../data';
import { Network } from '../Network';
import { Bg, Col, Title, Body, Tag, sizes, settled } from '../ui';
import { Tx, Arrow, LineUp, monoStyle } from '../Text';

const E = TL.ev.s6;
const S = 68;
const b = (beat: number) => bf(beat) - bf(S);

export const S6Trust: React.FC = () => {
  const f = useCurrentFrame();
  const fmt = useFmt();
  const { width, height } = useVideoConfig();
  const wipe = spring(f, b(E.wipe), 'wipe');
  const st = settled();
  const mal = RAW.mal;
  const orgs = st.orgs.map((o, i) => {
    const k = mal.indexOf(i);
    if (k < 0) return o;
    const t = b(E.poison + k * E.poisonStep);
    const hit = on(f, t);
    return { ...o, fill: hit ? C.blush : C.cream, stroke: hit ? C.terracotta : C.cocoa, scale: 1 + 0.12 * Math.sin(Math.PI * seg(f, t, t + 8)) };
  });
  const labels = st.labels.map((l, i) => {
    const k = mal.indexOf(i);
    const hit = k >= 0 && on(f, b(E.poison + k * E.poisonStep));
    return { ...l, value: hit ? COPY.story.poisoned : undefined, valueColor: C.terracottaText, nameColor: hit ? C.terracottaText : C.muted };
  });
  const caption = `Orgs ${N.mal} are secretly poisoned: ${N.flip} of their attack traffic relabelled as Benign. The agent is never told.`;
  return (
    <AbsoluteFill>
      {wipe < 1 && (
        <>
          <Bg color={C.cream} />
          <Network fmt={fmt} width={width} height={height} orgs={orgs} labels={labels} edge={st.edge} hub={st.hub} />
          <Col fmt={fmt} slot="top">
            <Tag fmt={fmt} style={{ marginBottom: 22 }}>{`α = ${N.byzAlpha} · seed ${N.trustSeed}`}</Tag>
            <Title fmt={fmt}><LineUp p={spring(f, 0, 'type')}>And can they be <em style={{ color: C.terracottaText }}>trusted</em>?</LineUp></Title>
            {fmt === 'wide' && <Body fmt={fmt} show={on(f, b(E.poison))} style={{ marginTop: 30 }}>{caption}</Body>}
          </Col>
          {fmt === 'tall' && <Col fmt={fmt} slot="bottom"><Body fmt={fmt} show={on(f, b(E.poison))}>{caption}</Body></Col>}
        </>
      )}
      {wipe > 0 && (
        <AbsoluteFill style={{ background: C.cocoa, transform: `translateY(${(1 - wipe) * 100}%)` }}>
          <Grid f={f} fmt={fmt} />
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ the grid
const Grid: React.FC<{ f: number; fmt: Fmt }> = ({ f, fmt }) => {
  const wide = fmt === 'wide';
  const s = sizes(fmt);
  const nR = RAW.nRounds;
  const cell = wide ? 27 : 28;
  const pitch = wide ? 32 : 33;
  const rowP = wide ? 34 : 32;
  const labW = wide ? 130 : 112;
  const gx = wide ? 115 : 64;
  const gridW = (nR - 1) * pitch + cell;
  // wide: grids side by side; tall: stacked
  const A = wide ? { x: gx + labW, y: 175 } : { x: gx + labW, y: 340 };
  const B = wide ? { x: A.x + gridW + 40, y: 175 } : { x: gx + labW, y: 820 };
  const fs = RAW.featSilo;
  const fr = RAW.featRound;
  const mal = RAW.mal;
  const focus = f >= b(E.org5);
  const org0On = f >= b(E.org0);
  const rowOpacity = (s0: number) => (!focus ? 1 : s0 === fs || (org0On && s0 === 0) ? 1 : 0.32);
  const colOn = (r: number) => f >= b(E.fill + r * E.fillStep);
  const ring = spring(f, b(E.detail), 'ui');
  const typeStart = b(E.type);
  const reason = N.featReason;
  const nChars = Math.floor(reason.length * seg(f, typeStart, typeStart + bf(E.typeBeats)));
  const tc = COPY.trust;
  const legend = [tc.legend.trust, tc.legend.downweight, tc.legend.quarantine];

  const grid = (g: number[][], o: { x: number; y: number }, attack: boolean) => (
    <>
      {g.map((row, s0) => row.map((v, r) => {
        const x = o.x + r * pitch; const y = o.y + s0 * rowP;
        const t = b(E.fill + r * E.fillStep);
        const p = colOn(r) ? spring(f, t, 'snap') : 0;
        return (
          <div key={`${s0}-${r}`} style={{
            position: 'absolute', left: x, top: y, width: cell, height: cell, borderRadius: 3,
            background: p > 0 ? STATE[v] : C.darkWell, opacity: rowOpacity(s0),
            transform: `scale(${p > 0 ? 0.55 + 0.45 * p : 1})`,
          }} />
        );
      }))}
      {attack && ring > 0 && (
        <div style={{
          position: 'absolute', left: o.x + (fr - 1) * pitch - 5, top: o.y + fs * rowP - 5, width: cell + 10, height: cell + 10,
          borderRadius: 6, border: `3px solid ${C.cream}`, transform: `scale(${0.6 + 0.4 * ring})`,
        }} />
      )}
      {/* round axis */}
      {[1, 10, nR].map((r) => (
        <div key={r} style={{ position: 'absolute', left: o.x + (r - 1) * pitch - 20, width: cell + 40, textAlign: 'center', top: o.y + 10 * rowP + 4, ...monoStyle(wide ? 24 : 26, C.darkMuted) }}>{r}</div>
      ))}
    </>
  );
  const rowLabels = (o: { x: number; y: number }) => Array.from({ length: RAW.nSilos }, (_, s0) => {
    const bad = mal.includes(s0);
    return (
      <div key={s0} style={{
        position: 'absolute', left: gx, top: o.y + s0 * rowP - 2, height: cell + 4, display: 'flex', alignItems: 'center',
        paddingLeft: 12, borderLeft: `3px solid ${bad ? C.terracottaLight : 'transparent'}`, opacity: rowOpacity(s0),
        ...monoStyle(wide ? 28 : 30, bad ? C.cream : C.darkMuted),
      }}>{COPY.story.org(s0)}</div>
    );
  });
  const flag = (silo: number, a: string, bb: string, show: boolean) => show && (
    <span style={{ ...monoStyle(wide ? 30 : 34, C.terracottaLight) }}>{a}<Arrow />{bb}</span>
  );

  const head = (text: string, o: { x: number; y: number }) => (
    <div style={{ position: 'absolute', left: o.x, top: o.y - (wide ? 48 : 50), ...monoStyle(s.tag, C.darkMuted), letterSpacing: '0.06em' }}>{text}</div>
  );
  const sumStyle: React.CSSProperties = { position: 'absolute', width: wide ? gridW : 952, ...monoStyle(wide ? 28 : 30, C.darkText), lineHeight: 1.3 };

  // detail panel + stamp geometry
  const panel = wide ? { x: gx, y: 655, w: 1040 } : { x: gx, y: 1232, w: 952 };
  const showDetail = f >= b(E.detail);
  const stamp = spring(f, b(E.stamp), 'snap');

  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: gx, top: wide ? 62 : 160 }}>
        {wide
          ? <Tag fmt={fmt} color={C.brass}>{`EVERY CALL THE AGENT MADE · SEED ${N.trustSeed} · α = ${N.byzAlpha}`}</Tag>
          : <><Tag fmt={fmt} color={C.brass}>EVERY CALL THE AGENT MADE</Tag><Tag fmt={fmt} color={C.brass} style={{ marginTop: 4 }}>{`SEED ${N.trustSeed} · α = ${N.byzAlpha}`}</Tag></>}
      </div>
      {head(tc.colClean, A)}
      {head(tc.colAttack(Number(N.attackF), Number(N.nSilos)), B)}
      {rowLabels(A)}
      {!wide && rowLabels(B)}
      {grid(RAW.gA, A, false)}
      {grid(RAW.gB, B, true)}

      {/* flag-rate column (wide) */}
      {wide && (
        <>
          <div style={{ position: 'absolute', left: B.x + gridW + 26, top: A.y - 48, ...monoStyle(24, C.darkMuted), opacity: on(f, b(E.org5)) }}>FLAG RATE</div>
          <div style={{ position: 'absolute', left: B.x + gridW + 26, top: B.y + fs * rowP - 4 }}>{flag(fs, N.org5RateA, N.org5RateB, focus)}</div>
          <div style={{ position: 'absolute', left: B.x + gridW + 26, top: B.y - 4 }}>{flag(0, N.org0RateA, N.org0RateB, org0On)}</div>
        </>
      )}

      {/* summaries (site copy) */}
      <div style={{ ...sumStyle, left: wide ? A.x : gx, top: A.y + 10 * rowP + (wide ? 40 : 38), opacity: on(f, b(E.summary)) }}>{N.sumClean}</div>
      <div style={{ ...sumStyle, left: wide ? B.x : gx, top: B.y + 10 * rowP + (wide ? 40 : 38), opacity: on(f, b(E.summary)) }}>{N.sumAttack}</div>

      {/* before the detail opens: caption + legend */}
      {!showDetail && (
        <div style={{ position: 'absolute', left: panel.x, top: panel.y + (wide ? 20 : 30), width: wide ? 1690 : 952, opacity: on(f, b(E.cap1)) }}>
          <Body fmt={fmt} color={C.darkText}>{`Left, nobody is attacking. Right, orgs ${N.mal} are poisoned.`}</Body>
          {!wide && <div style={{ height: 0 }} />}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px 30px', marginTop: 26, ...monoStyle(wide ? 28 : 30, C.darkMuted) }}>
            {legend.map((t: string, k: number) => (
              <span key={t} style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}><i style={{ width: 24, height: 24, borderRadius: 3, background: STATE[k] }} />{t}</span>
            ))}
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}><i style={{ width: 4, height: 26, background: C.terracottaLight }} />{tc.legend.poisoned}</span>
          </div>
        </div>
      )}

      {/* org 5, round 6: the agent's call */}
      {showDetail && (
        <div style={{
          position: 'absolute', left: panel.x, top: panel.y, width: panel.w, background: C.cocoa2, border: `1px solid ${C.darkLine}`,
          borderRadius: 14, padding: wide ? '24px 30px' : '28px 30px',
        }}>
          <div style={monoStyle(wide ? 28 : 30, C.darkMuted)}>{tc.detailHead(N.trustSeed, 'b', N.featSilo, N.featRound)}</div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 26, flexWrap: 'wrap', marginTop: 6 }}>
            <span style={{ fontFamily: F.disp, fontSize: wide ? 56 : 64, color: C.brass, lineHeight: 1.1 }}>{N.featDecision}</span>
            <span style={monoStyle(wide ? 24 : 26, C.darkMuted)}>{tc.reasonLabel}</span>
          </div>
          <p style={{ margin: '10px 0 0', fontFamily: F.body, fontSize: wide ? 32 : 34, lineHeight: 1.4, color: C.cream, overflowWrap: 'anywhere', minHeight: wide ? 135 : 190 }}>
            {reason.slice(0, nChars)}
          </p>
          <p style={{ margin: '12px 0 0', fontFamily: F.body, fontSize: wide ? 26 : 30, lineHeight: 1.4, color: C.darkMuted, opacity: on(f, b(E.fidelity)) }}>
            {`Reasons shown as written; about ${N.trendLo}–${N.trendHi}% of the agent’s trend claims contradicted the numbers it was given.`}
          </p>
          {!wide && (
            <div style={{ marginTop: 14, ...monoStyle(30, C.darkText) }}>
              <span style={{ opacity: focus ? 1 : 0 }}>{`Org ${N.featSilo} flag rate `}{flag(fs, N.org5RateA, N.org5RateB, true)}</span>
            </div>
          )}
        </div>
      )}

      {/* org 0 note */}
      {wide && (
        <div style={{ position: 'absolute', left: 1215, top: 640, width: 590, opacity: on(f, b(E.org0)) }}>
          <Body fmt={fmt} color={C.darkText}>{`Org 0 barely moves.`}</Body>
        </div>
      )}

      {/* the stamp (baselines.json, seed 42) */}
      {stamp > 0 && (
        <div style={{
          position: 'absolute', ...(wide ? { left: 1215, top: 712, width: 580 } : { left: 120, top: 370, width: 840 }),
          background: C.cocoa, border: `5px solid ${C.terracottaLight}`, borderRadius: 16, padding: wide ? '14px 24px 16px' : '22px 30px 24px',
          transform: `rotate(-3deg) scale(${1.25 - 0.25 * stamp})`, opacity: stamp > 0.02 ? 1 : 0,
        }}>
          <div style={{ fontFamily: F.disp, fontSize: wide ? 42 : 52, color: C.terracottaLight, lineHeight: 1.05 }}>Multi-Krum excluded</div>
          <div style={{ ...monoStyle(wide ? 100 : 150, C.terracottaLight), fontWeight: 300, lineHeight: 1 }}>{N.mkExcl}</div>
          <div style={{ fontFamily: F.body, fontSize: wide ? 28 : 32, color: C.darkText, lineHeight: 1.3, marginTop: 6 }}>of poisoned orgs, though it was given the true attacker count</div>
          <div style={{ ...monoStyle(wide ? 28 : 32, C.darkMuted), marginTop: 6 }}><Tx>{`seed ${N.mkSeed} · α = ${N.mkAlpha}`}</Tx></div>
        </div>
      )}
    </AbsoluteFill>
  );
};
