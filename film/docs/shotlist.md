# Shot list

**Film:** a federated intrusion detector that checks itself.
**Audience:** capstone panel on a projector, visitors to the showcase site, and phone viewers (9:16).
**Engine:** Remotion (React + SVG). The site is React, so the film imports the same JSON and the
same `format.js` / `copy.js`.
**Grid:** 100 BPM · beat = 0.6 s = 18 f · bar = 72 f @ 30 fps · 29 bars + 1.2 s ring-out =
**70.8 s (2124 frames)**. Every cut below lands on a beat (`b` = beat index from 0).

The beat sheet's times are moved onto the grid: 0:04 → 4.8, 0:14 → 14.4, 0:22 → 21.6,
0:30 → 28.8, 0:42 → 40.8, 0:58 → 57.6, 1:06 → 64.8. Each chapter stays within 1.2 s of the brief.

Number column: on-screen string → JSON file · key. Values were read from the files on 2026-10-07,
and `check-numbers.mjs` re-reads them at render.

---

## S1 · Hook — 0.0–4.8 s · f0–144 · b0–8 · cream

| Beat | Time | What happens | On screen | Sound |
|---|---|---|---|---|
| b0 | 0.0 | Line 1 **sets** (hard, no fade) on the left gutter, Brygada 132 | "Ten organizations." | First marimba note, D |
| b2 | 1.2 | Line 2 sets | "One detector." | Note F♯ |
| b4 | 2.4 | Line 3 sets | "No shared traffic." | Note A |
| b5 | 3.0 | 4 px terracotta underline draws under "No shared" (site `.underl`, `type` spring, 9 f) | — | Pulse begins: soft marimba eighths |
| b7 | 4.2 | Hold | — | — |

"Ten" is `headline.json · dataset.n_organizations` (= 10) spelled by a lookup, with an assertion.

9:16: three lines stacked at 112 px in the upper third, left aligned.

## S2 · Learning without sharing — 4.8–14.4 s · f144–432 · b8–24 · cream

Hard cut. The text column on the left holds the site's step-2 copy as it develops.

| Beat | Time | What happens | On screen | Sound |
|---|---|---|---|---|
| b8 | 4.8 | Ten org circles pop in (`ui` spring), org 0 at 12 o'clock then clockwise, one per half-beat. Area ∝ training rows. | "Org 0" … "Org 9" (mono labels) | Soft click per circle (10) |
| b12 | 7.2 | Hub scales in. Edges draw rim → hub, staggered 0.07 s as on the site. | Hub: "shared model". Tag: "circle area ∝ training rows · α = 0.5 · seed 1337" | Bass D on downbeat |
| b14 | 8.4 | First plum update dots travel inward, one per org, staggered | — | Click as each dot reaches the hub |
| b16 | 9.6 | Margin note sets, word group 1 | *"Updates travel."* (Alegreya) | — |
| b18 | 10.8 | Word group 2 | *"Packets don't."* | — |
| b20 | 12.0 | Hub pulses once (`ui` scale 1 → 1.08 → 1). The averaged model goes back out as brass dots, hub → orgs. | Caption: "The shared model averages them and sends the result back." (site step 2) | Rising marimba arpeggio |
| b22 | 13.2 | Second inward wave. Camera has pushed 4% across the shot. | — | — |

Numbers: circle radii ← `story.json · composition.rows[i].TOTAL` (no number printed; the sizes are
the data). Tag ← `story.json · alpha`, `seed`.

9:16: `narrow` geometry in the middle 55%, captions below the diagram.

## S3 · Uneven data — 14.4–21.6 s · f432–648 · b24–36 · cream

Match through the hub: the network stays, the circles change.

| Beat | Time | What happens | On screen | Sound |
|---|---|---|---|---|
| b24 | 14.4 | Each circle becomes a pie of its real class mix (conic sweep, all together, 12 f). Legend sets. | Legend: Benign · DoS · DDoS · PortScan · Other attacks. Tag: "real training mix · α = 0.5 · seed 1337" | Chord change Bm |
| b26 | 15.6 | Chapter question in the left column | "Nobody's traffic looks alike" (site step 3 title) | — |
| b28 | 16.8 | Camera pushes 6% toward org 0. Brass halo on org 0. Callout card. | "Org 0 · **95.4%** Benign" | Click |
| b32 | 19.2 | Camera drifts to org 4. Halo moves. Callout. | "Org 4 · **0** Benign rows of **17,052**" (no Benign at all) | Click |
| b34 | 20.4 | Margin note | *"This unevenness is what α controls."* (site step 3 note) | — |

Numbers: 95.4% ← `story.json · composition.rows[0].Benign / rows[0].TOTAL` (401889 / 421112, `pct1`).
0 ← `rows[4].Benign`. 17,052 ← `rows[4].TOTAL` (`int`). Pie slices ← `rows[i]` columns per site `PIE` order.

9:16: the callouts sit below the diagram instead of beside the org.

## S4 · It works — 21.6–28.8 s · f648–864 · b36–48 · cream → number card

| Beat | Time | What happens | On screen | Sound |
|---|---|---|---|---|
| b36 | 21.6 | Pies go back to plain circles. The alert card **slams** out of the hub (`ui` spring from scale 0 at the hub centre to full, 10 f). | Card head "FIRST ALERT · SERVED MODEL · α = 0.5 · SEED 42 · ROUND 18" / title "DDoS" / body "confidence 0.9999 · correct" | Low wood hit + G chord |
| b40 | 24.0 | Hard cut to a cream field, number left-aligned. **0.941** counts up over 3 beats in muted, then turns plum on the exact value. | "0.941" (mono 300, 220 px) | Ticks under the count, one bright note on landing |
| b41 | 24.6 | Label sets under the number | "macro-F1 · FedAvg · α = 0.5 · mean of three seeds" | — |
| b44 | 26.4 | Secondary line sets *(proposed, see Decided)* | "± 0.057 std across seeds 42, 1337, 2024" | — |
| b46 | 27.6 | Hold | — | — |

Numbers: "DDoS" ← `replay_alerts.json · alerts[seq=0].predicted_family`. 0.9999 ← `alerts[seq=0].confidence`
(0.99999964, `conf4` truncation). "correct" ← `alerts[seq=0].correct`. Seed 42 / round 18 / α 0.5 ←
`headline.json · served_demo_model.seed / best_round / alpha`. 0.941 ←
`headline.json · fedavg_macro_f1_headline_by_alpha["0.5"].mean` (0.94079, `f3`). 0.057 ← `…["0.5"].std`.
"three" ← `…["0.5"].n` (= 3), spelled with an assertion.

## S5 · Do they agree on why? — 28.8–40.8 s · f864–1224 · b48–68 · cream

| Beat | Time | What happens | On screen | Sound |
|---|---|---|---|---|
| b48 | 28.8 | Cut back to the network, all circles neutral. Question sets with the `lineup` mask. | "Do they agree on *why*?" ("why" plum italic). Tag: "α = 0.5 · seed 1337" | Chord D |
| b50 | 30.0 | Per-org Jaccard@10 values set under each org label, one per half-beat, in plum | 0.538 ×7, 0.484 (org 2), 0.292 (orgs 4, 7) | Click per value (10) |
| b51 | 30.6 | Definition in the left column | "Share of top-10 reasons an org's model has in common with the shared model. 1 = identical." | — |
| b56 | 33.6 | Orgs 4 and 7 **drop**: values and circles sink 14 px (`ui` spring) and turn terracotta-text. The other eight stay. | "0.292" ×2. Caption: "Orgs 4 and 7, with little or no Benign traffic, share only 0.292. The middle org sits at 0.538." | Low marimba minor third |
| b58 | 34.8 | **Hard cut** to the α chart: three agreement tracks stacked, labelled "α 5.0 · similar", "α 0.5 · uneven", "α 0.1 · very uneven". The seed-noise band shades across all three. | Band label: "seed-noise floor 0.429–0.484 · centralized models that differ only by seed". Tag: "median Jaccard@10 · seeds 42, 1337, 2024" | Bass G |
| b60 | 36.0 | α 5.0 bar grows | "0.667" | Click |
| b61 | 36.6 | α 0.5 bar grows | "0.538" | Click |
| b62 | 37.2 | α 0.1 bar grows and stops left of the band | "0.333" | Lower click |
| b63 | 37.8 | Chance tick draws | "chance 0.065" | — |
| b64 | 38.4 | 95% interval whisker draws on the α 0.1 bar and reaches into the band. A margin note sets with a hand-drawn rule to the overlap. | *"directional, not significant at α = 0.1"* + mono "95% interval 0.250–0.429" | — |
| b66 | 39.6 | Hold | — | — |

Numbers: per-org values ← `story.json · per_silo_agreement.rows[i].jaccard_at_10` (`f3`).
Median 0.538 ← median of those 10 (site `jacMedian`). Low threshold 0.4 is the site's design
constant `LOW_JACCARD` (a styling cutoff, not a result; never printed). 0.667 / 0.538 / 0.333 ←
`agreement_by_alpha.json · by_alpha[a].median.jaccard_at_10`. 0.429–0.484 ←
`agreement_by_alpha.json · instability_floor.jaccard_at_10_range` (the same values are in
`headline.json · centralized_seed_instability_floor.jaccard_at_10_range`). 0.065 ←
`chance_jaccard_at_10`. 0.250 / 0.429 ← `ci.json · by_metric.jaccard_at_10.ci95_low / ci95_high`
(α 0.1 only, matching `ci.json · alpha`).

9:16: the network uses the `narrow` geometry. The α chart becomes three full-width tracks
stacked vertically, with the note underneath.

## S6 · Can they be trusted? — 40.8–57.6 s · f1224–1728 · b68–96 · cream → cocoa

Chapter break: the S5 chart clears to the neutral network first. No colour from S5 carries into S6.

| Beat | Time | What happens | On screen | Sound |
|---|---|---|---|---|
| b68 | 40.8 | Network, all neutral. Question sets. | "And can they be *trusted*?" | Key drops to Bm, pulse to quarter notes |
| b70 | 42.0 | Orgs 0, 3, 5 turn **terracotta** (blush fill, terracotta border, label "poisoned"), one per half-beat | Caption: "Orgs 0, 3 and 5 are secretly poisoned: 40% of their attack traffic relabelled as Benign. The agent is never told." Tag "α = 0.5 · seed 1337" | Three low clicks |
| b72 | 43.2 | **Panel wipe** to cocoa. Trust grid: "NO ATTACK" and "3 OF 10 POISONED" side by side, rows Org 0–9, 20 round columns, dark-well cells. Terracotta-light rule on rows 0, 3, 5 (ground truth, hidden from the agent). | Legend: Trust · Downweight · Quarantine · Poisoned (ground truth, hidden from agent). Tag "seed 1337 · α = 0.5" | — |
| b73–82 | 43.8–49.2 | The grid **fills round by round**, one column per half-beat, both runs together (20 rounds) | Round axis 1…20 | Dry tick per round |
| b76 | 45.6 | Caption | "Left, nobody is attacking. Right, orgs 0, 3 and 5 are poisoned." | — |
| b80 | 48.0 | Summary lines set under each grid (site copy) | "83 of 200 calls flagged, nobody attacking" · "poisoned 29/60 flagged · honest 82/140" | — |
| b82 | 49.2 | **Org 5's row lights up**; other rows dim to 35%. Flag-rate column for org 5. | "0.00 → 0.95" | Brighter note |
| b84 | 50.4 | Round-6 cell gets a cream ring. The detail panel opens below the grid. | "SEED 1337 · ATTACK RUN · ORG 5 · ROUND 6" / "Downweight" / "THE AGENT'S STATED REASON, VERBATIM" | Click |
| b85–88 | 51.0–52.8 | The verbatim sentence **types out** (≈ 64 chars/s) | "high train_loss (0.3766992952671328) and low cosine_to_global (0.3590587707828174) suggest a potentially malicious client." | No typing SFX |
| b88 | 52.8 | Fidelity line sets under the reason, small | "Reasons shown as written; about 35–45% of the agent's trend claims contradicted the numbers it was given." | — |
| b89 | 53.4 | Org 0 row brightens briefly. Note. | "Org 0 barely moves (0.05 → 0.10)." | — |
| b90 | 54.0 | **Stamp** lands over the right third (`ui` spring scale 1.25 → 1, −3° set, no rotation animation), terracotta-light ink | "Multi-Krum excluded **0%**" / under it: "poisoned orgs excluded · given the true attacker count · seed 42 · α = 0.5" | **Low thump** |
| b92–95 | 55.2–57.0 | Hold | — | Bm sustains |

Numbers: 0, 3, 5 ← `byzagent_decisions.json · by_seed["1337"].f3_sudden.true_malicious_silos`. 40% ←
`…f3_sudden.attack.sudden.flip_fraction` (`pctWhole`). "3 OF 10" ← `….attack.f`, `n_silos`. Grid cells ←
`…clean.decisions[]` and `…f3_sudden.decisions[]` (`round`, `silo`, `decision`). 83/200, 29/60, 82/140 ←
counts of `decision ≠ trust` over those arrays (site's `sumClean` / `sumAttack`; the 29/60 and 82/140
match `decision_counts`). 0.00 → 0.95 ← org 5 flagged rounds / 20 in clean vs attack (0/20, 19/20, `f2`).
0.05 → 0.10 ← the same for org 0 (1/20, 2/20). Round 6, "Downweight", the sentence ←
`…f3_sudden.decisions[silo=5, round=6].decision / explanation`, with the selection read from
`story.json · pointers.byzagent.featured_silo / featured_round`. 35–45% ←
`byzagent_decisions.json · trend_claim_error_range_pct.low / high`. 0% ←
`baselines.json · strategies[multikrum].conditions.f3.mechanism.malicious_exclusion_rate` (`pctWhole`).
Seed 42 / α 0.5 ← `baselines.json · seed / alpha`.

9:16: the two grids stack (no attack on top, attack below), the detail panel underneath, and the
stamp over the lower grid.

## S7 · Proof it's real — 57.6–64.8 s · f1728–1944 · b96–108 · cocoa-2

Real screenshots only (asset list below). Each one sits in a 14 px-radius frame under a slow push
or drift.

| Beat | Time | What happens | On screen | Sound |
|---|---|---|---|---|
| b96 | 57.6 | Panel wipe. Showcase site screenshot (story section) drifts left. | Pill: "Recorded from real runs · nothing simulated" (site copy) | Key back to D, pulse returns |
| b98 | 58.8 | Hard cut: dashboard screenshot (Alert Stream / Client Trust Monitor), slow push | Tag: "React dashboard · FastAPI backend" | Click |
| b100 | 60.0 | Hard cut: site Replay screenshot, one alert selected, SHAP bars visible. Camera eases onto the SHAP panel. | (Text in the screenshot.) Tag: "served model · α = 0.5 · seed 42 · round 18" | — |
| b102 | 61.2 | A drawn cream ring (annotation, not UI) circles the real "Jump to a miss" button | — | Click |
| b103 | 61.8 | Hard cut: the same screenshot after the click, **#076**: "✕ missed · this was WebAttack" | Caption: "#076 · a real miss: WebAttack called Benign" | Low note |
| b106 | 63.6 | Hold, drift continues | Foot: "500 real test rows, read once for display only; no metric comes from them." | — |

Numbers: #076 ← first `correct == false` in `replay_alerts.json · alerts` (seq 76), which is also
where the site's `jumpMiss` lands from the start. WebAttack / Benign ←
`alerts[seq=76].true_family / predicted_family`. 500 ← `replay_alerts.json · n_alerts`.

9:16: the mobile-viewport screenshots of the site (390 × 844 @3×), stacked. The dashboard
screenshot is shown full width with a vertical pan.

## S8 · Silence and close — 64.8–70.8 s · f1944–2124 · b108–118 · cream

| Beat | Time | What happens | On screen | Sound |
|---|---|---|---|---|
| b108 | 64.8 | Cut to the neutral network, completely still | — | **One beat of silence** |
| b109 | 65.4 | Hub turns plum, scales to 1.4, reads "checks itself". Orgs dim to 0.45, edges to 0.25 (site step 7). | Hub: "checks itself" | Resolving D chord |
| b112 | 67.2 | Title sets on the left gutter with the `lineup` mask | "XFed-IDS-*ByzAgent*" (ByzAgent plum italic, as in the site footer) | — |
| b114 | 68.4 | Team names set in a 2 × 2 grid, Schibsted 36. Kicker above. | "V Naga Adithya · T Shaun · P Sampath · D Tharun" / kicker "VIT-AP CAPSTONE · 2026" | Final soft note |
| b116–118 | 69.6–70.8 | Hold, ring-out | — | Decay to silence |

Team names ← `site/src/copy.js · footer.members[*][0]`.

---

## Hero loop (separate composition)

- 1600 × 900, 30 fps, **12.0 s**, silent. No text, no labels, no numbers.
- Neutral network only: ten plain circles at their real relative sizes, edges, sand hub. Plum dots
  travel inward on a 2.4 s cycle, staggered per org. Every 4th cycle a brass wave goes back out.
  The hub breathes (scale ±2%) on a 12 s sine.
- Everything is periodic in 12 s, so the render is frames 0…360 and frame 360 is identical to
  frame 0 (checked with a pixel diff). Encoded as H.264 MP4 and VP9 WebM, CRF tuned to stay
  under 2 MB each.
- The network sits right of centre (centre at 62% of the width) so the site's left-aligned hero
  type stays on cream. Edges and circles at 60% opacity so the type stays readable over it.

## Assets to capture (after approval, before animation)

All with Playwright, 2× DPR desktop (1920 × 1080 viewport) plus 3× DPR mobile (390 × 844) for 9:16:

1. Built site (`npm run build && npm run preview` in `site/`): story section at step 3, explain
   section, trust grid at seed 1337, replay with one alert selected, replay after "Jump to a miss" (#076).
2. React dashboard (`frontend/`) + FastAPI (`backend/`): Alert Stream and Client Trust Monitor.
   If the backend does not start on this machine, S7 uses only the site screenshots. I will
   report that rather than redraw anything.

Saved to `film/public/assets/` with a `captures.json` (URL, viewport, timestamp, git commit).

## Deliverables (unchanged from the brief)

`film/out/xfed_film_16x9.mp4` · `xfed_film_9x16.mp4` · `hero_loop.mp4` / `.webm` · `poster.jpg`
(frame from S5 at b64, the α chart with the note) · `contact.png` · `film/docs/review_log.md` ·
copies to `site/public/film/`.
