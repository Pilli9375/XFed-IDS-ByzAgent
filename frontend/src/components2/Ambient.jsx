// Two blurred radial light pools behind the content. `tone` picks the
// colour layer (ok / attack / agent) and the layers cross-fade (~1.2 s);
// `strength` scales the theme's glow (1.35 for a missed flow). While
// loading, pool A is ok and pool B is agent, both pulsing (the designs'
// loading state).
const TONES = ['ok', 'attack', 'agent'];

export default function Ambient({ tone, strength = 1, bFactor = 0.5, loading }) {
  const a = loading
    ? { '--o1': 'calc(var(--glow) * 0.5)', '--o2': 'var(--glow)' }
    : { opacity: `calc(var(--glow) * ${strength})` };
  const b = loading
    ? { '--o1': 'var(--glow)', '--o2': 'calc(var(--glow) * 0.45)' }
    : { opacity: `calc(var(--glow) * ${strength * bFactor})` };
  return (
    <>
      <div aria-hidden="true" className="v-amb v-amb--a" data-tone={loading ? 'ok' : tone} style={a}>
        {TONES.map((t) => <span key={t} className={`c-${t}`} />)}
      </div>
      <div aria-hidden="true" className="v-amb v-amb--b" data-tone={loading ? 'agent' : tone} style={b}>
        {TONES.map((t) => <span key={t} className={`c-${t}`} />)}
      </div>
    </>
  );
}
