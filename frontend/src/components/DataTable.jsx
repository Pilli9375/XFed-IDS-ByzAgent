// Ports the div[data-testid="stDataFrame"] frame from theme.py's CSS onto a
// plain HTML table -- there's no st.dataframe equivalent to reach for here.
export default function DataTable({ columns, rows, getRowKey }) {
  return (
    <div className="xf-table-wrap">
      <table className="xf-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={getRowKey ? getRowKey(row, i) : i}>
              {columns.map((c) => (
                <td key={c.key}>{c.render ? c.render(row) : row[c.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
