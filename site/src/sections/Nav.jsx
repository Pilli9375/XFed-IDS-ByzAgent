import { nav } from '../copy.js';

export default function Nav() {
  return (
    <header className="site-header">
      <nav className="site-nav" aria-label={nav.label}>
        <a className="brand disp" href="#top">{nav.brand}</a>
        <div className="links">
          {nav.links.map(([id, label]) => <a key={id} href={`#${id}`}>{label}</a>)}
        </div>
        <a className="nav-cta btn" href="#replay">{nav.cta} <span className="arr" aria-hidden="true">→</span></a>
      </nav>
    </header>
  );
}
