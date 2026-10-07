// Sound-sync check: RMS (dBFS) in 20 ms windows just before vs just after each key visual event.
// A hit on the event shows as a jump of several dB inside the first window after it.
import { readFileSync } from 'node:fs';
const T = JSON.parse(readFileSync(new URL('../src/timeline.json', import.meta.url)));
const buf = readFileSync(new URL('../public/audio/score.wav', import.meta.url));
let off = 12; let fmt; let data;
while (off < buf.length) {
  const id = buf.toString('ascii', off, off + 4); const sz = buf.readUInt32LE(off + 4);
  if (id === 'fmt ') fmt = { ch: buf.readUInt16LE(off + 10), sr: buf.readUInt32LE(off + 12) };
  if (id === 'data') { data = { start: off + 8, len: sz }; break; }
  off += 8 + sz;
}
const n = data.len / 2 / fmt.ch;
const s = (i) => (buf.readInt16LE(data.start + i * 2 * fmt.ch) + buf.readInt16LE(data.start + i * 2 * fmt.ch + 2)) / 65536;
const rms = (t0, t1) => { let a = 0; let c = 0; for (let i = Math.max(0, Math.round(t0 * fmt.sr)); i < Math.min(n, Math.round(t1 * fmt.sr)); i++) { a += s(i) ** 2; c++; } return 10 * Math.log10(a / Math.max(1, c) + 1e-12); };
const spb = 60 / T.bpm; const E = T.ev;
const events = [
  ['S1 line 1', E.s1.line1], ['S1 line 3', E.s1.line3], ['S2 first org', E.s2.orgPop], ['S4 alert slam', E.s4.alert],
  ['S4 count lands', E.s4.number + E.s4.countBeats], ['S5 org 4/7 drop', E.s5.drop], ['S5 bar 0.1', E.s5.bar01],
  ['S6 first poison', E.s6.poison], ['S6 stamp thump', E.s6.stamp], ['S7 #076 cut', E.s7.miss], ['S8 close chord', E.s8.hub],
];
for (const [name, beat] of events) {
  const t = beat * spb;
  console.log(name.padEnd(18), `t=${t.toFixed(2)}s`, `before ${rms(t - 0.04, t - 0.005).toFixed(1)} dB`, `after ${rms(t, t + 0.02).toFixed(1)} dB`);
}
const sil = E.s8.silence * spb;
console.log('silent beat'.padEnd(18), `${sil.toFixed(2)}–${(sil + spb).toFixed(2)}s`, `${rms(sil + 0.01, sil + spb - 0.01).toFixed(1)} dB`);
