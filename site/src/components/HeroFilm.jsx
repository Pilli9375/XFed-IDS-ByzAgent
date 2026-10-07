import { useEffect, useRef } from 'react';
import { useReducedMotion } from '../motion.js';

const SOURCES = [
  ['/film/hero_loop.webm', 'video/webm'],
  ['/film/hero_loop.mp4', 'video/mp4'],
];

// Decorative loop behind the hero headline. The poster (frame 0 of the loop) is the first paint;
// the video sources are attached only once the loader has gone and the browser is idle, it plays
// only while the hero is on screen, and under reduced motion it is never attached (poster only).
export default function HeroFilm({ start }) {
  const ref = useRef(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    const v = ref.current;
    if (!v || !start || reduced) return undefined;
    let io = null;
    const attach = () => {
      if (!v.querySelector('source')) {
        SOURCES.forEach(([src, type]) => {
          const s = document.createElement('source');
          s.src = src;
          s.type = type;
          v.appendChild(s);
        });
        v.muted = true;
        v.load();
      }
      io = new IntersectionObserver(([e]) => {
        if (e.isIntersecting) v.play().catch(() => {});
        else v.pause();
      }, { threshold: 0 });
      io.observe(v.closest('.hero') || v);
    };
    const ric = window.requestIdleCallback || ((f) => setTimeout(f, 200));
    const cic = window.cancelIdleCallback || clearTimeout;
    const id = ric(attach, { timeout: 1500 });
    return () => {
      cic(id);
      if (io) io.disconnect();
      v.pause();
    };
  }, [start, reduced]);

  return (
    <div className="hero-film" aria-hidden="true">
      <video
        ref={ref}
        muted
        loop
        playsInline
        preload="none"
        poster="/film/hero_poster.webp"
        disablePictureInPicture
        tabIndex={-1}
      />
      <div className="hero-scrim" />
    </div>
  );
}
