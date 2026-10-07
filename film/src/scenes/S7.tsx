// S7 · Proof it's real: real Playwright screenshots only (public/assets, see captures.json),
// cropped by rectangles and moved by a slow camera. Never recoloured or redrawn.
import React from 'react';
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from 'remotion';
import { C, F } from '../theme';
import { bf, spring, on, seg, easeInOut, TL } from '../motion';
import { useFmt } from '../layout';
import { N, COPY } from '../data';
import { Tag, Body } from '../ui';
import { monoStyle } from '../Text';
import captures from '../../public/assets/captures.json';

const E = TL.ev.s7;
const S = 96;
const b = (beat: number) => bf(beat) - bf(S);
const cap = (file: string) => captures.find((c: { file: string }) => c.file === file) as { jump_button_in_clip?: { x: number; y: number; width: number; height: number } };

/** A crop (source px) of a screenshot, shown at `scale` inside a box, with a camera push. */
const Shot: React.FC<{
  file: string; src: [number, number, number, number]; full: [number, number];
  x: number; y: number; scale: number; push?: number; drift?: [number, number]; origin?: string; boxH?: number;
}> = ({ file, src, full, x, y, scale, push = 1, drift = [0, 0], origin = '50% 50%', boxH }) => {
  const [sx, sy, sw, sh] = src;
  const w = sw * scale; const h = boxH ?? sh * scale;
  return (
    // the camera scales the whole crop box, so the crop itself never changes and no UI is cut off
    <div style={{ position: 'absolute', left: x, top: y, width: w, height: h, transformOrigin: origin, transform: `translate(${drift[0]}px, ${drift[1]}px) scale(${push})` }}>
      <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
        <Img src={staticFile(`assets/${file}`)} style={{ position: 'absolute', left: -sx * scale, top: -sy * scale, width: full[0] * scale, height: full[1] * scale, maxWidth: 'none' }} />
      </div>
    </div>
  );
};

const pill = (COPY.replay.pill as string).replace(/^●\s*/, ''); // ● is not in the site fonts
const servedTag = `served model · α = ${N.servedAlpha} · seed ${N.servedSeed} · round ${N.servedRound}`;

export const S7Proof: React.FC = () => {
  const f = useCurrentFrame();
  const fmt = useFmt();
  const wide = fmt === 'wide';
  const wipe = spring(f, 0, 'wipe');
  const tDash = b(E.dash); const tReplay = b(E.replay); const tMiss = b(E.miss);
  const k = (a: number, z: number) => easeInOut(seg(f, a, z));
  const caption = (t: string, top: number, color: string = C.darkMuted, left = wide ? 115 : 64) => (
    <div style={{ position: 'absolute', left, top, ...monoStyle(wide ? 28 : 32, color) }}>{t}</div>
  );

  let body: React.ReactNode;
  if (f < tDash) {
    // the showcase site
    const p = k(0, tDash);
    body = wide ? (
      <>
        <Shot file="site_story_desktop.png" full={[3840, 2160]} src={[820, 40, 2200, 1460]} scale={0.6} x={(1920 - 2200 * 0.6) / 2} y={110} push={1.02 + 0.02 * p} drift={[-24 * p, 0]} />
        {caption('the showcase site · React + Vite', 1010)}
      </>
    ) : (
      <>
        <Shot file="site_story_mobile.png" full={[1170, 2532]} src={[0, 0, 1170, 2532]} scale={952 / 1170} x={64} y={260} boxH={1300} drift={[0, -120 * p]} />
        {caption('the showcase site · React + Vite', 1600)}
      </>
    );
  } else if (f < tReplay) {
    // the running dashboard, on a cream mat (48 px margin, no frame, no shadow)
    const p = k(tDash, tReplay);
    body = (
      <AbsoluteFill style={{ background: C.cream }}>
        {wide ? (
          <>
            <Shot file="dashboard_trust_grid_desktop.png" full={[3840, 2160]} src={[576, 58, 2880, 1334]} scale={1824 / 2880} x={48} y={48} push={0.97 + 0.03 * p} origin="0 0" />
            {caption('the running dashboard · FastAPI + React', 48 + 1334 * (1824 / 2880) + 22, C.muted, 48)}
          </>
        ) : (
          <>
            <Shot file="dashboard_trust_grid_desktop.png" full={[3840, 2160]} src={[614, 614, 1383, 768]} scale={984 / 1383} x={48} y={620} push={0.97 + 0.03 * p} origin="0 0" />
            {caption('the running dashboard · FastAPI + React', 620 + 768 * (984 / 1383) + 24, C.muted, 48)}
          </>
        )}
      </AbsoluteFill>
    );
  } else if (f < tMiss) {
    // alert #000 with its SHAP bars; a drawn ring marks the real "Jump to a miss" button
    const p = k(tReplay, tMiss);
    const ring = spring(f, b(E.ring), 'type');
    if (wide) {
      const s = 1690 / 2500;
      const bt = cap('site_replay_000_desktop.png').jump_button_in_clip!;
      const x0 = (1920 - 1690) / 2; const y0 = 300;
      const cx = x0 + (bt.x + bt.width / 2) * 2 * s; const cy = y0 + (bt.y + bt.height / 2) * 2 * s;
      body = (
        <>
          <Shot file="site_replay_000_desktop.png" full={[2500, 730]} src={[0, 0, 2500, 730]} scale={s} x={x0} y={y0} push={1 + 0.03 * p} origin={`${cx - x0}px ${cy - y0}px`} />
          <Ring cx={cx} cy={cy} rx={bt.width * s * 2 * 0.5 + 26} ry={bt.height * s * 2 * 0.5 + 20} p={ring} />
          {caption(servedTag, 230)}
        </>
      );
    } else {
      const sb = 952 / 1044; const sp = 952 / 1074;
      const bt = cap('site_replay_bar_mobile.png').jump_button_in_clip!;
      const cx = 64 + (bt.x + bt.width / 2) * 3 * sb; const cy = 330 + (bt.y + bt.height / 2) * 3 * sb;
      body = (
        <>
          <Shot file="site_replay_bar_mobile.png" full={[1044, 387]} src={[0, 0, 1044, 387]} scale={sb} x={64} y={330} />
          <Shot file="site_replay_000_mobile.png" full={[1074, 1041]} src={[0, 0, 1074, 1041]} scale={sp} x={64} y={720} push={1 + 0.02 * p} />
          <Ring cx={cx} cy={cy} rx={bt.width * 3 * sb * 0.5 + 24} ry={bt.height * 3 * sb * 0.5 + 18} p={ring} />
          {caption(servedTag, 250)}
        </>
      );
    }
  } else {
    // #076: the first miss, SHAP panel + verdict only (the analyst note is left out)
    const p = k(tMiss, bf(TL.ev.s8.silence) - bf(S));
    const missCaption = `#${N.missSeq} · a real miss: ${N.missTrue} called ${N.missPred}`;
    const foot = `${N.nAlerts} real test rows, read once for display only; no metric comes from them.`;
    body = wide ? (
      <>
        <Shot file="site_replay_076_desktop.png" full={[1448, 722]} src={[0, 0, 1448, 722]} scale={1} x={(1920 - 1448) / 2} y={170} push={1 + 0.03 * p} />
        {caption(servedTag, 110)}
        <div style={{ position: 'absolute', left: (1920 - 1448) / 2 + 48, top: 920 }}>
          <div style={{ fontFamily: F.body, fontSize: 38, color: C.cream }}>{missCaption}</div>
        </div>
        <div style={{ position: 'absolute', left: (1920 - 1448) / 2 + 48, top: 980, opacity: on(f, b(E.miss + 1)) }}>
          <Body fmt={fmt} color={C.darkMuted} style={{ fontSize: 28 }}>{foot}</Body>
        </div>
      </>
    ) : (
      <>
        <Shot file="site_replay_076_mobile.png" full={[1122, 1227]} src={[0, 0, 1122, 1227]} scale={952 / 1122} x={64} y={300} push={1 + 0.03 * p} />
        {caption(servedTag, 230)}
        <div style={{ position: 'absolute', left: 64, top: 300 + 1227 * (952 / 1122) + 40, width: 952 }}>
          <div style={{ fontFamily: F.body, fontSize: 42, color: C.cream, lineHeight: 1.3 }}>{missCaption}</div>
          <Body fmt={fmt} color={C.darkMuted} style={{ fontSize: 32, marginTop: 14, opacity: on(f, b(E.miss + 1)) }}>{foot}</Body>
        </div>
      </>
    );
  }

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ background: C.cocoa2, transform: `translateY(${(1 - wipe) * 100}%)` }}>
        {f < tDash || f >= tReplay ? (
          <div style={{ position: 'absolute', left: wide ? 115 : 64, top: wide ? 54 : 160 }}>
            <Tag fmt={fmt} color={C.brass}>{pill}</Tag>
          </div>
        ) : null}
        {body}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** Hand-drawn annotation ring (not UI): an ellipse that draws on. */
const Ring: React.FC<{ cx: number; cy: number; rx: number; ry: number; p: number }> = ({ cx, cy, rx, ry, p }) => {
  if (p <= 0) return null;
  const len = Math.PI * (3 * (rx + ry) - Math.sqrt((3 * rx + ry) * (rx + 3 * ry)));
  return (
    <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0, overflow: 'visible' }}>
      <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill="none" stroke={C.cream} strokeWidth={4} strokeLinecap="round"
        strokeDasharray={len} strokeDashoffset={len * (1 - p)} transform={`rotate(-4 ${cx} ${cy})`} />
    </svg>
  );
};
