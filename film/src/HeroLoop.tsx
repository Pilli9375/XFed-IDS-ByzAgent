// Silent 12 s seamless loop for the site hero: network only, no text. Every motion is periodic
// in LOOP frames, so frame HERO_FRAMES-1 (= LOOP) renders identically to frame 0.
import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { C } from './theme';
import { Network, Dot, neutralOrg } from './Network';
import { easeInOut } from './motion';

const LOOP = 360; // 12 s at 30 fps
const CYCLE = 72; // one inward wave every 2.4 s (5 per loop)
const TRAVEL = 48;
export const HERO_FRAMES = LOOP + 1;

export const HeroLoop: React.FC = () => {
  const f = useCurrentFrame() % LOOP;
  const dots: Dot[] = [];
  for (let i = 0; i < 10; i++) {
    const t = (((f - i * 7) % CYCLE) + CYCLE) % CYCLE;
    const p = t / TRAVEL;
    const wave = Math.floor((((f - i * 7) % LOOP) + LOOP) % LOOP / CYCLE); // 0..4
    if (p < 1) {
      const out = wave === 4; // once per loop the averaged model goes back out
      dots.push({ org: i, p: easeInOut(p), color: out ? C.brass : C.plum, inward: !out, opacity: Math.min(1, p * 8, (1 - p) * 8) });
    }
  }
  const breathe = 1 + 0.02 * Math.sin((2 * Math.PI * f) / LOOP);
  return (
    <AbsoluteFill style={{ background: C.cream }}>
      <div style={{ position: 'absolute', inset: 0, opacity: 0.6 }}>
        <Network fmt="hero" width={1600} height={900}
          orgs={Array.from({ length: 10 }, () => neutralOrg(1))} edge={Array(10).fill(1)} edgeOpacity={0.5}
          hub={{ scale: breathe, fill: C.sand, stroke: C.plum }} dots={dots} />
      </div>
    </AbsoluteFill>
  );
};
