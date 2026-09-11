// Ports theme.py's section_header(): eyebrow + title + optional lede.
// lede strings are hardcoded content authored in sections/registry.js (a
// direct port of app_lib/sections.py's own text), carrying <code>/<b>/<i>
// tags exactly as the Python source emits via st.markdown(unsafe_allow_html=True).
export default function SectionHeader({ eyebrow, title, lede }) {
  return (
    <div>
      <div className="xf-eyebrow">{eyebrow}</div>
      <h1>{title}</h1>
      {lede && <div className="xf-lede" dangerouslySetInnerHTML={{ __html: lede }} />}
    </div>
  );
}
