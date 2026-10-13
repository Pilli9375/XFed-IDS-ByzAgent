import { int } from '../../lib/format';

const ROWS = [82, 64, 90, 58, 76, 70, 88, 52, 66, 80];
const BARS = [78, 62, 50, 44, 38, 34, 30, 22, 18];

// Loading bloom from live_console.dc.html: shimmer placeholders, panel
// borders breathing in sequence (0 / .2 / .4 / .6 s).
export default function LiveSkeleton({ nValRows }) {
  const msg =
    nValRows != null
      ? `Verifying the served model against ${int(nValRows)} validation rows…`
      : 'Verifying the served model against the validation split…';
  return (
    <div aria-busy="true" aria-label="Loading the console" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: 14 }}>
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="bloom g-ok" style={{ gap: 10 }}>
            <div className="shim" style={{ height: 10, width: 60 }} />
            <div className="shim" style={{ height: 28, width: '70%' }} />
            <div className="shim" style={{ height: 12, width: '45%' }} />
          </div>
        ))}
      </div>
      <div className="v-row">
        <div className="bloom g-ok p-stream" style={{ animationDelay: '.2s' }}>
          <div className="shim" style={{ height: 12, width: '45%' }} />
          {ROWS.map((w, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <div className="shim" style={{ width: 8, height: 8, flex: 'none' }} />
              <div className="shim" style={{ height: 12, flex: '1 1 auto', maxWidth: `${w}%` }} />
            </div>
          ))}
        </div>
        <div className="bloom g-agent p-why" style={{ animationDelay: '.4s' }}>
          <div style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
            <div className="sk-ring shim" />
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div className="shim" style={{ height: 10, width: 60 }} />
              <div className="shim" style={{ height: 26, width: '40%' }} />
            </div>
          </div>
          <div className="shim" style={{ height: 14 }} />
          <div className="shim" style={{ height: 14 }} />
          <div className="shim" style={{ height: 12, width: '45%' }} />
          {BARS.map((w, i) => (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: 'minmax(60px, 190px) minmax(0,1fr)', gap: 14 }}>
              <div className="shim" style={{ height: 10, width: 60 }} />
              <div className="shim" style={{ height: 12, width: `${w}%` }} />
            </div>
          ))}
        </div>
        <div className="bloom g-attack p-trust" style={{ animationDelay: '.6s' }}>
          <div className="shim" style={{ height: 12, width: '45%' }} />
          {ROWS.map((_, i) => (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '48px minmax(0,1fr) 36px', gap: 10, alignItems: 'center' }}>
              <div className="shim" style={{ height: 10 }} />
              <div className="shim" style={{ height: 6 }} />
              <div className="shim" style={{ height: 10 }} />
            </div>
          ))}
        </div>
      </div>
      <p className="foot" role="status">{msg}</p>
    </div>
  );
}
