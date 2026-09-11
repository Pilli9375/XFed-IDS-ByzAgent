// Ports theme.py's pills()/pill_html(): a row of tone-colored badges.
// `items` is [text, toneHex][], same tuple shape pills() takes.
function pillStyle(tone) {
  return { color: tone, borderColor: `${tone}55`, background: `${tone}14` };
}

export default function Pills({ items }) {
  return (
    <div>
      {items.map(([text, tone], i) => (
        <span className="xf-pill" style={pillStyle(tone)} key={`${text}-${i}`}>
          {text}
        </span>
      ))}
    </div>
  );
}
