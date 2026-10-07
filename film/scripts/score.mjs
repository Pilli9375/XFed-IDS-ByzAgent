// Synthesises the film's score and sound effects from src/timeline.json (no samples):
// a modal-synthesis marimba pulse, soft felt-piano chords, wood clicks on data reveals, a low
// thump on the 0% stamp, and one beat of digital silence before the close. Then masters to
// -14 LUFS integrated / -1.5 dBTP with ffmpeg loudnorm (two pass) and writes out/beats.json.
// Deterministic: noise comes from a seeded PRNG.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const T = JSON.parse(readFileSync(path.join(ROOT, 'src', 'timeline.json'), 'utf8'));
const E = T.ev;
const SR = 48000;
const SPB = 60 / T.bpm; // seconds per beat
const DUR = T.durationInFrames / T.fps;
const N = Math.round(DUR * SR);
const L = new Float32Array(N);
const R = new Float32Array(N);
const at = (beat) => beat * SPB;

// mulberry32
let seed = 0x5eed1337;
const rnd = () => {
  seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};

const mtof = (m) => 440 * 2 ** ((m - 69) / 12);
const NOTE = { C: 0, 'C#': 1, D: 2, 'D#': 3, E: 4, F: 5, 'F#': 6, G: 7, 'G#': 8, A: 9, 'A#': 10, B: 11 };
const midi = (name) => {
  const m = name.match(/^([A-G]#?)(-?\d)$/);
  return 12 * (Number(m[2]) + 1) + NOTE[m[1]];
};

function add(t0, len, pan, fn) {
  const i0 = Math.max(0, Math.round(t0 * SR));
  const i1 = Math.min(N, i0 + Math.round(len * SR));
  const gl = Math.cos((pan + 1) * Math.PI / 4);
  const gr = Math.sin((pan + 1) * Math.PI / 4);
  for (let i = i0; i < i1; i++) {
    const v = fn((i - i0) / SR);
    L[i] += v * gl;
    R[i] += v * gr;
  }
}

// Marimba: three modal partials with their own decays + a short lowpassed mallet noise.
function marimba(t0, m, vel, pan = 0, decayScale = 1) {
  const f = mtof(m);
  const T1 = Math.min(2.2, Math.max(0.35, 1.5 * Math.sqrt(220 / f))) * decayScale;
  const parts = [[1, 1, T1], [3.932, 0.22, T1 * 0.22], [9.538, 0.06, T1 * 0.07]].filter(([r]) => f * r < SR / 2.2);
  const len = T1 * 5;
  let lp = 0;
  const noiseLen = 0.005;
  add(t0, len, pan, (t) => {
    const atk = Math.min(1, t / 0.0015);
    let s = 0;
    for (const [r, a, d] of parts) s += a * Math.exp(-t / d) * Math.sin(2 * Math.PI * f * r * t);
    if (t < noiseLen) { lp += 0.35 * ((rnd() * 2 - 1) - lp); s += 0.25 * lp * (1 - t / noiseLen); }
    return vel * atk * s;
  });
}

// Felt piano: slightly inharmonic harmonic stack, soft attack, per-partial decay.
function piano(t0, m, vel, pan = 0) {
  const f = mtof(m);
  const B = 0.0004;
  const parts = [];
  for (let n = 1; n <= 8; n++) {
    const fn = n * f * Math.sqrt(1 + B * n * n);
    if (fn < SR / 2.5) parts.push([fn, 1 / n ** 1.8, 3.2 / (1 + 0.5 * n)]);
  }
  add(t0, 4.5, pan, (t) => {
    const atk = Math.min(1, t / 0.012);
    let s = 0;
    for (const [fn, a, d] of parts) s += a * Math.exp(-t / d) * Math.sin(2 * Math.PI * fn * t);
    return vel * atk * s;
  });
}

// Wood click: bandpassed noise + short high sine.
function click(t0, vel = 1, pan = 0) {
  let y1 = 0; let y2 = 0;
  const f0 = 2600; const q = 6;
  const w = 2 * Math.PI * f0 / SR; const alpha = Math.sin(w) / (2 * q);
  const b0 = alpha; const a0 = 1 + alpha; const a1 = -2 * Math.cos(w); const a2 = 1 - alpha;
  let x1 = 0; let x2 = 0;
  add(t0, 0.06, pan, (t) => {
    const x = rnd() * 2 - 1;
    const y = (b0 * x - b0 * x2 - a1 * y1 - a2 * y2) / a0;
    x2 = x1; x1 = x; y2 = y1; y1 = y;
    return vel * (0.9 * y * Math.exp(-t / 0.008) + 0.12 * Math.sin(2 * Math.PI * 1900 * t) * Math.exp(-t / 0.018));
  });
}

// Low thump: falling sine 80 -> 50 Hz with a soft noise body.
function thump(t0, vel = 1) {
  let ph = 0; let lp = 0;
  add(t0, 0.6, 0, (t) => {
    const f = 50 + 30 * Math.exp(-t / 0.05);
    ph += 2 * Math.PI * f / SR;
    lp += 0.02 * ((rnd() * 2 - 1) - lp);
    return vel * (Math.sin(ph) * Math.exp(-t / 0.18) + 0.6 * lp * Math.exp(-t / 0.04));
  });
}

// ---------------------------------------------------------------- harmony (one chord per bar)
const CH = {
  D: ['D', ['D', 'F#', 'A']], Bm: ['B', ['B', 'D', 'F#']], G: ['G', ['G', 'B', 'D']], A: ['A', ['A', 'C#', 'E']],
  Em: ['E', ['E', 'G', 'B']], 'F#': ['F#', ['F#', 'A#', 'C#']],
};
// bar index -> chord (bar = 4 beats). S6 (bars 17-23) sits in B minor.
const BARS = ['D', 'D', 'D', 'Bm', 'G', 'A', 'Bm', 'G', 'A', 'G', 'D', 'A', 'D', 'Bm', 'G', 'Em', 'A',
  'Bm', 'G', 'Em', 'F#', 'Bm', 'G', 'F#', 'D', 'G', 'A', 'D', 'D', 'D'];
const pc = (n) => NOTE[n];
// nearest MIDI note with pitch class of `name` at or above `lo`
const voice = (name, lo) => { let m = lo; while (((m % 12) + 12) % 12 !== pc(name)) m++; return m; };

const silenceStart = at(E.s8.silence);
const closeStart = at(E.s8.hub);
const trustStart = at(E.s6.question);
const trustEnd = at(E.s7.site);

for (let bar = 0; bar < BARS.length; bar++) {
  const b0 = bar * T.beatsPerBar;
  const [root, tones] = CH[BARS[bar]];
  const tb = at(b0);
  if (tb >= DUR) break;
  const inTrust = tb >= trustStart && tb < trustEnd;
  const closing = b0 >= E.s8.silence;

  // bass on the downbeat (skip the hook's first bar so the three line notes stand alone)
  if (bar >= 1 && !closing) marimba(tb, voice(root, midi('D2')), inTrust ? 0.55 : 0.5, -0.1, 1.4);
  // soft felt-piano chord on the downbeat
  if (bar >= 2 && !closing) tones.forEach((n, k) => piano(tb + k * 0.012, voice(n, midi('F#3')), 0.11, -0.3 + 0.3 * k));

  // pulse: eighths in light chapters, quarters (lower) in the trust chapter
  if (b0 + 4 <= E.s1.underline) continue;
  const steps = inTrust ? 4 : 8;
  const order = [0, 2, 1, 2, 0, 2, 1, 2];
  for (let s = 0; s < steps; s++) {
    const beat = b0 + s * (4 / steps);
    if (beat < E.s1.underline) continue;
    if (beat >= E.s8.silence) break;
    const name = tones[order[s % order.length]];
    const m = voice(name, inTrust ? midi('B3') : midi('D4'));
    const accent = s % (steps / 4) === 0;
    marimba(at(beat), m, (accent ? 0.2 : 0.13) * (inTrust ? 1.1 : 1), s % 2 ? 0.25 : -0.25, 0.8);
  }
}

// hook: three notes as the lines set
marimba(at(E.s1.line1), midi('D4'), 0.55, -0.2);
marimba(at(E.s1.line2), midi('F#4'), 0.55, 0);
marimba(at(E.s1.line3), midi('A4'), 0.6, 0.2);
piano(at(E.s1.line3), midi('D3'), 0.18, 0);

// ---------------------------------------------------------------- data-reveal SFX
const CL = 0.16;
click(at(E.s1.kicker), CL * 0.8, 0.1);
for (let i = 0; i < 10; i++) click(at(E.s2.orgPop + i * E.s2.orgStep), CL, -0.6 + i * 0.13);
for (let i = 0; i < 10; i++) click(at(E.s2.dotsIn + i * E.s2.dotStep + E.s2.dotTravel), CL * 0.55, -0.4 + i * 0.08);
marimba(at(E.s2.out), midi('D5'), 0.18, 0.2); marimba(at(E.s2.out + 0.5), midi('F#5'), 0.16, 0.3); marimba(at(E.s2.out + 1), midi('A5'), 0.15, 0.4);
click(at(E.s3.org0), CL); click(at(E.s3.org4), CL);
// alert slam: low wood hit
marimba(at(E.s4.alert), midi('D2'), 0.9, 0, 1.2); click(at(E.s4.alert), 0.3);
// count-up ticks, bright landing note
for (let k = 0; k < 12; k++) click(at(E.s4.number + k * (E.s4.countBeats / 12)), CL * 0.45, 0.3);
marimba(at(E.s4.number + E.s4.countBeats), midi('A5'), 0.6, 0.1); marimba(at(E.s4.number + E.s4.countBeats), midi('D5'), 0.4, -0.1); click(at(E.s4.number + E.s4.countBeats), 0.3);
for (let i = 0; i < 10; i++) click(at(E.s5.values + i * E.s5.valueStep), CL, -0.6 + i * 0.13);
marimba(at(E.s5.drop), midi('B2'), 0.45, 0, 1.2); marimba(at(E.s5.drop), midi('D3'), 0.35, 0, 1.2);
click(at(E.s5.bar5), CL); click(at(E.s5.bar05), CL); click(at(E.s5.bar01), CL * 0.9); marimba(at(E.s5.bar01), midi('F#3'), 0.25, 0);
for (let i = 0; i < 3; i++) { click(at(E.s6.poison + i * E.s6.poisonStep), CL * 0.9); marimba(at(E.s6.poison + i * E.s6.poisonStep), midi('B2'), 0.3, 0, 0.8); }
for (let r = 0; r < 20; r++) click(at(E.s6.fill + r * E.s6.fillStep), 0.07, 0.15);
marimba(at(E.s6.org5), midi('F#5'), 0.3, 0.2);
click(at(E.s6.detail), CL);
thump(at(E.s6.stamp), 1.0);
click(at(E.s7.dash), CL); click(at(E.s7.ring), CL); marimba(at(E.s7.miss), midi('A2'), 0.45, 0, 1.2);

// ---------------------------------------------------------------- close
const closeD = ['D3', 'A3', 'D4', 'F#4', 'A4'];
closeD.forEach((n, k) => piano(closeStart + k * 0.02, midi(n), 0.26, -0.4 + 0.2 * k));
marimba(closeStart, midi('D2'), 0.6, 0, 1.6);
marimba(closeStart, midi('D5'), 0.3, 0.1, 1.4);
marimba(at(E.s8.title), midi('A4'), 0.22, -0.1, 1.4);
marimba(at(E.s8.team), midi('F#4'), 0.2, 0.1, 1.6);
marimba(at(E.s8.team + 1), midi('D4'), 0.22, 0, 2.0);

// ---------------------------------------------------------------- gates
const fadeIn = Math.round(0.06 * SR);
for (let i = 0; i < N; i++) {
  const t = i / SR;
  let g = 1;
  if (t >= silenceStart - 0.06 && t < silenceStart) g = (silenceStart - t) / 0.06; // close out the tails
  else if (t >= silenceStart && t < closeStart) g = 0; // one beat of digital silence
  if (t > DUR - 0.5) g *= Math.max(0, (DUR - t) / 0.5);
  if (i < fadeIn) g *= i / fadeIn;
  L[i] *= g; R[i] *= g;
}

// ---------------------------------------------------------------- write wav (float32)
function wav32(file, l, r) {
  const n = l.length;
  const buf = Buffer.alloc(44 + n * 8);
  buf.write('RIFF', 0); buf.writeUInt32LE(36 + n * 8, 4); buf.write('WAVE', 8);
  buf.write('fmt ', 12); buf.writeUInt32LE(16, 16); buf.writeUInt16LE(3, 20); buf.writeUInt16LE(2, 22);
  buf.writeUInt32LE(SR, 24); buf.writeUInt32LE(SR * 8, 28); buf.writeUInt16LE(8, 32); buf.writeUInt16LE(32, 34);
  buf.write('data', 36); buf.writeUInt32LE(n * 8, 40);
  for (let i = 0; i < n; i++) { buf.writeFloatLE(l[i], 44 + i * 8); buf.writeFloatLE(r[i], 48 + i * 8); }
  writeFileSync(file, buf);
}
let peak = 0;
for (let i = 0; i < N; i++) peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i]));
for (let i = 0; i < N; i++) { L[i] *= 0.5 / peak; R[i] *= 0.5 / peak; }

const AUD = path.join(ROOT, 'public', 'audio');
mkdirSync(AUD, { recursive: true });
const raw = path.join(ROOT, 'out', 'score_raw.wav');
mkdirSync(path.join(ROOT, 'out'), { recursive: true });
wav32(raw, L, R);

// Master to -14 LUFS: measure, apply exact gain, catch peaks with a look-ahead limiter at
// -2.5 dBFS (headroom for true peak <= -1.5 dBTP), re-measure and correct once.
const measure = (file, extra = []) => {
  const r = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', file, ...extra, '-af', 'ebur128=peak=true', '-f', 'null', '-'], { encoding: 'utf8' });
  const sum = r.stderr.slice(r.stderr.lastIndexOf('Summary:'));
  return { I: Number(sum.match(/I:\s+(-?[\d.]+) LUFS/)[1]), TP: Number(sum.match(/Peak:\s+(-?[\d.inf]+) dBFS/)[1]), LRA: Number(sum.match(/LRA:\s+(-?[\d.]+) LU/)[1]) };
};
const out = path.join(AUD, 'score.wav');
const master = (gain) => {
  const r = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-y', '-i', raw, '-af', `volume=${gain.toFixed(2)}dB,alimiter=limit=0.75:attack=4:release=60:level=false`, '-ar', String(SR), '-c:a', 'pcm_s16le', out], { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(r.stderr);
  return measure(out);
};
let gain = -14 - measure(raw).I;
let m = master(gain);
for (let k = 0; k < 4 && Math.abs(m.I + 14) > 0.1; k++) { gain += -14 - m.I; m = master(gain); }
console.log(`master: gain ${gain.toFixed(2)} dB -> I ${m.I} LUFS, true peak ${m.TP} dBFS, LRA ${m.LRA} LU`);
if (m.TP > -1.5) throw new Error('true peak above -1.5 dBTP');
const s3 = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', out, '-af', 'ebur128=peak=true', '-f', 'null', '-'], { encoding: 'utf8' });
const summ = s3.stderr.slice(s3.stderr.lastIndexOf('Summary:'));
console.log(summ.trim());

// ---------------------------------------------------------------- beats.json
const beats = Array.from({ length: T.totalBeats + 1 }, (_, b) => ({ beat: b, bar: Math.floor(b / T.beatsPerBar) + 1, downbeat: b % T.beatsPerBar === 0, t: +(b * SPB).toFixed(4), frame: b * T.framesPerBeat }));
writeFileSync(path.join(ROOT, 'out', 'beats.json'), JSON.stringify({
  bpm: T.bpm, fps: T.fps, framesPerBeat: T.framesPerBeat, durationInFrames: T.durationInFrames,
  cuts: T.cuts.map((b) => ({ beat: b, frame: b * T.framesPerBeat, t: +(b * SPB).toFixed(4) })),
  chapters: T.chapters.map((c) => ({ ...c, startFrame: c.start * T.framesPerBeat, endFrame: c.end * T.framesPerBeat })),
  silence: { fromFrame: E.s8.silence * T.framesPerBeat, toFrame: E.s8.hub * T.framesPerBeat },
  beats,
}, null, 1));
console.log('wrote public/audio/score.wav and out/beats.json');
