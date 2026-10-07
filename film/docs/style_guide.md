# Film style guide

Taken from the live showcase site (`site/src/styles.css`, `site/src/sections/StoryDiagram.jsx`,
`site/src/copy.js`, `site/src/format.js`, `site/src/fonts.css`). The film borrows the site's
grammar (palette, type, diagram geometry, number formatting) so the two read as one product.
Where the film needs something the site doesn't have (springs, camera, sound), it is defined here.

---

## 1. Palette

Exact tokens from `site/src/styles.css :root`. No other colours, no gradients.

| Token | Hex | Film role |
|---|---|---|
| cream | `#F6F0E4` | Light chapters' background; text on dark |
| sand | `#ECE3D1` | Hub fill (shared model); panel wells on cream |
| line | `#DCD0BA` | Hairlines, chart tracks, Benign slice of pies |
| cocoa | `#2B211C` | Text on cream; trust chapter background; cards |
| cocoa-2 | `#1F1814` | Proof chapter background (site's darkest, Replay) |
| ink-soft | `#4A3D35` | Body text on cream |
| muted | `#6E6157` | Labels, axis text, org labels on cream |
| plum | `#3A285C` | The system's colour: hub border, update dots, agreement bars, the closing hub |
| terracotta | `#A85F3F` | Fills and lines only: poisoned borders, underline, floor band edge |
| terracotta-text | `#8F4E31` | Terracotta *text* on cream/sand (low-Jaccard values, "poisoned") |
| terracotta-light | `#D98A68` | Terracotta on dark: quarantine cells, poisoned row rule, the 0% stamp |
| brass | `#C19A52` | Halo on the featured org, downweight cells, positive SHAP bars, kickers on dark |
| olive | `#8E9A4F` | Trust cells, "correct" verdict |
| blush | `#F3D9CC` | Fill of a poisoned org circle (site step 6) |
| dark-line | `#45382F` | Hairlines on cocoa |
| dark-muted | `#ADA192` | Labels on cocoa |
| dark-faint | `#7D7064` | Negative SHAP bars, zero line |
| dark-text | `#D9CFBF` | Body text on cocoa |
| dark-well | `#3A2E27` | Empty grid cell, SHAP track |

**Colour meaning stays fixed across the whole film.** Plum is the shared model and agreement.
Terracotta is poisoned or low. Olive, brass and terracotta-light are trust, downweight and
quarantine, exactly as on the site's trust grid. At the chapter cut from explanations (S5) to
trust (S6) every org circle returns to neutral cream first. Orgs 4 and 7 are terracotta in S5
(low Jaccard) and are also flagged in S6. If the colour carried over, the film would suggest a
link between the two experiments that we do not claim.

Pie slice order and colours (site `PIE`): Benign `line` · DoS `plum` · DDoS `terracotta` ·
PortScan `brass` · other attacks (Bot, BruteForce, Heartbleed, Infiltration, WebAttack) `olive`.

## 2. Type

Only the self-hosted woff2 files in `site/public/fonts`, loaded in Remotion with
`@remotion/fonts` from copies made by a sync script that checks the SHA-256 of each copy against
the site original. Weights available, and nothing else is used:

| Family | Files | Use |
|---|---|---|
| Brygada 1918 | 400, 400 italic, 500 | Display: hook lines, chapter questions, the closing title. `em` words in italic plum (cream chapters) or italic terracotta-light/brass (dark chapters), as on the site. Letter-spacing −0.025em, line-height 0.98. |
| Schibsted Grotesk | 400, 500 | Body: captions, definitions, team names. |
| Atkinson Hyperlegible Mono | 300, 400 | **Every number** and every data label (org ids, seed/α tags, kickers like `N—02 · …`). `font-variant-numeric: tabular-nums`. 300 for big hero numbers (as in the site's loader), 400 for everything else. |
| Alegreya italic | 400 italic | Margin notes only (the site's `.note`): "Updates travel. Packets don't.", "directional, not significant at α = 0.1". |

### Sizes (px at 1080 tall for 16:9; at 1080 wide for 9:16)

| Role | 16:9 | 9:16 |
|---|---|---|
| Hook display | 132 | 112 |
| Chapter question | 88 | 84 |
| Big number (macro-F1, the stamp) | 220 (mono 300) | 200 |
| Card title | 64 | 64 |
| Caption / body | 36 | 40 |
| Margin note | 40 | 44 |
| Data label (org ids, values, seed/α tags) | 28 minimum, values 34 | 34 minimum, values 40 |

Nothing on screen is smaller than 28 px in 16:9 or 34 px in 9:16. Text is always rendered as
text (never a scaled bitmap), so no blur.

## 3. Numbers

- Every number is computed at render time from `site/public/data/*.json`, imported directly
  (`film/src/data.ts`). No numeric literal sits in any scene component.
- Formatting reuses `site/src/format.js` by import, so the film rounds exactly like the site:
  `f3` for metrics (0.941, 0.292), `pct1` for shares (95.4%), `pctWhole` for rates (0%, 40%),
  `conf4` truncates confidence (0.99999964 → 0.9999, never 1.0000), `f2` for flag rates, U+2212 minus.
- Shared strings that already exist on the site (step captions, card heads, legend, trust
  summaries, replay labels, team names) are imported from `site/src/copy.js`, not retyped.
- **Seed and α tags** sit next to every number that depends on them, set in mono 28 px muted,
  e.g. `α = 0.5 · seed 1337`. When the source changes between shots (seed 1337 network → all-seed
  α bars → seed 42 stamp), the tag changes visibly with it.
- Count-ups: when a number counts up, it counts in `muted` and switches to its final colour on the
  exact value. The viewer only reads a value in full colour when it is the real number.
- `film/scripts/check-numbers.mjs` writes `film/out/numbers.json`: every on-screen numeric
  string → its JSON file + key path → raw value → formatted string. The critique rounds check
  this file against frames.

## 4. The N—00 story diagram (reused geometry)

From `StoryDiagram.jsx`, coordinate box scaled to the frame:

- `wide`: W 760 × H 600, centre (380, 290), ellipse radii RX 300 / RY 225, hub radius 46,
  org radius `R0 12 + R1 30 · sqrt(TOTAL / max TOTAL)` (area ∝ training rows), label offset 24.
- `narrow` (9:16): W 440 × H 470, centre (220, 240), RX 125 / RY 170, hub 36, R0 9, R1 22, label 20.
- Org *i* sits at angle `−90° + 36°·i` (org 0 at 12 o'clock, clockwise).
- Edges: org rim → hub rim, 1.5 px cocoa at 50% opacity (scaled with the box), drawn rim-outward→hub.
- Hub: sand fill, 1.5 px plum border, mono label `shared\nmodel`. Close: plum fill, cream text
  `checks\nitself`, scale 1.4, orgs and edges dim (orgs 0.45, edges 0.25), labels stay at full strength.
- Update dots: 6 px plum, travel rim → hub.
- Poisoned org: blush fill, terracotta border, label `poisoned` in terracotta-text.
- Featured org halo: 2 px brass ring, radius + 12.
- Cards: cocoa, radius 14, padding 18/22, head mono dark-muted, title Brygada, body mono or note.

In the film the box is scaled to fill the frame: about 1.6× in 16:9 (the diagram takes the right
62% of the frame, captions in the left column at the 6% gutter, as on the site's pinned story),
about 2.3× of `narrow` in 9:16 (diagram in the middle 55%, captions below).

## 5. Other reused components

- **Agreement bar** (site `.agree`): line-coloured track, floor band `rgba(168,95,63,.20)` with
  dashed terracotta edges, chance tick dashed muted, plum bar, pill radius.
- **Trust grid** (site `.tgrid`): 20 px square cells, radius 3, dark-well empty, olive / brass /
  terracotta-light = trust / downweight / quarantine, 3 px terracotta-light left rule on
  ground-truth poisoned rows, flag-rate column `0.00 → 0.95`. Scaled ×1.6 in the film.
- **Agent detail** (site `.tdet`): cocoa-2 panel, mono head, Brygada decision word, `THE AGENT'S
  STATED REASON, VERBATIM`, reason in Schibsted 21 px ×1.6.
- **SHAP bars**: shown only via the real site screenshot (§8), never redrawn.

## 6. Motion grammar

- **Render is a pure function of the frame.** No CSS transitions or keyframes, no timers, no
  `Math.random`. Seeded noise only (mulberry32 with a fixed seed).
- **Springs, closed-form** (damped harmonic, `x(t)` evaluated directly per frame). Two presets:
  - `ui`: damping 14, stiffness 170, mass 1, about 4% overshoot. Used for circles, cards, cells and the stamp.
  - `type`: critically damped, no overshoot. Used for anything with letters.
  A value with several targets is a sum of springs, one per change.
- **Type sets, it does not fade.** Words appear at full opacity on a beat. The only type
  movement is the site's `lineup` mask: a line rises 0.5 em into a clipping box over 9 frames
  with the `type` spring. The hook uses hard sets with no mask.
- **Camera**: one slow move per shot at most, push ≤ 6% scale or drift ≤ 3% of frame width,
  `type` spring or linear. No rotation, no shake, no zoom blur.
- **Cuts**: hard cuts on beats (`film/out/beats.json`). Two transition types:
  1. *Match through the hub*: the hub stays put while everything around it changes.
  2. *Panel wipe*: a cocoa panel slides up over the frame. This is the site loader's motion,
     `cubic-bezier(.76,0,.24,1)` approximated by the `type` spring, 12 frames, landing on a beat.
     Used once into the dark trust chapter and once into proof.
- Stagger: org-indexed events advance one org per half-beat (9 frames) unless stated.
- Something new every 2–4 seconds; no beat is held still longer than 4 s except the
  deliberate one-beat silence before the close.

## 7. Composition and safe areas

- 16:9: 6% side gutter (site `--gutter`) = 115 px, 80 px top/bottom. Left-aligned type on the
  gutter, never a centred title on an empty field.
- 9:16: 64 px side gutter, 160 px top, 220 px bottom (platform UI). Each scene has its own layout
  function: `layout(format) → boxes`. Nothing is cropped from the 16:9 master. The vertical
  version is re-laid out.
- Flat colour fields. No vignette, no grain, no orbs (the site's blurred hero orbs are left out:
  in a still video frame they read as a generic gradient).

## 8. Real UI

The dashboard and site appear only as **Playwright screenshots** of the real builds, captured at
2× device pixel ratio so they stay sharp under a 6% push. They are shown in a plain frame:
14 px radius, `0 18px 40px rgba(43,33,28,.25)` shadow, as on the site's cards. They are never
recoloured, retouched or redrawn. The React dashboard has its own dark-blue theme (`#0d1117`,
cyan accent). It will look like a different product next to the film's palette, and it stays
that way because it is the real thing.

## 9. Sound

- Score synthesised in code (Node, no samples): a marimba made by modal synthesis (partials at
  1, 3.93 and 9.24 × f0 with separate exponential decays, plus a short seeded-noise mallet click).
  Soft piano-like voicing comes from lowpassed sine stacks for chords. No synth pads.
- 100 BPM. One beat = 0.6 s = 18 frames at 30 fps, one bar = 72 frames.
- Key D major (D, Bm, G, A). The trust chapter drops to B minor and thins to quarter notes.
  The close resolves on D.
- SFX: soft wood clicks on data reveals (−24 dB under the score), a low sine thump (55 Hz, 180 ms)
  on the 0% stamp, a dry tick per round in the grid fill (−30 dB), and one full beat of digital
  silence before the close.
- Master to −14 LUFS integrated, true peak ≤ −1.5 dBTP (ffmpeg `loudnorm`, two pass).

## 10. Banned in this film

Centred title on a gradient · fades as the default entrance · a logo slapped on the end ·
corner labels and frame borders · glow, bloom or drop-shadow on text · particle bursts ·
glowing 3D networks · dead beats · blurry scaled text · invented UI · any number not traced to
a JSON key · the same colour meaning different things in different chapters.
