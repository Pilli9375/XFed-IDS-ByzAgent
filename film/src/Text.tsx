import React from 'react';
import { C, F } from './theme';

// Glyphs none of the self-hosted font files contain. Rendering one would silently fall back to
// a system font, so it is a hard error instead (→ is drawn with <Arrow/>).
const MISSING = /[→←✕✓∝≈]/;

/** Text with Greek letters set in Alegreya italic's Greek subset (the only file that has them). */
export const Tx: React.FC<{ children: string; greekScale?: number }> = ({ children, greekScale = 1.08 }) => {
  if (MISSING.test(children)) throw new Error(`glyph not in the site fonts: ${children}`);
  const parts = children.split(/([ατ])/);
  return (
    <>
      {parts.map((p, i) => (p === 'α' || p === 'τ'
        ? <span key={i} style={{ fontFamily: F.greek, fontStyle: 'italic', fontWeight: 400, fontSize: `${greekScale}em` }}>{p}</span>
        : <React.Fragment key={i}>{p}</React.Fragment>))}
    </>
  );
};

/** Right arrow drawn as a path, sized to the current font. */
export const Arrow: React.FC<{ color?: string }> = ({ color = 'currentColor' }) => (
  <svg viewBox="0 0 24 12" style={{ width: '0.95em', height: '0.5em', margin: '0 0.3em', verticalAlign: '0.12em', overflow: 'visible' }}>
    <path d="M0 6 H21 M16 1 L22 6 L16 11" stroke={color} strokeWidth={1.8} fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

/** Mask reveal (the site's `lineup`): the line rises into a clipping box. p: 0..1 spring. */
export const LineUp: React.FC<{ p: number; children: React.ReactNode; style?: React.CSSProperties }> = ({ p, children, style }) => (
  <span style={{ display: 'block', overflow: 'hidden', paddingBottom: '0.08em', ...style }}>
    <span style={{ display: 'block', transform: `translateY(${(1 - p) * 105}%)` }}>{children}</span>
  </span>
);

export const monoStyle = (size: number, color: string = C.muted): React.CSSProperties => ({
  fontFamily: F.mono, fontSize: size, color, fontVariantNumeric: 'tabular-nums', letterSpacing: '0.02em',
});
