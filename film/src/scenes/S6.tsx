// S6 · Can they be trusted? Poisoned orgs on the network, then the agent's calls round by round
// (seed 1337, clean vs attack), org 5's verbatim reason, and the Multi-Krum stamp (seed 42).
import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, F, STATE } from '../theme';
import { bf, spring, on, seg, camera, TL } from '../motion';
import { useFmt, Fmt } from '../layout';
import { N, RAW, COPY } from '../data';
import { Network } from '../Network';
import { Bg, Col, Title, Body, Tag, sizes, settled } from '../ui';
import { Tx, Arrow, LineUp, monoStyle } from '../Text';
import { focus } from './S1to4';

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
  const F_ = focus(fmt);
  const cam = camera(f, S, [
    { beat: 68, s: 1.02, ...F_.hub },
    { beat: 69.5, s: 1.06, ...F_.toward(0, 0.25) },
    { beat: 71, s: 1.06, ...F_.toward(5, 0.25) },
  ]);
  const caption = `Orgs ${N.mal} are secretly poisoned: ${N.flip} of their attack traffic relabelled as Benign. The agent is never told.`;
  return (
    <AbsoluteFill>
      {wipe < 1 && (
        <>
          <Bg color={C.cream} />
          <Network fmt={fmt} width={width} height={height} orgs={orgs} labels={labels} edge={st.edge} hub={st.hub} camera={cam} />
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
  // wide: both grids side by side across ~84% of the frame; tall: stacked
  const cell = 32;
  const pitch = 37;
  const rowP = wide ? 37 : 36;
  const labW = 110;
  const gx = wide ? 115 : 64;
  const gridW = (nR - 1) * pitch + cell;
  const A = wide ? { x: gx + labW, y: 140 } : { x: gx + labW, y: 326 };
  const B = wide ? { x: A.x + gridW + 40, y: 140 } : { x: gx + labW, y: 846 };
  const below = wide ? 620 : 1300; // caption / legend / detail panel top
  const fs = RAW.featSilo;
  const fr = RAW.featRound;
  const mal = RAW.mal;
  const focusRow = f >= b(E.org5);
  const org0On = f >= b(E.org0);
  const rowOpacity = (s0: number) => (!focusRow ? 1 : s0 === fs || (org0On && s0 === 0) ? 1 : 0.32);
  const ring = spring(f, b(E.detail), 'ui');
  const typeStart = b(E.type);
  const reason = N.featReason;
  const nChars = Math.floor(reason.length * seg(f, typeStart, typeStart + bf(E.typeBeats)));
  const tc = COPY.trust;
  const legend = [tc.legend.trust, tc.legend.downweight, tc.legend.quarantine];
  const rowY = (o: { y: number }, s0: number) => o.y + s0 * rowP;

  // camera: drift while the grid fills, push to org 5's row, then to the call and the stamp
  const Bc = B.x + gridW / 2;
  const cam = wide
    ? camera(f, S, [
      { beat: 72, s: 1.0, fx: 960, fy: 540 },
      { beat: 74, s: 1.012, fx: 900, fy: 420 },
      { beat: 76, s: 1.02, fx: 1000, fy: 380 },
      { beat: 78, s: 1.015, fx: 940, fy: 440 },
      { beat: 80, s: 1.02, fx: 960, fy: 520 },
      { beat: 82, s: 1.04, fx: Bc, fy: rowY(B, fs) },
      { beat: 84, s: 1.03, fx: 620, fy: 760 },
      { beat: 86, s: 1.035, fx: 660, fy: 780 },
      { beat: 88, s: 1.03, fx: 700, fy: 760 },
      { beat: 90, s: 1.035, fx: 1500, fy: 860 },
      { beat: 92, s: 1.04, fx: 1480, fy: 870 },
      { beat: 94, s: 1.035, fx: 1440, fy: 850 },
    ])
    : camera(f, S, [
      { beat: 72, s: 1.0, fx: 540, fy: 800 },
      { beat: 74, s: 1.015, fx: 520, fy: 700 },
      { beat: 76, s: 1.02, fx: 560, fy: 760 },
      { beat: 78, s: 1.015, fx: 540, fy: 820 },
      { beat: 80, s: 1.02, fx: 540, fy: 900 },
      { beat: 82, s: 1.04, fx: 540, fy: rowY(B, fs) },
      { beat: 84, s: 1.02, fx: 540, fy: 1300 },
      { beat: 87, s: 1.025, fx: 520, fy: 1320 },
      { beat: 90, s: 1.03, fx: 540, fy: 500 },
      { beat: 92, s: 1.035, fx: 540, fy: 520 },
    ]);
  const panY = wide ? 0 : -110 * spring(f, b(E.detail), 'slow'); // tall: pan up to make room for the call

  const grid = (g: number[][], o: { x: number; y: number }, attack: boolean) => (
    <>
      {g.map((row, s0) => row.map((v, r) => {
        const t = b(E.fill + r * E.fillStep);
        const p = f >= t ? spring(f, t, 'snap') : 0;
        return (
          <div key={`${s0}-${r}`} style={{
            position: 'absolute', left: o.x + r * pitch, top: rowY(o, s0), width: cell, height: cell, borderRadius: 4,
            background: p > 0 ? STATE[v] : C.darkWell, opacity: rowOpacity(s0),
            transform: `scale(${p > 0 ? 0.55 + 0.45 * p : 1})`,
          }} />
        );
      }))}
      {attack && ring > 0 && (
        <div style={{
          position: 'absolute', left: o.x + (fr - 1) * pitch - 6, top: rowY(o, fs) - 6, width: cell + 12, height: cell + 12,
          borderRadius: 7, border: `3px solid ${C.cream}`, transform: `scale(${0.6 + 0.4 * ring})`,
        }} />
      )}
      {[1, 10, nR].map((r) => (
        <div key={r} style={{ position: 'absolute', left: o.x + (r - 1) * pitch - 24, width: cell + 48, textAlign: 'center', top: rowY(o, 10) + 2, ...monoStyle(wide ? 24 : 30, C.darkMuted) }}>{r}</div>
      ))}
    </>
  );
  const rowLabels = (o: { x: number; y: number }) => Array.from({ length: RAW.nSilos }, (_, s0) => {
    const bad = mal.includes(s0);
    return (
      <div key={s0} style={{
        position: 'absolute', left: gx, top: rowY(o, s0) - 2, height: cell + 4, display: 'flex', alignItems: 'center',
        paddingLeft: 12, borderLeft: `3px solid ${bad ? C.terracottaLight : 'transparent'}`, opacity: rowOpacity(s0),
        ...monoStyle(wide ? 28 : 30, bad ? C.cream : C.darkMuted),
      }}>{COPY.story.org(s0)}</div>
    );
  });
  const flag = (a: string, c: string, size: number) => <span style={{ ...monoStyle(size, C.terracottaLight) }}>{a}<Arrow />{c}</span>;
  const head = (text: string, o: { x: number; y: number }) => (
    <div style={{ position: 'absolute', left: o.x, top: o.y - (wide ? 46 : 48), ...monoStyle(s.tag, C.darkMuted), letterSpacing: '0.06em' }}>{text}</div>
  );
  const sumStyle: React.CSSProperties = { position: 'absolute', ...monoStyle(wide ? 28 : 30, C.darkText), lineHeight: 1.3 };
  const showDetail = f >= b(E.detail);
  const stamp = spring(f, b(E.stamp), 'snap');

  const Stamp = stamp > 0 && (
    <div style={{
      position: 'absolute', ...(wide ? { left: 1185, top: 832, width: 620 } : { left: 120, top: 370, width: 840 }),
      background: C.cocoa, border: `5px solid ${C.terracottaLight}`, borderRadius: 16, padding: wide ? '12px 20px' : '22px 30px 24px',
      transform: `rotate(-3deg) scale(${1.25 - 0.25 * stamp})`, opacity: stamp > 0.02 ? 1 : 0,
      display: 'flex', flexDirection: wide ? 'row' : 'column', alignItems: wide ? 'center' : 'flex-start', gap: wide ? 22 : 0,
    }}>
      {wide && <div style={{ ...monoStyle(104, C.terracottaLight), fontWeight: 300, lineHeight: 1 }}>{N.mkExcl}</div>}
      <div>
        <div style={{ fontFamily: F.disp, fontSize: wide ? 36 : 52, color: C.terracottaLight, lineHeight: 1.05, whiteSpace: 'nowrap' }}>Multi-Krum excluded</div>
        {!wide && <div style={{ ...monoStyle(150, C.terracottaLight), fontWeight: 300, lineHeight: 1 }}>{N.mkExcl}</div>}
        <div style={{ fontFamily: F.body, fontSize: wide ? 24 : 32, color: C.darkText, lineHeight: 1.3, marginTop: 4 }}>of poisoned orgs, though it was given the true attacker count</div>
        <div style={{ ...monoStyle(wide ? 24 : 32, C.darkMuted), marginTop: 4 }}><Tx>{`seed ${N.mkSeed} · α = ${N.mkAlpha}`}</Tx></div>
      </div>
    </div>
  );

  return (
    <AbsoluteFill style={{ transformOrigin: `${cam.fx}px ${cam.fy}px`, transform: `translateY(${panY}px) scale(${cam.scale})` }}>
      <div style={{ position: 'absolute', left: gx, top: wide ? 56 : 160 }}>
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

      {/* summaries (site copy) */}
      <div style={{ ...sumStyle, left: wide ? A.x : gx, top: rowY(A, 10) + (wide ? 36 : 40), opacity: on(f, b(E.summary)) }}>{N.sumClean}</div>
      <div style={{ ...sumStyle, left: wide ? B.x : gx, top: rowY(B, 10) + (wide ? 36 : 40), opacity: on(f, b(E.summary)) }}>{N.sumAttack}</div>

      {/* while the grid fills: caption + legend under it */}
      {!showDetail && (
        <div style={{ position: 'absolute', left: gx, top: below, width: wide ? 1040 : 952, opacity: on(f, b(E.cap1)) }}>
          <Body fmt={fmt} color={C.darkText}>{`Left, nobody is attacking. Right, orgs ${N.mal} are poisoned.`}</Body>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px 30px', marginTop: 22, ...monoStyle(wide ? 28 : 30, C.darkMuted) }}>
            {legend.map((t: string, k: number) => (
              <span key={t} style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}><i style={{ width: 26, height: 26, borderRadius: 4, background: STATE[k] }} />{t}</span>
            ))}
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}><i style={{ width: 4, height: 28, background: C.terracottaLight }} />{tc.legend.poisoned}</span>
          </div>
        </div>
      )}

      {/* org 5, round 6: the agent's call */}
      {showDetail && (
        <div style={{
          position: 'absolute', left: gx, top: below, width: wide ? 1040 : 952, background: C.cocoa2, border: `1px solid ${C.darkLine}`,
          borderRadius: 14, padding: wide ? '22px 30px' : '26px 30px',
        }}>
          <div style={monoStyle(wide ? 28 : 30, C.darkMuted)}>{tc.detailHead(N.trustSeed, 'b', N.featSilo, N.featRound)}</div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 26, flexWrap: 'wrap', marginTop: 6 }}>
            <span style={{ fontFamily: F.disp, fontSize: wide ? 56 : 64, color: C.brass, lineHeight: 1.1 }}>{N.featDecision}</span>
            {!wide && <span style={{ marginLeft: 'auto' }}>{flag(N.org5RateA, N.org5RateB, 32)}</span>}
          </div>
          <div style={{ ...monoStyle(wide ? 24 : 30, C.darkMuted), marginTop: 6 }}>{tc.reasonLabel}</div>
          <p style={{ margin: '8px 0 0', fontFamily: F.body, fontSize: wide ? 32 : 34, lineHeight: 1.4, color: C.cream, overflowWrap: 'anywhere', minHeight: wide ? 90 : 143 }}>
            {reason.slice(0, nChars)}
          </p>
          <p style={{ margin: '12px 0 0', fontFamily: F.body, fontSize: wide ? 26 : 30, lineHeight: 1.4, color: C.darkMuted, opacity: on(f, b(E.fidelity)) }}>
            {`Reasons shown as written; about ${N.trendLo}–${N.trendHi}% of the agent’s trend claims contradicted the numbers it was given.`}
          </p>
        </div>
      )}

      {/* right column (wide): org 5's flag rate, org 0's note */}
      {wide && (
        <div style={{ position: 'absolute', left: 1185, top: below, width: 620 }}>
          <div style={{ opacity: on(f, b(E.org5)) }}>
            <div style={monoStyle(26, C.darkMuted)}>{`ORG ${N.featSilo} · FLAG RATE`}</div>
            <div style={{ marginTop: 2 }}>{flag(N.org5RateA, N.org5RateB, 50)}</div>
            <div style={monoStyle(24, C.darkMuted)}>no attack<Arrow />attack</div>
          </div>
          <div style={{ marginTop: 10, opacity: on(f, b(E.org0)), fontFamily: F.body, fontSize: 28, color: C.darkText }}>
            Org 0 barely moves: {flag(N.org0RateA, N.org0RateB, 28)}
          </div>
        </div>
      )}
      {Stamp}
    </AbsoluteFill>
  );
};
