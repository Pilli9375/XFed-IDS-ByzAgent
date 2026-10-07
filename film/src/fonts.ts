// Only the self-hosted site fonts (copied byte-identical by scripts/sync-fonts.mjs).
import { loadFont } from '@remotion/fonts';
import { staticFile } from 'remotion';

const f = (family: string, file: string, weight: string, style: 'normal' | 'italic' = 'normal') =>
  loadFont({ family, url: staticFile(`fonts/${file}`), weight, style, display: 'block' });

export const fontsReady = Promise.all([
  f('Brygada 1918', 'brygada-1918-latin-400-normal.woff2', '400'),
  f('Brygada 1918', 'brygada-1918-latin-400-italic.woff2', '400', 'italic'),
  f('Brygada 1918', 'brygada-1918-latin-500-normal.woff2', '500'),
  f('Schibsted Grotesk', 'schibsted-grotesk-latin-400-normal.woff2', '400'),
  f('Schibsted Grotesk', 'schibsted-grotesk-latin-500-normal.woff2', '500'),
  f('Atkinson Hyperlegible Mono', 'atkinson-hyperlegible-mono-latin-300-normal.woff2', '300'),
  f('Atkinson Hyperlegible Mono', 'atkinson-hyperlegible-mono-latin-400-normal.woff2', '400'),
  f('Alegreya', 'alegreya-latin-400-italic.woff2', '400', 'italic'),
  // Greek subset under its own family: only α and τ use it (see Text.tsx)
  f('Alegreya Greek', 'alegreya-greek-400-italic.woff2', '400', 'italic'),
]);
