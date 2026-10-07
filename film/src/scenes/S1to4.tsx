import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, F } from '../theme';
import { bf, spring, on, mix, travel, camera, TL } from '../motion';
import { useFmt, FRAME, geometry, Fmt } from '../layout';
import { N, RAW, COPY } from '../data';
import { Network, Dot, OrgState } from '../Network';
import { Bg, Col, Title, Body, Note, Tag, sizes, settled } from '../ui';
import { Tx, LineUp, monoStyle } from '../Text';

const E = TL.ev;
const at = (chapterStart: number) => (beat: number) => bf(beat) - bf(chapterStart);

/** Camera focus helpers in frame pixels. */
export const focus = (fmt: Fmt) => {
  const g = geometry(fmt);
  const toward = (org: number, k: number) => ({ fx: mix(g.hub.x, g.orgs[org].x, k), fy: mix(g.hub.y, g.orgs[org].y, k) });
  const between = (a: number, c: number, k: number) => ({
    fx: mix(g.hub.x, (g.orgs[a].x + g.orgs[c].x) / 2, k), fy: mix(g.hub.y, (g.orgs[a].y + g.orgs[c].y) / 2, k),
  });
  return { g, hub: { fx: g.hub.x, fy: g.hub.y }, toward, between };
};

// ------------------------------------------------------------------ S1 · hook
// Words slam in on the beat at full-frame scale; on beat 5 the ten organizations burst out from
// behind the last word and fly to their places, the hook type settles into the text column, and
// the hub and edges start drawing before the cut on beat 8.
const HOOK = {
  wide: { size: 184, lines: [[0, 1], [2, 3], [4, 5, 6]], top: 250, endTop: 175, endScale: 0.36, kickerTop: 84 },
  tall: { size: 144, lines: [[0], [1], [2, 3], [4, 5], [6]], top: 585, endTop: 236, endScale: 0.3, kickerTop: 160 },
} as const;

export const S1Hook: React.FC = () => {
  const f = useCurrentFrame();
  const fmt = useFmt();
  const { width, height } = useVideoConfig();
  const b = at(0);
  const fr = FRAME[fmt];
  const H = HOOK[fmt];
  const words = [N.nOrgsWord, 'organizations.', 'One', 'detector.', 'No', 'shared', 'traffic.'];
  const lh = H.size * 1.04;
  const ul = spring(f, b(E.s1.underline), 'type');
  const shrink = spring(f, b(E.s1.burst), 'type');
  const blockTop = mix(H.top, H.endTop, shrink);
  const blockScale = mix(1, H.endScale, shrink);

  // where "traffic." sits before the block moves (Brygada averages ~0.47 em per character)
  const lastLine = H.lines.length - 1;
  const prefix = H.lines[lastLine].slice(0, -1).map((w) => words[w].length + 1).reduce((a, c) => a + c, 0);
  const origin = { x: fr.gx + (prefix + words[6].length / 2) * 0.47 * H.size, y: H.top + (lastLine + 0.55) * lh };

  const g = geometry(fmt);
  const st = settled();
  const orgs: OrgState[] = st.orgs.map((o, i) => {
    const t = b(E.s1.burst + i * E.s1.burstStep);
    if (f < t) return { ...o, scale: 0 };
    const p = spring(f, t, 'ui');
    return { ...o, scale: mix(0.3, 1, p), dx: (origin.x - g.orgs[i].x) * (1 - p), dy: (origin.y - g.orgs[i].y) * (1 - p) };
  });
  const labels = st.labels.map((l, i) => ({ ...l, opacity: on(f, b(E.s1.burst + i * E.s1.burstStep) + 9) }));
  const edge = st.edge.map((_, i) => spring(f, b(E.s1.edges + i * E.s1.edgeStep), 'type'));
  const hub = { ...st.hub, scale: spring(f, b(E.s1.hub), 'ui') };
  const F_ = focus(fmt);
  const cam = camera(f, 0, [
    { beat: 0, s: 1.12, ...F_.hub },
    { beat: 5.5, s: 1.0, ...F_.hub },
    { beat: 7, s: 1.03, ...F_.hub },
  ]);

  const word = (w: number) => {
    const t = b(E.s1.words[w]);
    const slam = spring(f, t, 'slam');
    return (
      // anchored bottom-left so a slamming word only grows into empty space, never over its neighbours
      <span key={w} style={{ display: 'inline-block', opacity: on(f, t), transformOrigin: '0% 100%', transform: `scale(${1 + 0.18 * (1 - slam)})`, marginRight: '0.25em' }}>
        {words[w]}
      </span>
    );
  };
  return (
    <AbsoluteFill>
      <Bg color={C.cream} />
      <Network fmt={fmt} width={width} height={height} orgs={orgs} labels={labels} edge={edge} hub={hub} camera={cam} />
      <div style={{ position: 'absolute', left: fr.gx, top: H.kickerTop, ...monoStyle(fmt === 'wide' ? 28 : 32, C.plum), letterSpacing: '0.06em', opacity: on(f, b(E.s1.kicker)) }}>
        {(COPY.hero.kicker as string).replace(/^●\s*/, '')}
      </div>
      <div style={{ position: 'absolute', left: fr.gx, top: blockTop, transformOrigin: '0 0', transform: `scale(${blockScale})`, width: fr.W - 2 * fr.gx }}>
        {H.lines.map((ln, li) => (
          <div key={li} style={{ fontFamily: F.disp, fontSize: H.size, lineHeight: 1.04, letterSpacing: '-0.025em', color: C.cocoa, whiteSpace: 'nowrap' }}>
            {ln.some((w) => w === 4) ? (
              <>
                <span style={{ position: 'relative', display: 'inline-block' }}>
                  {word(4)}{word(5)}
                  <span style={{ position: 'absolute', left: 0, right: '0.25em', bottom: H.size * 0.02, height: fmt === 'wide' ? 8 : 7, borderRadius: 4, background: C.terracotta, transformOrigin: 'left center', transform: `scaleX(${ul})` }} />
                </span>
                {ln.filter((w) => w > 5).map(word)}
              </>
            ) : ln.map(word)}
          </div>
        ))}
      </div>
      <Col fmt={fmt} slot={fmt === 'wide' ? 'top' : 'bottom'} top={fmt === 'wide' ? H.endTop + H.lines.length * lh * H.endScale + 30 : undefined}>
        <Tag fmt={fmt} show={on(f, b(E.s1.tag))}>{`circle area scales with training rows · α = ${N.storyAlpha} · seed ${N.storySeed}`}</Tag>
      </Col>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ S2 · learning without sharing
function wave(frame: number, startBeat: number, stepBeat: number, travelBeats: number, inward: boolean, color: string, base: number): Dot[] {
  const dots: Dot[] = [];
  for (let i = 0; i < 10; i++) {
    const s = bf(startBeat + i * stepBeat) - base;
    const p = travel(frame, s, travelBeats);
    if (frame < s || p >= 0.995) continue;
    dots.push({ org: i, p, color, inward, opacity: Math.min(1, (frame - s) / 3, (1 - p) * 12) });
  }
  return dots;
}

export const S2Learning: React.FC = () => {
  const f = useCurrentFrame();
  const fmt = useFmt();
  const { width, height } = useVideoConfig();
  const S = 8; const b = at(S); const base = bf(S);
  const st = settled();
  const E2 = E.s2;
  const outs = E2.waves.filter((w) => !w.in).map((w) => b(w.at));
  const pulse = 1 + outs.reduce((acc, t) => acc + 0.09 * (spring(f, t, 'snap') - spring(f, t + 7, 'snap')), 0);
  const hub = { ...st.hub, scale: pulse };
  const dots = E2.waves.flatMap((w) => wave(f, w.at, w.in ? E2.dotStep : 0, E2.dotTravel, w.in, w.in ? C.plum : C.brass, base));
  const F_ = focus(fmt);
  const cam = camera(f, S, [
    { beat: 8, s: 1.03, ...F_.hub },
    { beat: 10, s: 1.07, ...F_.toward(0, 0.35) },
    { beat: 12, s: 1.06, ...F_.between(8, 9, 0.35) },
    { beat: 14, s: 1.02, ...F_.hub },
    { beat: 16, s: 1.07, ...F_.between(2, 3, 0.35) },
    { beat: 18, s: 1.03, ...F_.hub },
    { beat: 20, s: 1.07, ...F_.between(6, 7, 0.35) },
    { beat: 22, s: 1.04, ...F_.hub },
  ]);
  const s = sizes(fmt);
  const step2 = COPY.story.steps[1];
  const [send, back] = (step2.d() as string).split(/(?<=\.) /);
  const notes = (
    <Note fmt={fmt} style={fmt === 'tall' ? { fontSize: s.note * 1.15 } : { marginTop: 30 }}>
      <span style={{ opacity: on(f, b(E2.note1)) }}>Updates travel.</span>{' '}
      <span style={{ opacity: on(f, b(E2.note2)) }}>Packets don’t.</span>
    </Note>
  );
  return (
    <AbsoluteFill>
      <Bg color={C.cream} />
      <Network fmt={fmt} width={width} height={height} orgs={st.orgs} labels={st.labels} edge={st.edge} hub={hub} dots={dots} camera={cam} />
      <Col fmt={fmt} slot="top">
        <Tag fmt={fmt} style={{ marginBottom: 22 }}>{`circle area scales with training rows · α = ${N.storyAlpha} · seed ${N.storySeed}`}</Tag>
        <Title fmt={fmt}><LineUp p={spring(f, 0, 'type')}>{step2.t}</LineUp></Title>
        {fmt === 'wide' && (
          <>
            <Body fmt={fmt} show={on(f, b(E2.body1))} style={{ marginTop: 30 }}>{send}</Body>
            {notes}
            <Body fmt={fmt} show={on(f, b(E2.body2))} style={{ marginTop: 30 }}>{back}</Body>
          </>
        )}
      </Col>
      {fmt === 'tall' && (
        <Col fmt={fmt} slot="bottom">
          {notes}
          <Body fmt={fmt} show={on(f, b(E2.body2))} style={{ marginTop: 14 }}>{back}</Body>
        </Col>
      )}
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ S3 · uneven data
export const S3Uneven: React.FC = () => {
  const f = useCurrentFrame();
  const fmt = useFmt();
  const { width, height } = useVideoConfig();
  const S = 24; const b = at(S);
  const st = settled();
  const pie = spring(f, b(E.s3.pies), 'type');
  const orgs = st.orgs.map((o) => ({ ...o, pie, pieOpacity: 1 }));
  const F_ = focus(fmt);
  const cam = camera(f, S, [
    { beat: 24, s: 1.04, ...F_.hub },
    { beat: 26, s: 1.03, ...F_.toward(2, 0.25) },
    { beat: 28, s: 1.07, ...F_.toward(0, 0.5) },
    { beat: 30, s: 1.1, ...F_.toward(1, 0.45) },
    { beat: 32, s: 1.07, ...F_.toward(4, 0.5) },
    { beat: 34, s: 1.03, ...F_.hub },
  ]);
  const haloOrg = f >= b(E.s3.org4) ? 4 : 0;
  const haloP = spring(f, b(haloOrg === 4 ? E.s3.org4 : E.s3.org0), 'ui');
  const s = sizes(fmt);
  const step3 = COPY.story.steps[2];
  const legend = COPY.story.legend as string[];
  const callout = f >= b(E.s3.org4)
    ? { org: 'Org 4', big: N.org4Benign, rest: `Benign rows of ${N.org4Total}` }
    : { org: 'Org 0', big: N.org0Benign, rest: 'Benign' };
  const calloutOn = on(f, b(E.s3.org0));
  const swatch = [C.line, C.plum, C.terracotta, C.brass, C.olive];
  const Legend = (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px 26px', ...monoStyle(s.tag, C.muted) }}>
      {legend.map((t, k) => (
        <span key={t} style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
          <i style={{ width: 22, height: 22, borderRadius: 4, background: swatch[k], border: k === 0 ? `1.5px solid ${C.muted}` : 0 }} />{t}
        </span>
      ))}
    </div>
  );
  const Callout = (
    <div style={{ opacity: calloutOn }}>
      <div style={monoStyle(s.tag + 4, C.muted)}>{callout.org}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 18, flexWrap: 'wrap' }}>
        <span style={{ ...monoStyle(fmt === 'wide' ? 96 : 104, C.plum), fontWeight: 300, lineHeight: 1 }}>{callout.big}</span>
        <span style={{ fontFamily: F.body, fontSize: s.body + 2, color: C.inkSoft }}>{callout.rest}</span>
      </div>
    </div>
  );
  return (
    <AbsoluteFill>
      <Bg color={C.cream} />
      <Network fmt={fmt} width={width} height={height} orgs={orgs} labels={st.labels} edge={st.edge} hub={st.hub}
        halo={calloutOn ? { org: haloOrg, opacity: 1, scale: 0.85 + 0.15 * haloP } : null} camera={cam} />
      <Col fmt={fmt} slot="top">
        <Tag fmt={fmt} style={{ marginBottom: 22 }}>{`real training mix · α = ${N.storyAlpha} · seed ${N.storySeed}`}</Tag>
        <Title fmt={fmt}><LineUp p={spring(f, b(E.s3.question), 'type')}>{step3.t}</LineUp></Title>
        {fmt === 'wide' && (
          <>
            <div style={{ marginTop: 34 }}>{Legend}</div>
            <div style={{ marginTop: 44 }}>{Callout}</div>
            <Note fmt={fmt} style={{ marginTop: 34, opacity: on(f, b(E.s3.note)) }}><Tx>This unevenness is what α controls.</Tx></Note>
          </>
        )}
        {fmt === 'tall' && <div style={{ marginTop: 26 }}>{Legend}</div>}
      </Col>
      {fmt === 'tall' && (
        <Col fmt={fmt} slot="bottom" top={1490}>
          {Callout}
          <Note fmt={fmt} style={{ marginTop: 10, opacity: on(f, b(E.s3.note)) }}><Tx>This unevenness is what α controls.</Tx></Note>
        </Col>
      )}
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ S4 · it works
export const S4Works: React.FC = () => {
  const f = useCurrentFrame();
  const fmt = useFmt();
  const { width, height } = useVideoConfig();
  const S = 36; const b = at(S);
  const st = settled();
  const pieOut = 1 - spring(f, 0, 'type');
  const orgs = st.orgs.map((o) => ({ ...o, pie: 1, pieOpacity: pieOut }));
  const s = sizes(fmt);
  const card = spring(f, b(E.s4.alert), 'snap');
  const fr = FRAME[fmt];
  const F_ = focus(fmt);
  const wide = fmt === 'wide';

  if (f < b(E.s4.number)) {
    const g = F_.g;
    const cw = wide ? 720 : 860;
    const cam = camera(f, S, [{ beat: 36, s: 1.0, ...F_.hub }, { beat: 37, s: 1.1, ...F_.toward(9, 0.4) }, { beat: 38.5, s: 1.12, ...F_.toward(3, 0.45) }, { beat: 39.5, s: 1.06, ...F_.toward(5, 0.35) }]);
    return (
      <AbsoluteFill>
        <Bg color={C.cream} />
        <div style={{ position: 'absolute', inset: 0, opacity: 1 - 0.45 * Math.min(1, card) }}>
          <Network fmt={fmt} width={width} height={height} orgs={orgs} labels={st.labels} edge={st.edge} edgeOpacity={0.35} hub={st.hub} camera={cam} />
        </div>
        <div style={{
          position: 'absolute', left: g.hub.x - cw / 2, top: g.hub.y - (wide ? 170 : 200), width: cw,
          background: C.cocoa, borderRadius: 14, padding: wide ? '30px 36px' : '36px 40px',
          transformOrigin: '50% 50%', transform: `scale(${Math.max(0, card)})`,
        }}>
          <div style={monoStyle(s.tag, C.darkMuted)}>FIRST ALERT · SERVED MODEL</div>
          <div style={monoStyle(s.tag, C.darkMuted)}><Tx>{`α = ${N.servedAlpha} · SEED ${N.servedSeed} · ROUND ${N.servedRound}`}</Tx></div>
          <div style={{ fontFamily: F.disp, fontSize: wide ? 104 : 120, lineHeight: 1.05, color: C.cream, marginTop: 10 }}>{N.alertFamily}</div>
          <div style={{ ...monoStyle(s.body, C.darkText), marginTop: 8 }}>
            confidence <span style={{ color: C.cream }}>{N.alertConf}</span> · <span style={{ color: C.olive }}>{N.alertCorrect}</span>
          </div>
        </div>
        <Col fmt={fmt} slot="top">
          <Title fmt={fmt}>{COPY.story.steps[3].t}</Title>
          {wide && <Body fmt={fmt} style={{ marginTop: 30 }}>{COPY.story.steps[3].m()}</Body>}
        </Col>
      </AbsoluteFill>
    );
  }

  // 0.941 counts up; then the three seeds land on a 0–1 strip, and a zoom of its 0.80–1.00
  // window spreads them out so the ± std is visible, not just stated
  const nb = b(E.s4.number);
  const k = travel(f, nb, E.s4.countBeats);
  const done = f >= nb + bf(E.s4.countBeats);
  const shown = done ? N.f1 : (RAW.f1 * k).toFixed(3);
  const L = wide
    ? { title: 100, num: 172, label: 400, t1: 590, t2: 820, x0: fr.gx, W: 1690, fx: 1300, fy: 760, lab: 26, val: 52 }
    : { title: 510, num: 590, label: 820, t1: 1180, t2: 1440, x0: fr.gx, W: 952, fx: 700, fy: 1380, lab: 30, val: 48 };
  const zl = Number(N.zoomLo); const zh = Number(N.zoomHi);
  const X1 = (v: number) => L.x0 + v * L.W;
  const X2 = (v: number) => L.x0 + ((v - zl) / (zh - zl)) * L.W;
  const cam = camera(f, S, [
    { beat: 40, s: 1.0, fx: L.x0, fy: L.num },
    { beat: 42, s: 1.02, fx: L.x0, fy: L.num },
    { beat: 44, s: 1.025, fx: L.fx, fy: L.fy },
    { beat: 46, s: 1.045, fx: L.fx + 40, fy: L.fy + 20 },
  ]);
  const band = spring(f, b(E.s4.std), 'type');
  const m = RAW.f1;
  const sd = RAW.f1Std;
  const stripAt = b(E.s4.seeds) - 6;
  const axisOn = on(f, stripAt);
  const zoom = spring(f, stripAt, 'type');
  const seedAt = (seed: number) => b(E.s4.seeds + RAW.perSeed.findIndex((q) => q.seed === seed) * E.s4.seedStep);
  // the highest seed is labelled above the zoomed track, the others below it, under a row that
  // holds the 0.80 / mean / 1.00 ticks — so neighbouring seeds and the callout lines never collide
  const top = RAW.perSeed.reduce((a, c) => (c.v > a.v ? c : a));
  const above = (seed: number) => seed === top.seed;
  const tick = (x: number, y: number, text: string, color: string = C.muted, align: 'left' | 'right' | 'center' = 'center') => (
    <div style={{ position: 'absolute', left: align === 'left' ? x : align === 'right' ? x - 200 : x - 100, width: 200, textAlign: align, top: y, ...monoStyle(wide ? 26 : 30, color), opacity: axisOn }}>{text}</div>
  );
  return (
    <AbsoluteFill>
      <Bg color={C.cream} />
      <div style={{ position: 'absolute', inset: 0, transformOrigin: `${cam.fx}px ${cam.fy}px`, transform: `scale(${cam.scale})` }}>
        <div style={{ position: 'absolute', left: L.x0, top: L.title }}><Title fmt={fmt}>{COPY.story.steps[3].t}</Title></div>
        <div style={{ position: 'absolute', left: L.x0, top: L.num, ...monoStyle(s.big, done ? C.plum : C.muted), fontWeight: 300, lineHeight: 1, letterSpacing: '-0.02em' }}>{shown}</div>
        <div style={{ position: 'absolute', left: L.x0, top: L.label, width: wide ? 1690 : 952 }}>
          <Tag fmt={fmt} color={C.inkSoft} show={on(f, b(E.s4.label))} style={{ fontSize: s.tag + 6 }}>{`macro-F1 · FedAvg · α = ${N.f1Alpha} · mean of ${N.f1nWord} seeds`}</Tag>
          <Tag fmt={fmt} show={on(f, b(E.s4.std))} style={{ marginTop: 12, fontSize: s.tag + 2 }}>{`± ${N.f1Std} std across ${N.f1n} seeds · each dot is one seed’s model`}</Tag>
        </div>

        <svg width={width} height={height} style={{ position: 'absolute', inset: 0, overflow: 'visible' }}>
          {axisOn > 0 && (
            <>
              {/* full 0–1 strip with the zoom window marked */}
              <line x1={L.x0} x2={L.x0 + L.W} y1={L.t1} y2={L.t1} stroke={C.line} strokeWidth={6} strokeLinecap="round" />
              <rect x={X1(zl)} y={L.t1 - 18} width={X1(zh) - X1(zl)} height={36} rx={6} fill="none" stroke={C.plum} strokeWidth={2} />
              {/* callout lines from the window to the zoomed track */}
              <line x1={X1(zl)} y1={L.t1 + 18} x2={mix(X1(zl), L.x0, zoom)} y2={mix(L.t1 + 18, L.t2 - 40, zoom)} stroke={C.plum} strokeWidth={1.5} strokeDasharray="5 6" />
              <line x1={X1(zh)} y1={L.t1 + 18} x2={mix(X1(zh), L.x0 + L.W, zoom)} y2={mix(L.t1 + 18, L.t2 - 40, zoom)} stroke={C.plum} strokeWidth={1.5} strokeDasharray="5 6" />
              {/* zoomed track */}
              <line x1={L.x0} x2={L.x0 + L.W * zoom} y1={L.t2} y2={L.t2} stroke={C.line} strokeWidth={8} strokeLinecap="round" />
            </>
          )}
          {band > 0 && <rect x={X2(m - sd)} y={L.t2 - 30} width={(X2(m + sd) - X2(m - sd)) * band} height={60} rx={8} fill="rgba(58,40,92,.14)" />}
          {axisOn > 0 && <line x1={X2(m)} x2={X2(m)} y1={L.t2 - 40} y2={L.t2 + 40} stroke={C.plum} strokeWidth={4} opacity={zoom} />}
          {RAW.perSeed.map((p) => {
            const t = seedAt(p.seed);
            if (f < t) return null;
            const pp = spring(f, t, 'ui');
            return (
              <g key={p.seed}>
                <circle cx={X1(p.v)} cy={L.t1} r={8 * pp} fill={C.cocoa} />
                <circle cx={X2(p.v)} cy={L.t2} r={18 * pp} fill={C.cocoa} />
              </g>
            );
          })}
        </svg>
        {tick(L.x0, L.t1 + 24, N.axis0, C.muted, 'left')}
        {tick(L.x0 + L.W, L.t1 + 24, N.axis1, C.muted, 'right')}
        {tick(L.x0, L.t2 + 48, N.zoomLo, C.plum, 'left')}
        {tick(L.x0 + L.W, L.t2 + 48, N.zoomHi, C.plum, 'right')}
        <div style={{ position: 'absolute', left: X2(m) - 100, width: 200, textAlign: 'center', top: L.t2 + 48, ...monoStyle(wide ? 26 : 30, C.plum), opacity: axisOn }}>mean</div>
        {RAW.perSeed.map((p) => {
          const up = above(p.seed);
          const x = Math.min(X2(p.v), L.x0 + L.W - (wide ? 125 : 126));
          return (
            <div key={p.seed} style={{ position: 'absolute', left: x - 110, width: 220, textAlign: 'center', top: up ? L.t2 - (wide ? 132 : 136) : L.t2 + (wide ? 88 : 92), opacity: on(f, seedAt(p.seed)) }}>
              {up && <div style={monoStyle(L.lab, C.muted)}>{`seed ${p.seed}`}</div>}
              <div style={{ ...monoStyle(L.val, C.cocoa), lineHeight: 1.1 }}>{N[`f1Seed${p.seed}`]}</div>
              {!up && <div style={monoStyle(L.lab, C.muted)}>{`seed ${p.seed}`}</div>}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
