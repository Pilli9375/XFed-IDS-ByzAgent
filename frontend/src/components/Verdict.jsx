// Ports theme.py's verdict(): the big prediction readout block. `meta` is
// a small HTML string built by the caller (bold spans around known,
// trusted values -- confidence %, tier, family names from the fixed
// 9-class vocabulary), same trusted-content posture as SectionHeader's lede.
export default function Verdict({ name, meta, tone }) {
  return (
    <div className="xf-verdict" style={{ '--tone': tone }}>
      <div className="xf-verdict-name">{name}</div>
      <div className="xf-verdict-meta" dangerouslySetInnerHTML={{ __html: meta }} />
    </div>
  );
}
