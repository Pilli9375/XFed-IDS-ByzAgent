import { source } from '../copy.js';

// Small "source" link to the file behind a displayed number (opens GitHub).
export default function Src({ href, children = source, className = 'src', label }) {
  return (
    <a className={className} href={href} target="_blank" rel="noopener noreferrer" aria-label={label}>
      {children}
    </a>
  );
}
