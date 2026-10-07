import React from 'react';
import { AbsoluteFill } from 'remotion';
import { C, F } from './theme';
import { Fmt, FRAME } from './layout';
import { Tx } from './Text';
import { COPY } from './data';
import { neutralOrg, OrgState, Label } from './Network';

export const Bg: React.FC<{ color: string }> = ({ color }) => <AbsoluteFill style={{ background: color }} />;

/** Text column: left of the diagram (wide) or a block at `slot` (tall). */
export const Col: React.FC<{ fmt: Fmt; slot?: 'top' | 'bottom'; children: React.ReactNode; top?: number; style?: React.CSSProperties }> = ({ fmt, slot = 'top', children, top, style }) => {
  const fr = FRAME[fmt];
  const pos: React.CSSProperties = fmt === 'wide'
    ? { left: fr.gx, top: top ?? 150, width: 560 }
    : slot === 'top'
      ? { left: fr.gx, top: top ?? fr.top, width: fr.W - 2 * fr.gx }
      : { left: fr.gx, top: top ?? 1505, width: fr.W - 2 * fr.gx };
  return <div style={{ position: 'absolute', ...pos, ...style }}>{children}</div>;
};

export const sizes = (fmt: Fmt) => ({
  title: fmt === 'wide' ? 66 : 76,
  body: fmt === 'wide' ? 34 : 38,
  note: fmt === 'wide' ? 40 : 44,
  tag: fmt === 'wide' ? 28 : 32,
  big: fmt === 'wide' ? 220 : 200,
});

export const Title: React.FC<{ fmt: Fmt; children: React.ReactNode; color?: string; style?: React.CSSProperties }> = ({ fmt, children, color = C.cocoa, style }) => (
  <div style={{ fontFamily: F.disp, fontWeight: 400, fontSize: sizes(fmt).title, lineHeight: 1.02, letterSpacing: '-0.02em', color, ...style }}>{children}</div>
);

export const Body: React.FC<{ fmt: Fmt; children: string; color?: string; style?: React.CSSProperties; show?: number }> = ({ fmt, children, color = C.inkSoft, style, show = 1 }) => (
  <p style={{ margin: 0, fontFamily: F.body, fontSize: sizes(fmt).body, lineHeight: 1.42, color, opacity: show, ...style }}><Tx>{children}</Tx></p>
);

export const Note: React.FC<{ fmt: Fmt; children: React.ReactNode; color?: string; style?: React.CSSProperties }> = ({ fmt, children, color = C.muted, style }) => (
  <p style={{ margin: 0, fontFamily: F.note, fontStyle: 'italic', fontSize: sizes(fmt).note, lineHeight: 1.3, color, ...style }}>{children}</p>
);

export const Tag: React.FC<{ fmt: Fmt; children: string; color?: string; style?: React.CSSProperties; show?: number }> = ({ fmt, children, color = C.muted, style, show = 1 }) => (
  <div style={{ fontFamily: F.mono, fontSize: sizes(fmt).tag, letterSpacing: '0.04em', color, opacity: show, fontVariantNumeric: 'tabular-nums', ...style }}><Tx>{children.replace(/ · /g, '\u00A0· ').replace(/ = /g, '\u00A0=\u00A0')}</Tx></div>
);

/** Cocoa panel sliding up over the frame (the site loader's motion, reversed). p: 0..1. */
export const Wipe: React.FC<{ p: number; color: string }> = ({ p, color }) => (
  p <= 0 ? null : <AbsoluteFill style={{ background: color, transform: `translateY(${(1 - p) * 100}%)` }} />
);

/** The settled network every chapter returns to: neutral orgs, edges drawn, hub "shared model". */
export const settled = () => ({
  orgs: Array.from({ length: 10 }, () => neutralOrg(1)) as OrgState[],
  labels: Array.from({ length: 10 }, (_, i) => ({ name: COPY.story.org(i) as string, opacity: 1 })) as Label[],
  edge: Array(10).fill(1) as number[],
  hub: { scale: 1, fill: C.sand, stroke: C.plum, text: COPY.story.hub.shared as string, color: C.plum },
});
