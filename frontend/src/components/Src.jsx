import { sourceUrl } from '../api/client';

// The small link every displayed number carries to the file it was read from.
export default function Src({ path, label }) {
  if (!path) return null;
  const name = label ?? path.split('/').slice(-2).join('/');
  return (
    <a className="src" href={sourceUrl(path)} target="_blank" rel="noopener noreferrer" title={path} aria-label={`${name}, source file ${path}`}>
      {name}
    </a>
  );
}

export function Srcs({ paths }) {
  const unique = [...new Set(paths.filter(Boolean))];
  return (
    <span className="src-list">
      {unique.map((p) => (
        <Src key={p} path={p} />
      ))}
    </span>
  );
}

// One per panel: the panel's source files, folded behind "Sources (n) ▸".
export function Sources({ paths }) {
  const unique = [...new Set(paths.filter(Boolean))];
  if (unique.length === 0) return null;
  return (
    <details className="srcs">
      <summary>Sources ({unique.length})</summary>
      <span className="src-list src-list--col">
        {unique.map((p) => (
          <Src key={p} path={p} label={p} />
        ))}
      </span>
    </details>
  );
}
