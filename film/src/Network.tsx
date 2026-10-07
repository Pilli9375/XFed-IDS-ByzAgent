// The N—00 network (orgs, edges, hub, pies, update dots), drawn from the site's geometry.
// Stateless: every visual property arrives as a prop computed from the current frame.
import React from 'react';
import { C, F, PIE } from './theme';
import { Fmt, geometry } from './layout';
import { RAW } from './data';
import { Tx } from './Text';

export type OrgState = { scale: number; fill: string; stroke: string; opacity: number; dy: number; pie: number; pieOpacity: number };
export type Label = { name: string; value?: string; valueColor?: string; nameColor?: string; opacity: number; dy?: number };
export type Dot = { org: number; p: number; color: string; inward: boolean; opacity: number };

export const neutralOrg = (scale = 1): OrgState => ({ scale, fill: C.cream, stroke: C.cocoa, opacity: 1, dy: 0, pie: 0, pieOpacity: 0 });

type Props = {
  fmt: Fmt | 'hero';
  orgs: OrgState[];
  labels?: Label[];
  edge: number[];
  edgeOpacity?: number;
  hub: { scale: number; fill: string; stroke: string; text?: string; color?: string };
  dots?: Dot[];
  halo?: { org: number; opacity: number; scale: number } | null;
  camera?: { scale: number; fx: number; fy: number };
  width: number;
  height: number;
};

function arc(cx: number, cy: number, r: number, a0: number, a1: number) {
  // angles in degrees, 0 = 12 o'clock, clockwise (conic-gradient convention)
  if (a1 - a0 >= 359.999) return `M ${cx} ${cy - r} A ${r} ${r} 0 1 1 ${cx - 0.001} ${cy - r} Z`;
  const p = (a: number) => [cx + r * Math.sin((a * Math.PI) / 180), cy - r * Math.cos((a * Math.PI) / 180)];
  const [x0, y0] = p(a0); const [x1, y1] = p(a1);
  return `M ${cx} ${cy} L ${x0} ${y0} A ${r} ${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1} ${y1} Z`;
}

export const Network: React.FC<Props> = ({ fmt, orgs, labels, edge, edgeOpacity = 0.5, hub, dots = [], halo, camera, width, height }) => {
  const g = geometry(fmt);
  const sw = fmt === 'hero' ? 2 : fmt === 'tall' ? 2.6 : 2.2; // site 1.5 px at the site's scale
  const nameSize = fmt === 'tall' ? 34 : 28;
  const valueSize = fmt === 'tall' ? 40 : 34;
  const hubSize = fmt === 'tall' ? 30 : 26;
  const cam = camera ?? { scale: 1, fx: g.hub.x, fy: g.hub.y };
  const dotR = fmt === 'hero' ? 6 : fmt === 'tall' ? 10 : 8;

  return (
    <div style={{ position: 'absolute', inset: 0, transformOrigin: `${cam.fx}px ${cam.fy}px`, transform: `scale(${cam.scale})` }}>
      <svg width={width} height={height} style={{ position: 'absolute', inset: 0 }}>
        {g.orgs.map((o, i) => {
          const st = orgs[i];
          const r = o.r * st.scale;
          const x0 = o.x + o.ux * o.r; const y0 = o.y + o.uy * o.r + st.dy;
          const x1 = g.hub.x - o.ux * g.hub.r; const y1 = g.hub.y - o.uy * g.hub.r;
          const p = edge[i];
          if (p <= 0 || r <= 0) return null;
          return <line key={`e${i}`} x1={x0} y1={y0} x2={x0 + (x1 - x0) * p} y2={y0 + (y1 - y0) * p} stroke={C.cocoa} strokeWidth={sw} opacity={edgeOpacity} />;
        })}

        {dots.map((d, k) => {
          const o = g.orgs[d.org];
          const ax = o.x + o.ux * o.r; const ay = o.y + o.uy * o.r;
          const bx = g.hub.x - o.ux * g.hub.r; const by = g.hub.y - o.uy * g.hub.r;
          const p = d.inward ? d.p : 1 - d.p;
          return <circle key={`d${k}`} cx={ax + (bx - ax) * p} cy={ay + (by - ay) * p} r={dotR} fill={d.color} opacity={d.opacity} />;
        })}

        {halo && halo.opacity > 0 && (() => {
          const o = g.orgs[halo.org];
          const pad = fmt === 'tall' ? 22 : 18;
          return <circle cx={o.x} cy={o.y + orgs[halo.org].dy} r={(o.r + pad) * halo.scale} fill="none" stroke={C.brass} strokeWidth={3} opacity={halo.opacity} />;
        })()}

        {g.orgs.map((o, i) => {
          const st = orgs[i];
          const r = o.r * st.scale;
          if (r <= 0.01) return null;
          const cy = o.y + st.dy;
          let acc = 0;
          const total = RAW.comp[i].total;
          return (
            <g key={`o${i}`} opacity={st.opacity}>
              <circle cx={o.x} cy={cy} r={r} fill={st.fill} />
              {st.pieOpacity > 0 && st.pie > 0 && (
                <g opacity={st.pieOpacity}>
                  {RAW.comp[i].slices.map((v, s) => {
                    const a0 = acc; acc += (v / total) * 360;
                    const lim = st.pie * 360;
                    if (v === 0 || a0 >= lim) return null;
                    return <path key={s} d={arc(o.x, cy, r, a0, Math.min(acc, lim))} fill={PIE[s]} />;
                  })}
                </g>
              )}
              <circle cx={o.x} cy={cy} r={r} fill="none" stroke={st.stroke} strokeWidth={sw} />
            </g>
          );
        })}

        {hub.scale > 0 && (
          <circle cx={g.hub.x} cy={g.hub.y} r={g.hub.r * hub.scale} fill={hub.fill} stroke={hub.stroke} strokeWidth={sw} />
        )}
      </svg>

      {hub.text && hub.scale > 0.6 && (
        <div style={{
          position: 'absolute', left: g.hub.x - 150, top: g.hub.y - 60, width: 300, height: 120,
          display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center',
          fontFamily: F.mono, fontSize: hubSize * Math.min(1.25, hub.scale), lineHeight: 1.25, whiteSpace: 'pre', color: hub.color,
        }}>{hub.text}</div>
      )}

      {labels && g.orgs.map((o, i) => {
        const L = labels[i];
        if (!L || L.opacity <= 0) return null;
        const st = orgs[i];
        const lines = L.value ? 2 : 1;
        const h = nameSize * 1.2 + (lines > 1 ? valueSize * 1.15 : 0);
        const w = Math.max(L.name.length * nameSize * 0.62, (L.value?.length ?? 0) * valueSize * 0.62);
        const ext = (h / 2) * Math.abs(o.uy) + (w / 2) * Math.abs(o.ux);
        const d = o.r * Math.max(st.scale, 0.001) + (fmt === 'tall' ? 16 : 12) + ext;
        const cx = o.x - o.ux * d;
        const cy = o.y - o.uy * d + st.dy + (L.dy ?? 0);
        return (
          <div key={`l${i}`} style={{
            position: 'absolute', left: cx - 200, top: cy - h / 2, width: 400, textAlign: 'center',
            opacity: L.opacity, fontFamily: F.mono, fontVariantNumeric: 'tabular-nums', lineHeight: 1.2,
          }}>
            <div style={{ fontSize: nameSize, color: L.nameColor ?? C.muted }}><Tx>{L.name}</Tx></div>
            {L.value && <div style={{ fontSize: valueSize, color: L.valueColor ?? C.cocoa, lineHeight: 1.15 }}><Tx>{L.value}</Tx></div>}
          </div>
        );
      })}
    </div>
  );
};
