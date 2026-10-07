# XFed-IDS-ByzAgent — explainer film

A 70.8 s data-driven film in Remotion. It reads the site's own data (`../site/public/data/*.json`),
number formatting (`../site/src/format.js`) and copy (`../site/src/copy.js`), so every number on
screen is built from a JSON key at render time. Nothing is typed into a component.

- `docs/style_guide.md`: tokens, type, diagram geometry and motion grammar (from `site/src`)
- `docs/shotlist.md`: beat grid (100 BPM, 18 frames/beat) and the source key for every number
- `docs/review_log.md`: four critique rounds with scores and fixes
- `out/numbers.json`: every on-screen number → file, key path, raw value, displayed text

## Rebuild

```bash
npm ci
npm run fonts      # byte-identical copies of site/public/fonts (SHA-256 checked)
npm run score      # synthesises public/audio/score.wav (-14 LUFS) and out/beats.json
npm run numbers    # writes out/numbers.json
npx remotion render Film16x9 out/xfed_film_16x9.mp4 --crf=18
npx remotion render Film9x16 out/xfed_film_9x16.mp4 --crf=18
npx remotion render HeroLoop out/hero --sequence --image-format=png   # then encode, see review_log.md
```

`npm run capture` re-takes the real-UI screenshots in `public/assets`. It needs `vite preview` of
`site/` on :4180, and the React dashboard on :5173 with the FastAPI backend on :8000. Set
`SKIP_DASH=1` to capture only the site. Never start `backend/simulator.py` for this: it reads the
test set.

## Timeline

`src/timeline.json` is the single timing source for the scenes and the score. Change a beat there
and both the picture and the sound move with it.
