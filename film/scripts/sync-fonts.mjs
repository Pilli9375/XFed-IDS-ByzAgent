// Copies the site's self-hosted woff2 files into film/public/fonts and verifies each copy's
// SHA-256 against the site original, so the film uses byte-identical font files.
import { createHash } from 'node:crypto';
import { copyFileSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SRC = path.join(ROOT, '..', 'site', 'public', 'fonts');
const DST = path.join(ROOT, 'public', 'fonts');
export const FONT_FILES = [
  'brygada-1918-latin-400-normal.woff2',
  'brygada-1918-latin-400-italic.woff2',
  'brygada-1918-latin-500-normal.woff2',
  'schibsted-grotesk-latin-400-normal.woff2',
  'schibsted-grotesk-latin-500-normal.woff2',
  'atkinson-hyperlegible-mono-latin-300-normal.woff2',
  'atkinson-hyperlegible-mono-latin-400-normal.woff2',
  'alegreya-latin-400-italic.woff2',
  'alegreya-greek-400-italic.woff2',
];
const sha = (p) => createHash('sha256').update(readFileSync(p)).digest('hex');
for (const f of FONT_FILES) {
  copyFileSync(path.join(SRC, f), path.join(DST, f));
  const a = sha(path.join(SRC, f));
  const b = sha(path.join(DST, f));
  if (a !== b) throw new Error(`hash mismatch for ${f}`);
  console.log(f, a.slice(0, 12));
}
