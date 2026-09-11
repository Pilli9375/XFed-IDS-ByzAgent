import { ACCENT, TEXT } from '../theme/tokens';

// Ports theme.py's callout(): tone + '44' border, tone + '0f' background --
// the same hex-alpha-suffix trick, just spelled out in JS instead of an
// f-string.
export default function Callout({ tone = ACCENT, children }) {
  const style = {
    color: TEXT,
    borderColor: `${tone}44`,
    borderLeftColor: tone,
    background: `${tone}0f`,
  };
  return (
    <div className="xf-callout" style={style}>
      {children}
    </div>
  );
}
