import { useState } from 'react';

// Ports button[data-baseweb="tab"] / div[data-baseweb="tab-highlight"] from
// theme.py's CSS onto a plain button row -- there's no st.tabs() to reach
// for here. `items`: [{ label, content }].
export default function Tabs({ items }) {
  const [active, setActive] = useState(0);
  return (
    <div>
      <div className="xf-tabs" role="tablist">
        {items.map((it, i) => (
          <button
            key={it.label}
            type="button"
            role="tab"
            aria-selected={i === active}
            className={`xf-tab${i === active ? ' active' : ''}`}
            onClick={() => setActive(i)}
          >
            {it.label}
          </button>
        ))}
      </div>
      <div className="xf-tab-panel">{items[active].content}</div>
    </div>
  );
}
