import { ACCENT } from '../theme/tokens';

// Ports theme.py's stat(): custom metric card with an accent bar, used
// instead of a plain number because it gives control over tone/sizing.
export default function Stat({ label, value, sub = '', tone = ACCENT, small = false }) {
  return (
    <div className="xf-stat" style={{ '--tone': tone }}>
      <div className="xf-stat-label">{label}</div>
      <div className={`xf-stat-value${small ? ' sm' : ''}`}>{value}</div>
      {sub && <div className="xf-stat-sub">{sub}</div>}
    </div>
  );
}
