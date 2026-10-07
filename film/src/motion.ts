// Pure functions of the frame: beat grid, closed-form springs, seeded noise.
import T from './timeline.json';

export const FPS = T.fps;
export const FPB = T.framesPerBeat;
/** Frame of a (possibly fractional) beat. */
export const bf = (beat: number) => Math.round(beat * FPB);

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const mix = (a: number, b: number, p: number) => a + (b - a) * p;
/** Linear 0..1 progress between two frames. */
export const seg = (frame: number, f0: number, f1: number) => clamp01((frame - f0) / Math.max(1, f1 - f0));
export const easeInOut = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2);
export const easeOut = (x: number) => 1 - (1 - x) ** 3;

type Preset = { w: number; z: number };
// ui: ~4% overshoot (circles, cards, cells, the stamp). type: critically damped, no overshoot.
export const SPRING: Record<'ui' | 'type' | 'slow' | 'wipe' | 'snap' | 'slam' | 'drift' | 'cam', Preset> = {
  ui: { w: 13, z: 0.72 },
  snap: { w: 22, z: 0.72 },
  type: { w: 14, z: 1 },
  slow: { w: 4, z: 1 },
  wipe: { w: 22, z: 1 },
  slam: { w: 26, z: 1 }, // hook words: fast, no overshoot (type never overshoots)
  drift: { w: 2.2, z: 1 }, // slow camera drift on screenshots
  cam: { w: 2.8, z: 1 }, // diagram camera: each move overlaps the next key, so it never settles
};

/** Closed-form damped spring from 0 to 1, starting at `start` (frames). */
export function spring(frame: number, start: number, preset: keyof typeof SPRING = 'ui') {
  const t = (frame - start) / FPS;
  if (t <= 0) return 0;
  const { w, z } = SPRING[preset];
  if (z >= 1) return 1 - Math.exp(-w * t) * (1 + w * t);
  const wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + ((z * w) / wd) * Math.sin(wd * t));
}

/** Hard set: 0 before the frame, 1 from it. Type never fades. */
export const on = (frame: number, at: number) => (frame >= at ? 1 : 0);

export function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const TL = T;

export type CamKey = { beat: number; s: number; fx: number; fy: number };
/**
 * Camera as a sum of springs, one per key change (the "several targets" rule): scale and focus
 * point move toward each key from its beat on. Keys use global beats; `frame` is chapter-local.
 */
export function camera(frame: number, chapterStartBeat: number, keys: CamKey[], preset: keyof typeof SPRING = 'cam') {
  let { s, fx, fy } = keys[0];
  for (let i = 1; i < keys.length; i++) {
    const p = spring(frame, bf(keys[i].beat) - bf(chapterStartBeat), preset);
    s += (keys[i].s - keys[i - 1].s) * p;
    fx += (keys[i].fx - keys[i - 1].fx) * p;
    fy += (keys[i].fy - keys[i - 1].fy) * p;
  }
  return { scale: s, fx, fy };
}

/** Critically damped 0..1 travel that is ~99% done `beats` after `start` (frames). */
export function travel(frame: number, start: number, beats: number) {
  const t = (frame - start) / FPS;
  if (t <= 0) return 0;
  const w = 6.6 / (beats * (60 / T.bpm));
  return Math.min(1, 1 - Math.exp(-w * t) * (1 + w * t));
}
