import { NavLink } from 'react-router-dom';
import { SECTIONS } from '../sections/registry';

function NavIcon({ d }) {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}

function NavGroup({ items }) {
  return (
    <nav className="xf-nav">
      {items.map((s) => (
        <NavLink
          key={s.key}
          to={s.path}
          className={({ isActive }) => `xf-navitem${isActive ? ' active' : ''}`}
        >
          <NavIcon d={s.icon} />
          <span>{s.navLabel}</span>
        </NavLink>
      ))}
    </nav>
  );
}

function BackendStatus({ status }) {
  if (status.state === 'loading') {
    return (
      <div>
        <span className="xf-status-dot loading" />
        Connecting to backend…
      </div>
    );
  }
  if (status.state === 'error') {
    return (
      <div>
        <span className="xf-status-dot error" />
        Backend unreachable
        <br />
        {status.error}
      </div>
    );
  }
  const { health, config } = status;
  return (
    <div>
      <div>
        <span className={`xf-status-dot ${health.model_loaded ? 'ok' : 'error'}`} />
        <b>{config.tag}</b>
      </div>
      <div>
        α={config.alpha} · seed={config.seed} · round {config.best_round}
      </div>
      <div>
        {config.n_features} features · {config.n_classes} classes
      </div>
    </div>
  );
}

export default function Sidebar({ status }) {
  const sections = SECTIONS.filter((s) => s.group === 'sections');
  const trust = SECTIONS.filter((s) => s.group === 'trust');
  const analyst = SECTIONS.filter((s) => s.group === 'analyst');

  return (
    <aside className="xf-sidebar">
      <div>
        <div className="xf-brand">
          XFed<span>·</span>IDS
        </div>
        <div className="xf-brand-sub">
          Explainable Federated
          <br />
          Intrusion Detection
        </div>

        <div className="xf-navlabel">Sections</div>
        <NavGroup items={sections} />

        <div className="xf-navlabel">Trust check (ByzAgent)</div>
        <NavGroup items={trust} />

        <div className="xf-navlabel">Analyst tools</div>
        <NavGroup items={analyst} />
      </div>

      <div className="xf-sidebar-footer">
        <BackendStatus status={status} />
      </div>
    </aside>
  );
}
