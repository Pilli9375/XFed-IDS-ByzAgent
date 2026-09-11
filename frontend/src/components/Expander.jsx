// Ports theme.py's div[data-testid="stExpander"] frame onto a native
// <details>/<summary> -- there's no Streamlit expander to reach for here.
export default function Expander({ title, children }) {
  return (
    <details className="xf-expander">
      <summary>{title}</summary>
      <div className="xf-expander-body">{children}</div>
    </details>
  );
}
