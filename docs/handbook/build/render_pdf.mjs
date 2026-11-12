// Render docs/handbook/XFed_Team_Handbook.html to PDF with the Playwright
// Chromium already installed for film/ (film/node_modules/playwright).
//   node docs/handbook/build/render_pdf.mjs [--pages out_dir 1,2,10]
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const hb = path.resolve(here, '..');
const repo = path.resolve(hb, '..', '..');
const require = createRequire(path.join(repo, 'film', 'package.json'));
const { chromium } = require('playwright');

const html = path.join(hb, 'XFed_Team_Handbook.html');
const pdf = path.join(hb, 'XFed_Team_Handbook.pdf');

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(pathToFileURL(html).href, { waitUntil: 'load' });
await page.emulateMedia({ media: 'print' });
const small = 'font-size:7.5pt;font-family:Segoe UI,Arial,sans-serif;color:#6b7280;width:100%;padding:0 18mm;box-sizing:border-box;';
await page.pdf({
  path: pdf,
  format: 'A4',
  printBackground: true,
  displayHeaderFooter: true,
  headerTemplate: `<div style="${small}text-align:right;">XFed-IDS-ByzAgent Team Handbook</div>`,
  footerTemplate: `<div style="${small}text-align:center;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>`,
  preferCSSPageSize: true,
  outline: true,
  tagged: true,
});
await browser.close();
console.log('wrote', pdf);
