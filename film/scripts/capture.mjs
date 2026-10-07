// Real-UI captures for the film (Playwright). Nothing is restyled or edited: pages are
// screenshotted as served, and only cropped by clip rectangles.
//   site:      built site via `vite preview` on :4180
//   dashboard: React dashboard (vite dev) on :5173 talking to the FastAPI backend on :8000.
//              The alert simulator is NOT run (it reads test_global.parquet); only sections
//              that need no simulator are captured.
import { chromium } from 'playwright';
import { execSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, 'public', 'assets');
mkdirSync(OUT, { recursive: true });

const SITE = process.env.SITE_URL ?? 'http://localhost:4180';
const DASH = process.env.DASH_URL ?? 'http://localhost:5173';
const commit = execSync('git rev-parse --short HEAD', { cwd: ROOT }).toString().trim();
const log = [];

const browser = await chromium.launch();

async function ctx(kind, opts = {}) {
  const viewport = kind === 'mobile' ? { width: 390, height: 844 } : { width: 1920, height: 1080 };
  const deviceScaleFactor = kind === 'mobile' ? 3 : 2;
  return browser.newContext({ viewport, deviceScaleFactor, ...opts });
}

async function shot(page, file, clip, meta) {
  await page.screenshot({ path: path.join(OUT, file), clip, animations: 'disabled' });
  log.push({ file, url: page.url(), clip, captured_at: new Date().toISOString(), git_commit: commit, ...meta });
  console.log('captured', file);
}

// Union rectangle (page coordinates) of two elements, padded.
async function union(page, selA, selB, pad = 0) {
  return page.evaluate(([a, b, p]) => {
    const ra = document.querySelector(a).getBoundingClientRect();
    const rb = document.querySelector(b).getBoundingClientRect();
    const x = Math.min(ra.left, rb.left) - p;
    const y = Math.min(ra.top, rb.top) - p;
    return { x, y, width: Math.max(ra.right, rb.right) - x + p, height: Math.max(ra.bottom, rb.bottom) - y + p };
  }, [selA, selB, pad]);
}

// ---------------------------------------------------------------- site: story
for (const kind of ['desktop', 'mobile']) {
  const c = await ctx(kind);
  const page = await c.newPage();
  await page.goto(SITE, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(2500); // loader slides away
  if (kind === 'desktop') {
    // Pinned story: scroll into the middle of step 6 (orgs 0, 3, 5 poisoned, agent card).
    const top = await page.evaluate(() => document.querySelector('#story').getBoundingClientRect().top + window.scrollY);
    const y = top + 1080 * 3.5 * (5.5 / 7);
    await page.mouse.wheel(0, 0);
    await page.evaluate((yy) => window.scrollTo(0, yy), y);
    await page.waitForTimeout(2200);
    await shot(page, 'site_story_desktop.png', undefined, { section: 'story (pinned, step 6)', viewport: '1920x1080@2x' });
  } else {
    await page.evaluate(() => document.querySelector('#story .story-list > li:nth-child(3)').scrollIntoView({ block: 'start' }));
    await page.waitForTimeout(1800);
    await shot(page, 'site_story_mobile.png', undefined, { section: 'story list, step 3', viewport: '390x844@3x' });
  }
  await c.close();
}

// ---------------------------------------------------------------- site: replay
for (const kind of ['desktop', 'mobile']) {
  // reduced motion: reveal transitions off, so the frame is settled when captured (stream still runs)
  const c = await ctx(kind, { reducedMotion: 'reduce' });
  const page = await c.newPage();
  await page.goto(SITE, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => document.querySelector('#replay .rp-body').scrollIntoView({ block: 'center' }));
  // the stream starts at seq 0; pause on it
  const pause = page.locator('.rp-btn.solid');
  await pause.waitFor();
  await pause.click();
  await page.waitForTimeout(600);
  const head0 = await page.locator('.rp-why .h').innerText();
  if (!head0.includes('#000')) throw new Error(`expected alert #000 after pause, got: ${head0}`);
  // alert #000: feed + SHAP panel, clipped above the analyst note. Clip rects are viewport
  // coordinates; the region is scrolled to 140 px from the top so the sticky nav never overlaps.
  const topSel = kind === 'desktop' ? '.rp-feed' : '.rp-why .h';
  await page.evaluate((sel) => window.scrollBy(0, document.querySelector(sel).getBoundingClientRect().top - 140), topSel);
  await page.waitForTimeout(300);
  const a2 = kind === 'desktop'
    ? await union(page, '.rp-feed', '.rp-why .shap-dir', 0)
    : await union(page, '.rp-why .h', '.rp-why .shap-dir', 16);
  if (kind === 'desktop') {
    const noteTop = await page.evaluate(() => document.querySelector('.rp-why .rp-note').getBoundingClientRect().top);
    a2.height = Math.min(a2.height, noteTop - a2.y - 4);
  }
  await shot(page, `site_replay_000_${kind}.png`, a2, { section: 'replay, alert #000 paused', alert_seq: 0 });
  if (kind === 'mobile') {
    // the feed's button bar + counts (mobile stacks the feed above the panel)
    await page.evaluate(() => window.scrollBy(0, document.querySelector('.rp-feed').getBoundingClientRect().top - 140));
    await page.waitForTimeout(300);
    const bar = await union(page, '.rp-feed .rp-bar', '.rp-feed .rp-counts', 12);
    await shot(page, 'site_replay_bar_mobile.png', bar, { section: 'replay feed controls, paused on #000' });
    const btn = await page.locator('.rp-btn.line').boundingBox();
    log[log.length - 1].jump_button_in_clip = { x: btn.x - bar.x, y: btn.y - bar.y, width: btn.width, height: btn.height };
  }

  if (kind === 'desktop') {
    // the button itself, for the annotation ring position (page coords relative to clip)
    const btn = await page.locator('.rp-btn.line').boundingBox();
    log[log.length - 1].jump_button_in_clip = { x: btn.x - a2.x, y: btn.y - a2.y, width: btn.width, height: btn.height };
  }

  // Jump to a miss -> #076; crop to the SHAP panel + verdict only
  if (kind === 'mobile') {
    await page.locator('.rp-btn.line').scrollIntoViewIfNeeded();
  }
  await page.locator('.rp-btn.line').click();
  await page.waitForTimeout(600);
  const head = await page.locator('.rp-why .h').innerText();
  if (!head.includes('#076')) throw new Error(`expected #076 after Jump to a miss, got: ${head}`);
  await page.evaluate(() => window.scrollBy(0, document.querySelector('.rp-why').getBoundingClientRect().top - 140));
  await page.waitForTimeout(300);
  const b = await union(page, '.rp-why .h', '.rp-why .shap-dir', 24);
  await shot(page, `site_replay_076_${kind}.png`, b, { section: 'replay after "Jump to a miss", #076, SHAP panel + verdict (analyst note excluded)', alert_seq: 76 });
  await c.close();
}

// ---------------------------------------------------------------- dashboard
if (!process.env.SKIP_DASH) {
  const c = await ctx('desktop');
  const page = await c.newPage();
  await page.goto(`${DASH}/client-trust-monitor`, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(2500);
  await shot(page, 'dashboard_trust_desktop.png', undefined, { section: 'React dashboard, Client Trust Monitor (live FastAPI /trust)', viewport: '1920x1080@2x' });
  // same page scrolled to the per-round decision grids
  await page.getByText('Per-round decisions', { exact: true }).evaluate((el) => window.scrollBy(0, el.getBoundingClientRect().top - 40));
  await page.waitForTimeout(1200);
  await shot(page, 'dashboard_trust_grid_desktop.png', undefined, { section: 'React dashboard, Client Trust Monitor, per-round decision grids', viewport: '1920x1080@2x' });
  await c.close();
}

await browser.close();
// keep earlier dashboard entries when only the site was re-captured
let prev = [];
try { prev = JSON.parse(readFileSync(path.join(OUT, 'captures.json'), 'utf8')); } catch { /* first run */ }
const merged = [...prev.filter((p) => !log.some((l) => l.file === p.file)), ...log];
writeFileSync(path.join(OUT, 'captures.json'), JSON.stringify(merged, null, 2));
console.log('wrote captures.json');
