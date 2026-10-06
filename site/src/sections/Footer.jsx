import { footer } from '../copy.js';
import { REPO } from '../sources.js';
import Rich from '../components/Rich.jsx';

export default function Footer() {
  return (
    <footer className="foot">
      <div>
        <p className="kicker mono">{footer.team}</p>
        <div className="team">
          {footer.members.map(([name, reg]) => (
            <div key={reg} style={{ display: 'contents' }}>
              <span>{name}</span>
              <span className="mono">{reg}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="foot-r">
        <p className="name disp"><Rich parts={footer.name} /></p>
        <p>{footer.data}</p>
        <p style={{ marginTop: 12 }}><a href={REPO} target="_blank" rel="noopener noreferrer">{footer.code}</a></p>
      </div>
    </footer>
  );
}
