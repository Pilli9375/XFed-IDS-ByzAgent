// S8 · One still beat of silence, then the hub turns plum and reads "checks itself", the title
// and the team (site footer copy).
import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, F } from '../theme';
import { bf, spring, on, mix, camera, TL } from '../motion';
import { focus } from './S1to4';
import { useFmt } from '../layout';
import { COPY } from '../data';
import { Network } from '../Network';
import { Bg, Col, Tag, settled } from '../ui';
import { LineUp } from '../Text';

const E = TL.ev.s8;
const S = 108;
const b = (beat: number) => bf(beat) - bf(S);

export const S8Close: React.FC = () => {
  const f = useCurrentFrame();
  const fmt = useFmt();
  const wide = fmt === 'wide';
  const { width, height } = useVideoConfig();
  const st = settled();
  const lit = on(f, b(E.hub));
  const p = spring(f, b(E.hub), 'ui');
  const dim = spring(f, b(E.hub), 'type');
  const orgs = st.orgs.map((o) => ({ ...o, opacity: mix(1, 0.45, dim) }));
  const hub = lit
    ? { scale: 1 + 0.4 * p, fill: C.plum, stroke: C.plum, text: COPY.story.hub.checks as string, color: C.cream }
    : st.hub;
  const F_ = focus(fmt);
  // one still beat for the silence, then a push in on the hub as it turns plum, then a slow drift
  const cam = camera(f, S, [
    { beat: 108, s: 1.0, ...F_.hub },
    { beat: 109, s: 1.08, ...F_.hub },
    { beat: 111, s: 1.06, ...F_.toward(8, 0.25) },
    { beat: 113, s: 1.1, ...F_.hub },
    { beat: 115, s: 1.04, ...F_.toward(2, 0.35) },
    { beat: 116.5, s: 1.12, ...F_.toward(6, 0.25) },
  ]);
  const names = (COPY.footer.members as [string, string][]).map((m) => m[0]);
  const kicker = (COPY.hero.kicker as string).split('·').pop()!.trim(); // "VIT-AP 2026"
  const title = spring(f, b(E.title), 'type');
  const titleSize = wide ? 104 : 110;
  const Title = (
    <div style={{ fontFamily: F.disp, fontSize: titleSize, lineHeight: 1.0, letterSpacing: '-0.025em', color: C.cocoa }}>
      <LineUp p={title}>XFed-IDS-</LineUp>
      <LineUp p={spring(f, b(E.title) + 4, 'type')}><em style={{ color: C.plum }}>ByzAgent</em></LineUp>
    </div>
  );
  const Team = (
    <div style={{ opacity: on(f, b(E.team)) }}>
      <Tag fmt={fmt} style={{ marginBottom: 18 }}>{kicker}</Tag>
      <div style={{ display: 'grid', gridTemplateColumns: 'auto auto', gap: wide ? '12px 40px' : '12px 48px', justifyContent: 'start', fontFamily: F.body, fontSize: wide ? 36 : 40, color: C.cocoa }}>
        {names.map((n) => <span key={n}>{n}</span>)}
      </div>
    </div>
  );
  return (
    <AbsoluteFill>
      <Bg color={C.cream} />
      <Network fmt={fmt} width={width} height={height} orgs={orgs} labels={st.labels} edge={st.edge} edgeOpacity={mix(0.5, 0.25, dim)} hub={hub} camera={cam} />
      {wide ? (
        <Col fmt={fmt} slot="top" top={250}>
          {Title}
          <div style={{ marginTop: 70 }}>{Team}</div>
        </Col>
      ) : (
        <>
          <Col fmt={fmt} slot="top">{Title}</Col>
          <Col fmt={fmt} slot="bottom" top={1490}>{Team}</Col>
        </>
      )}
    </AbsoluteFill>
  );
};
