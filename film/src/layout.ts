// Formats and the N—00 story-diagram geometry (ported from site/src/sections/StoryDiagram.jsx).
import { useVideoConfig } from 'remotion';
import { RAW } from './data';

export type Fmt = 'wide' | 'tall';
export const useFmt = (): Fmt => {
  const { width, height } = useVideoConfig();
  return width >= height ? 'wide' : 'tall';
};

// Site GEOM (coordinate boxes). Film scales the box `k` and offsets it (ox, oy).
const GEOM = {
  wide: { W: 760, H: 600, CX: 380, CY: 290, RX: 300, RY: 225, HUB: 46, R0: 12, R1: 30 },
  narrow: { W: 440, H: 470, CX: 220, CY: 240, RX: 125, RY: 170, HUB: 36, R0: 9, R1: 22 },
};

export const FRAME = {
  wide: { W: 1920, H: 1080, gx: 115, top: 80, bottom: 80 },
  tall: { W: 1080, H: 1920, gx: 64, top: 160, bottom: 220 },
} as const;

export type OrgGeo = { x: number; y: number; r: number; ux: number; uy: number; ang: number };
export type Geo = { k: number; hub: { x: number; y: number; r: number }; orgs: OrgGeo[] };

const tmax = Math.max(...RAW.comp.map((c) => c.total));

export function geometry(fmt: Fmt | 'hero'): Geo {
  const G = fmt === 'tall' ? GEOM.narrow : GEOM.wide;
  let k: number; let ox: number; let oy: number;
  if (fmt === 'wide') { k = 1.45; ox = 1920 - 115 - G.W * k; oy = (1080 - G.H * k) / 2 + 10; }
  else if (fmt === 'tall') { k = 2.16; ox = (1080 - G.W * k) / 2; oy = 470; }
  else { k = 1.3; ox = 1600 * 0.62 - G.CX * k; oy = 450 - G.CY * k; }
  const hub = { x: ox + G.CX * k, y: oy + G.CY * k, r: G.HUB * k };
  const orgs = RAW.comp.map((c, i) => {
    const ang = ((-90 + (360 / RAW.comp.length) * i) * Math.PI) / 180;
    const x = ox + (G.CX + G.RX * Math.cos(ang)) * k;
    const y = oy + (G.CY + G.RY * Math.sin(ang)) * k;
    const r = (G.R0 + G.R1 * Math.sqrt(c.total / tmax)) * k; // area ∝ training rows (site formula)
    const dx = hub.x - x; const dy = hub.y - y; const d = Math.hypot(dx, dy);
    return { x, y, r, ux: dx / d, uy: dy / d, ang };
  });
  return { k, hub, orgs };
}
