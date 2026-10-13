import { NavLink } from 'react-router-dom';
import { THEMES, useTheme } from '../hooks/useTheme';

const SWATCH = {
  'deep-sea': ['#5FD4B4', '#061316'],
  aubergine: ['#B8E986', '#120B17'],
  porcelain: ['#2448E8', '#EEF1F5'],
};

export default function Header({ children }) {
  const { theme, setTheme } = useTheme();
  return (
    <header className="v-header">
      <NavLink to="/" className="v-brand" aria-label="XFed-IDS, live console">
        <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
          <rect x="1" y="1" width="20" height="20" rx="5" fill="none" stroke="var(--ok)" strokeWidth="1.5" />
          <path d="M6 6l10 10M16 6L6 16" stroke="var(--ink)" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        <span>XFed-IDS</span>
      </NavLink>
      <nav aria-label="Views" className="v-seg">
        <NavLink to="/" end>Live</NavLink>
        <NavLink to="/investigate">Investigate</NavLink>
        <NavLink to="/limits">Limits</NavLink>
      </nav>
      <div className="v-spacer" />
      <div role="group" aria-label="Theme" className="v-seg v-seg--theme">
        {THEMES.map((t) => (
          <button key={t.id} type="button" aria-pressed={theme === t.id} onClick={() => setTheme(t.id)}>
            <span className="v-swatch" style={{ background: SWATCH[t.id][1], boxShadow: `inset 0 0 0 3px ${SWATCH[t.id][0]}` }} />
            {t.label}
          </button>
        ))}
      </div>
      {children}
    </header>
  );
}
