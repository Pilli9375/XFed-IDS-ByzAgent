# Review log

Critique rounds on full draft renders (`out/draft_16x9.mp4`, `out/draft_9x16.mp4`). Each round:
2 fps contact sheets per 15 s (16:9), full-resolution stills at key frames, a 9:16 phone strip
scaled to 360 px wide, `scripts/sync-check.mjs` for sound sync, and every on-screen number checked
against `out/numbers.json` (built from the JSON by `scripts/check-numbers.mjs`).

Scores 1–10: hook · readability at phone size · motion quality · variety · composition ·
brand accuracy · sound sync · factual accuracy.

---

## Round 1 — first full draft

| Hook | Phone | Motion | Variety | Composition | Brand | Sound sync | Factual |
|---|---|---|---|---|---|---|---|
| 7 | 6 | 7 | 8 | 6 | 9 | 7 | 8 |

**Three worst problems**
1. **0:37–0:40 (S5 α chart).** The 0.333 value label sat on the 95% interval whisker and inside
   the floor band. The CI label and the hand rule crossed it, so a key number was hard to read.
   That costs factual accuracy as well as composition.
2. **0:43–0:57 (S6, 9:16).** The top kicker ran off the right edge. "3 OF 10 POISONED" overlapped the
   clean grid's summary line. In 16:9 the rotated 0% stamp ran past the bottom edge.
3. **0:25.8 (S4 count landing).** The landing note was only +1.7 dB over the bed, so the moment
   0.941 turns plum had no audible hit. Mastering also fell back to loudnorm's dynamic mode.

Smaller: update dots (6 px) almost vanished at phone size, and the org 3/2 labels sat inside the right
safe margin (diagram offset +40 px).

**Factual check:** all 66 registry values appear as built, with α/seed tags present on every
dependent number. Flag counts in the grid match `decision_counts` (asserted in `numbers.js`).
Org 0's attack row is flagged in rounds 14 and 18 only, and org 5 in every round except 20; both
match `by_seed["1337"].f3_sudden.decisions`.

**Fixes for round 2:** values moved into a fixed column right of the tracks; CI label beside its row
label (16:9) or under the row (9:16); the hand rule dropped in 9:16. 9:16 grid smaller (28 px cells),
kicker on two lines, summaries full width. Stamp made smaller and raised. Dots 8–10 px. Diagram
offset removed. Landing note boosted and click added. Mastering switched to exact gain plus a
look-ahead limiter (−14.0 LUFS, −2.5 dBTP).

---

## Round 2 — after round-1 fixes

| Hook | Phone | Motion | Variety | Composition | Brand | Sound sync | Factual |
|---|---|---|---|---|---|---|---|
| 7 | 7 | 8 | 8 | 8 | 9 | 8 | 9 |

`sync-check.mjs`: every key event has an audio hit of +3 to +12 dB in the first 20 ms (the count
landing is now +4.0 dB). The silent beat measures −120 dB (digital silence).

**Three worst problems**
1. **0:43–0:57 (S6, 9:16).** The two-line kicker still crowded "NO ATTACK", and the first grid's
   summary sat against the second grid's heading.
2. **0:21.6–0:24 (S4, 9:16).** The alert card cut across the org 7 and org 3 labels, leaving label
   fragments peeking out under it.
3. **0:03.0–0:04.8 (S1).** After the underline draws, 1.8 s has nothing new. The type also looked
   small for a hook on a projector.

**Fixes for round 3:** hook type 132 → 156 px. On beat 6 the site's hero kicker
"FEDERATED INTRUSION DETECTION · VIT-AP 2026" sets, with a soft click. The network dims to 40%
under the alert card. The 9:16 grids were moved down and re-spaced.

## Round 3 — fact-check round (full-resolution stills, every number)

| Hook | Phone | Motion | Variety | Composition | Brand | Sound sync | Factual |
|---|---|---|---|---|---|---|---|
| 8 | 8 | 8 | 8 | 8 | 9 | 9 | 8 |

Sixteen full-resolution 16:9 stills (4.5 s to 70 s) were read against `out/numbers.json`. Every
built value appears exactly as formatted, with its α/seed tag. That covers 95.4%, 0 of 17,052,
DDoS / 0.9999 / correct / α 0.5 · seed 42 · round 18, 0.941 ± 0.057, all ten per-org Jaccard values,
0.667 / 0.538 / 0.333, floor 0.429–0.484, chance 0.065, interval 0.250–0.429, orgs 0, 3, 5 / 40%,
83/200, 29/60, 82/140, 0.00 → 0.95, 0.05 → 0.10, round 6 / Downweight / the verbatim sentence,
35–45%, 0%, seed 42 · α 0.5, #076 WebAttack → Benign, and 500.

**Three worst problems**
1. **1:02.4 (S7, alert #000).** The camera push scaled the image *inside* a fixed crop. That cut
   off the right edge of the real UI, so the SHAP values read "+2.5…". A real number was cut on
   screen, which is why factual drops to 8.
2. **Tags (S2, S5).** Line breaks fell before a "·" or between "α =" and "0.5".
3. **0:38–0:40 (S5 chart).** The dashed chance line ran through the "α 5.0 · similar" row labels.

**Fixes for round 4:** the camera now scales the whole crop box, so the crop never changes. The
dashboard eases 0.97 → 1.0 from its top-left corner, so its 48 px cream margin never shrinks. Tags
bind "· " and " = " with no-break spaces. The chance tick is drawn only across each track.

## Round 4 — final check before the full render

| Hook | Phone | Motion | Variety | Composition | Brand | Sound sync | Factual |
|---|---|---|---|---|---|---|---|
| 8 | 8 | 8 | 8 | 9 | 9 | 9 | 9 |

- Alert #000's SHAP values are fully on screen (+2.53, +2.07, +2.02, +1.57, +1.56). They match
  `replay_alerts.json · alerts[seq=0].top_features[*].shap_value` at 2 decimals, as the site shows them.
- 9:16 phone strip at 360 px: no overlaps. The smallest type is 30 px, which is about 10 px on a
  phone. That is legible, but it is the weakest point.
- Determinism: frame 1640 rendered twice gives byte-identical PNGs.
- Hero loop: rendered frame 0 and frame 360 are byte-identical PNGs. After encoding, both files
  decode first frame = last frame (luma difference 0), because keyframes are forced at both ends.
- Final master, measured on the rendered MP4: −14.0 LUFS integrated, −2.5 dBTP, LRA 2.9 LU.

**Still open:** the 9:16 grid and detail text sit at 30 px, which is the minimum. The dashboard's
own dark-blue theme reads as a different product next to the film. That was approved, and it is
not recoloured.

---

## Round 5 — planning-chat review: energy and composition

The planning chat checked frames and scored round 4's hook, motion and variety at 6–7, not the
8s logged above. They were right: the hook was 4.8 s of type with no motion, the camera only moved
in a few shots, the 0.941 frame was mostly empty, and the trust grid's lower half was dead. Every
number was kept; the only new values are listed below with their registry entries.

**Changes**
- **Hook (0–4.8 s).**
  - Each word slams in on its beat at 184 px (16:9) or 144 px (9:16). The scale goes 1.18 → 1 on
    a critically damped spring, anchored bottom-left, so a word only grows into empty space. An
    earlier try scaled from the centre at 1.45 and covered the neighbouring words.
  - On beat 5 the ten circles burst from behind "traffic." and fly to their places on a `ui`
    spring. The hook type settles into the text column, and the hub and edges are drawing by beat 6.5.
  - In 9:16 the hook is centred vertically, set over five lines at full column width.
- **Camera.** Every diagram chapter (S1–S6, S8) has camera keys every 1–2 beats on a slow spring
  (w = 2.8, critically damped), so each move is still running when the next starts. Moves push in
  toward the org under discussion (org 0 and org 4 in S3, orgs 4 and 7 in S5, org 5's row and then
  the call in S6) and drift gently otherwise. Screenshot moves are springs too; no easing curves remain.
  - Measured: frame-to-frame mean luma change on the 16:9 film (480 px, `tblend` + `signalstats`)
    has no run of 36+ frames (2 beats) below 0.1 anywhere. At the stricter 0.2 the one remaining
    run is the dashboard screenshot at 61.2–62.9 s, which is not a diagram.
- **0.941 frame.** Under the number:
  - A 0–1 strip with the three per-seed values as dots.
  - A marked 0.80–1.00 window with dashed callout lines to a full-width zoomed track. On it, the
    three seeds, the mean tick and a ± std band (graphic only) spread out so the spread is visible.
    Labels: seed 2024 · 0.860, seed 42 · 0.975, seed 1337 · 0.987.
  - The per-seed values are `fedprox_vs_fedavg.json · rows[alpha=0.5, seed].fedavg.test_macro_f1_headline`.
    `numbers.js` refuses to build unless they reproduce `headline.json`'s mean, std (population,
    ddof = 0), min and max to 1e-12.
- **Trust grid (16:9).**
  - Cells grew from 27 px to 32 px, so both grids span 115–1735 px (84% of the frame).
  - The caption and legend sit under the grids from beat 74, while they fill.
  - Org 5's flag rate moved to a right-hand callout, with org 0's note under it. The stamp is now
    horizontal, so it fits above the bottom safe area.
  - In 9:16 the camera pans up 110 px when the call opens.
- **Type floor.** 16:9: nothing under 24 px (axis numbers and the "VERBATIM" label are 24). 9:16:
  nothing under 30 px except the trust-grid row labels (30 as well).
- **Sound.**
  - One marimba note per hook word.
  - A click cascade, A2 hit and click on the burst.
  - Louder out-wave arpeggios with a D3 under them.
  - Clicks and notes for the three seed dots.
  - The pulse now enters with the hub, after the burst.
  - `sync-check.mjs` gained a transient (first-difference) column. The burst shows +4.8 dB
    transient; RMS alone can't separate it from the ringing word notes.
  - Master: −14.0 LUFS, −2.5 dBTP, LRA 3.5 LU.
- **Unchanged:** the hero loop (frame 100 re-rendered byte-identical to the shipped PNG sequence)
  and every value in rounds 1–4.

**New registry entries (73 total, was 66):** `f1Seed42` 0.975, `f1Seed1337` 0.987, `f1Seed2024` 0.860
(each from `fedprox_vs_fedavg.json`). Scale constants: `axis0` "0" and `axis1` "1" (macro-F1 range),
and `zoomLo` "0.80" / `zoomHi` "1.00" (zoom window, asserted to contain all three values and mean − std).

| Hook | Phone | Motion | Variety | Composition | Brand | Sound sync | Factual |
|---|---|---|---|---|---|---|---|
| 8 | 8 | 8 | 8 | 8 | 9 | 9 | 9 |

**Honest limits of these 8s**
- Hook: the slam is deliberately restrained (+18%) to obey "no overshoot on type". The burst origin
  is estimated from character widths, not measured from the DOM, so the circles come from roughly
  behind "traffic.", not from its exact centre.
- Variety: the network is still the base image in five chapters. Pies, values, poisoning and the
  camera vary it, but a viewer sees the same ring often.
- Composition: during the grid fill (beats 74–84) the bottom ~250 px of the 16:9 frame is still
  empty. In 9:16 the dashboard screenshot is small on its mat, because it is width-limited.
