import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, F } from '../theme';
import { bf, spring, on, seg, mix, easeInOut, easeOut, TL } from '../motion';
import { useFmt, FRAME, geometry } from '../layout';
import { N, RAW, COPY } from '../data';
import { Network, Dot } from '../Network';
import { Bg, Col, Title, Body, Note, Tag, sizes, settled } from '../ui';
import { Tx, LineUp, monoStyle } from '../Text';

const E = TL.ev;
const at = (chapterStart: number) => (beat: number) => bf(beat) - bf(chapterStart);

// ------------------------------------------------------------------ S1 · hook
export const S1Hook: React.FC = () => {
  const f = useCurrentFrame();
  const fmt = useFmt();
  const b = at(0);
  const fr = FRAME[fmt];
  const size = fmt === 'wide' ? 156 : 100;
  const push = 1 + 0.02 * easeInOut(seg(f, 0, bf(8)));
  const ul = spring(f, b(E.s1.underline), 'type');
  const line: React.CSSProperties = { display: 'block', fontFamily: F.disp, fontSize: size, lineHeight: 1.08, letterSpacing: '-0.025em', color: C.cocoa };
  return (
    <AbsoluteFill>
      <Bg color={C.cream} />
      <div style={{
        position: 'absolute', left: fr.gx, top: fmt === 'wide' ? 250 : 640, transformOrigin: '0 50%', transform: `scale(${push})`,
      }}>
        <span style={{ ...line, opacity: on(f, b(E.s1.line1)) }}>{N.nOrgsWord} organizations.</span>
        <span style={{ ...line, opacity: on(f, b(E.s1.line2)) }}>One detector.</span>
        <span style={{ ...line, opacity: on(f, b(E.s1.line3)) }}>
          <span style={{ position: 'relative', display: 'inline-block' }}>
            No shared
            <span style={{ position: 'absolute', left: 0, right: 0, bottom: size * 0.04, height: fmt === 'wide' ? 6 : 5, borderRadius: 3, background: C.terracotta, transformOrigin: 'left center', transform: `scaleX(${ul})` }} />
          </span>{' '}traffic.
        </span>
        <div style={{ ...monoStyle(fmt === 'wide' ? 28 : 32, C.plum), letterSpacing: '0.06em', marginTop: fmt === 'wide' ? 44 : 40, opacity: on(f, b(E.s1.kicker)) }}>
          {(COPY.hero.kicker as string).replace(/^●\s*/, '')}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ S2 · learning without sharing
/** Update dots for one wave: org i leaves at start + i*step beats, travels `travel` beats. */
function wave(frame: number, startBeat: number, stepBeat: number, travelBeats: number, inward: boolean, color: string, base: number): Dot[] {
  const dots: Dot[] = [];
  for (let i = 0; i < 10; i++) {
    const s = bf(startBeat + i * stepBeat) - base;
    const p = seg(frame, s, s + bf(travelBeats));
    if (p <= 0 || p >= 1) continue;
    dots.push({ org: i, p: easeInOut(p), color, inward, opacity: Math.min(1, p * 8, (1 - p) * 8) });
  }
  return dots;
}

export const S2Learning: React.FC = () => {
  const f = useCurrentFrame();
  const fmt = useFmt();
  const { width, height } = useVideoConfig();
  const S = 8; const b = at(S); const base = bf(S);
  const st = settled();
  const orgs = st.orgs.map((o, i) => ({ ...o, scale: spring(f, b(E.s2.orgPop + i * E.s2.orgStep), 'ui') }));
  const labels = st.labels.map((l, i) => ({ ...l, opacity: on(f, b(E.s2.orgPop + i * E.s2.orgStep)) }));
  const edge = st.edge.map((_, i) => spring(f, b(E.s2.hub + i * E.s2.edgeStep), 'type'));
  const pulse = 1 + 0.08 * Math.sin(Math.PI * seg(f, b(E.s2.out), b(E.s2.out) + 10));
  const hub = { ...st.hub, scale: spring(f, b(E.s2.hub), 'ui') * pulse };
  const dots = [
    ...wave(f, E.s2.dotsIn, E.s2.dotStep, E.s2.dotTravel, true, C.plum, base),
    ...wave(f, E.s2.out, 0, E.s2.dotTravel, false, C.brass, base),
    ...wave(f, E.s2.dotsIn2, E.s2.dotStep, E.s2.dotTravel, true, C.plum, base),
  ];
  const g = geometry(fmt);
  const cam = { scale: 1 + 0.04 * easeInOut(seg(f, 0, bf(16))), fx: g.hub.x, fy: g.hub.y };
  const s = sizes(fmt);
  const step2 = COPY.story.steps[1];
  // the site's step-2 text, split at its sentence boundary: "sends only the model update" | "averages them"
  const [send, back] = (step2.d() as string).split(/(?<=\.) /);
  return (
    <AbsoluteFill>
      <Bg color={C.cream} />
      <Network fmt={fmt} width={width} height={height} orgs={orgs} labels={labels} edge={edge} hub={hub} dots={dots} camera={cam} />
      <Col fmt={fmt} slot="top">
        <Tag fmt={fmt} show={on(f, b(E.s2.hub))} style={{ marginBottom: 22 }}>{`circle area scales with training rows · α = ${N.storyAlpha} · seed ${N.storySeed}`}</Tag>
        <Title fmt={fmt}><LineUp p={spring(f, 0, 'type')}>{step2.t}</LineUp></Title>
        {fmt === 'wide' && (
          <>
            <Body fmt={fmt} show={on(f, b(E.s2.hub))} style={{ marginTop: 30 }}>{send}</Body>
            <Note fmt={fmt} style={{ marginTop: 30 }}>
              <span style={{ opacity: on(f, b(E.s2.note1)) }}>Updates travel.</span>{' '}
              <span style={{ opacity: on(f, b(E.s2.note2)) }}>Packets don’t.</span>
            </Note>
            <Body fmt={fmt} show={on(f, b(E.s2.out))} style={{ marginTop: 30 }}>{back}</Body>
          </>
        )}
      </Col>
      {fmt === 'tall' && (
        <Col fmt={fmt} slot="bottom">
          <Note fmt={fmt} style={{ fontSize: s.note * 1.15 }}>
            <span style={{ opacity: on(f, b(E.s2.note1)) }}>Updates travel.</span>{' '}
            <span style={{ opacity: on(f, b(E.s2.note2)) }}>Packets don’t.</span>
          </Note>
          <Body fmt={fmt} show={on(f, b(E.s2.out))} style={{ marginTop: 14 }}>{back}</Body>
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
  const pie = easeOut(seg(f, b(E.s3.pies), b(E.s3.pies) + 14));
  const orgs = st.orgs.map((o) => ({ ...o, pie, pieOpacity: 1 }));
  const g = geometry(fmt);
  const o0 = g.orgs[0]; const o4 = g.orgs[4];
  const p0 = spring(f, b(E.s3.org0), 'slow');
  const p4 = spring(f, b(E.s3.org4), 'slow');
  // push toward the called-out org, but only half way so every label stays in frame
  const tx = mix(mix(g.hub.x, o0.x, 0.5), o4.x, 0.5);
  const fx = mix(mix(g.hub.x, mix(g.hub.x, o0.x, 0.5), p0), tx, p4);
  const fy = mix(mix(g.hub.y, mix(g.hub.y, o0.y, 0.5), p0), mix(mix(g.hub.y, o0.y, 0.5), o4.y, 0.5), p4);
  const cam = { scale: 1 + 0.05 * p0, fx, fy };
  const haloOrg = f >= b(E.s3.org4) ? 4 : 0;
  const haloP = spring(f, b(haloOrg === 4 ? E.s3.org4 : E.s3.org0), 'ui');
  const s = sizes(fmt);
  const step3 = COPY.story.steps[2];
  const legend = COPY.story.legend as string[];
  const callout = f >= b(E.s3.org4)
    ? { org: 'Org 4', big: N.org4Benign, rest: `Benign rows of ${N.org4Total}` }
    : { org: 'Org 0', big: N.org0Benign, rest: 'Benign' };
  const calloutOn = on(f, b(E.s3.org0));
  const Legend = (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px 26px', ...monoStyle(s.tag, C.muted) }}>
      {legend.map((t, k) => (
        <span key={t} style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
          <i style={{ width: 22, height: 22, borderRadius: 4, background: ['line', 'plum', 'terracotta', 'brass', 'olive'].map((n) => (C as Record<string, string>)[n])[k], border: k === 0 ? `1.5px solid ${C.muted}` : 0 }} />{t}
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
  const pieOut = 1 - seg(f, 0, 9);
  const orgs = st.orgs.map((o) => ({ ...o, pie: 1, pieOpacity: pieOut }));
  const g = geometry(fmt);
  const s = sizes(fmt);
  const card = spring(f, b(E.s4.alert), 'snap');
  const showNumber = f >= b(E.s4.number);
  const fr = FRAME[fmt];

  if (!showNumber) {
    const cw = fmt === 'wide' ? 720 : 860;
    return (
      <AbsoluteFill>
        <Bg color={C.cream} />
        <div style={{ position: 'absolute', inset: 0, opacity: 1 - 0.6 * Math.min(1, card) }}>
          <Network fmt={fmt} width={width} height={height} orgs={orgs} labels={st.labels} edge={st.edge} edgeOpacity={0.35} hub={st.hub} />
        </div>
        <div style={{
          position: 'absolute', left: g.hub.x - cw / 2, top: g.hub.y - (fmt === 'wide' ? 170 : 200), width: cw,
          background: C.cocoa, borderRadius: 14, padding: fmt === 'wide' ? '30px 36px' : '36px 40px',
          transformOrigin: '50% 50%', transform: `scale(${Math.max(0, card)})`,
        }}>
          <div style={monoStyle(s.tag, C.darkMuted)}>FIRST ALERT · SERVED MODEL</div>
          <div style={monoStyle(s.tag, C.darkMuted)}><Tx>{`α = ${N.servedAlpha} · SEED ${N.servedSeed} · ROUND ${N.servedRound}`}</Tx></div>
          <div style={{ fontFamily: F.disp, fontSize: fmt === 'wide' ? 104 : 120, lineHeight: 1.05, color: C.cream, marginTop: 10 }}>{N.alertFamily}</div>
          <div style={{ ...monoStyle(s.body, C.darkText), marginTop: 8 }}>
            confidence <span style={{ color: C.cream }}>{N.alertConf}</span> · <span style={{ color: C.olive }}>{N.alertCorrect}</span>
          </div>
        </div>
        <Col fmt={fmt} slot="top">
          <Title fmt={fmt}>{COPY.story.steps[3].t}</Title>
          {fmt === 'wide' && <Body fmt={fmt} style={{ marginTop: 30 }}>{COPY.story.steps[3].m()}</Body>}
        </Col>
      </AbsoluteFill>
    );
  }

  const nb = b(E.s4.number);
  const k = seg(f, nb, nb + bf(E.s4.countBeats));
  const done = k >= 1;
  const shown = done ? N.f1 : (RAW.f1 * easeOut(k)).toFixed(3);
  const push = 1 + 0.03 * seg(f, nb, b(12));
  return (
    <AbsoluteFill>
      <Bg color={C.cream} />
      <div style={{ position: 'absolute', left: fr.gx, top: fmt === 'wide' ? 190 : 560, transformOrigin: '0 0', transform: `scale(${push})` }}>
        <Title fmt={fmt}>{COPY.story.steps[3].t}</Title>
        <div style={{ ...monoStyle(s.big, done ? C.plum : C.muted), fontWeight: 300, lineHeight: 1, marginTop: 40, letterSpacing: '-0.02em' }}>{shown}</div>
        <Tag fmt={fmt} color={C.inkSoft} show={on(f, b(E.s4.label))} style={{ marginTop: 26, fontSize: s.tag + 6 }}>{`macro-F1 · FedAvg · α = ${N.f1Alpha} · mean of ${N.f1nWord} seeds`}</Tag>
        <Tag fmt={fmt} show={on(f, b(E.s4.std))} style={{ marginTop: 16, fontSize: s.tag + 2 }}>{`± ${N.f1Std} std across ${N.f1n} seeds`}</Tag>
      </div>
    </AbsoluteFill>
  );
};
