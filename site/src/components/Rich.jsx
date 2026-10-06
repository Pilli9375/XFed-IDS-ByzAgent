// Renders copy segments from copy.js: 'text' | {em: 'text'} | {note: 'text'}.
export default function Rich({ parts, emClass }) {
  return parts.map((p, i) => {
    if (typeof p === 'string') return p;
    if (p.em) return <em key={i} className={emClass}>{p.em}</em>;
    if (p.note) return <em key={i} className="note">{p.note}</em>;
    return null;
  });
}
