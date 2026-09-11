// Ports theme.py's subhead(): a smaller in-section heading than
// SectionHeader's h1, with the same optional lede treatment.
export default function Subhead({ title, lede = '' }) {
  return (
    <div>
      <div className="xf-subhead">{title}</div>
      {lede && <div className="xf-lede" dangerouslySetInnerHTML={{ __html: lede }} />}
    </div>
  );
}
