import { useRef } from 'react';
import { useInView } from '../motion.js';

// Fades and lifts its content in the first time it scrolls into view (.rv -> .rv.in).
export default function Reveal({ as: Tag = 'div', className = '', style, children, threshold = 0.18, rootMargin, ...rest }) {
  const ref = useRef(null);
  const inView = useInView(ref, { threshold, rootMargin });
  return (
    <Tag ref={ref} className={`rv${inView ? ' in' : ''} ${className}`} style={style} {...rest}>
      {children}
    </Tag>
  );
}
