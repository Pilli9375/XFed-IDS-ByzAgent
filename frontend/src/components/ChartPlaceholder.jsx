// Not a theme.py port -- a new, neutral "not built yet" box, visually
// distinct from Callout (which mirrors Streamlit's warning/info semantics)
// so a chart that's actively being added doesn't read as a data problem.
export default function ChartPlaceholder({ title, children }) {
  return (
    <div className="xf-placeholder">
      <div className="xf-placeholder-title">{title}</div>
      <div>{children}</div>
    </div>
  );
}
