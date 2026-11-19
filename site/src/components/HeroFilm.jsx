import { useEffect, useRef } from 'react';
import { useReducedMotion } from '../motion.js';

const POSTER = '/film/hero_poster.webp';
const SOURCES = [
  ['/film/hero_loop.webm', 'video/webm'],
  ['/film/hero_loop.mp4', 'video/mp4'],
];

// Decorative loop behind the hero headline, drawn into a <canvas>.
// Why a canvas: a <video> (its poster and its first frame) counts as a Largest Contentful Paint
// candidate, and this box is larger than the headline, so the decoration would take over LCP.
// A canvas is not a candidate and stays out of the accessibility tree, which is what decoration
// should be. The poster (frame 0 of the loop) is drawn as soon as it decodes; the video, kept
// out of the DOM, is only created after the loader has gone and the browser is idle, plays only
// while the hero is on screen, and is never created under reduced motion (poster only).
export default function HeroFilm({ start }) {
  const ref = useRef(null);
  const src = useRef(null); // whatever was drawn last (poster image or video), for redraws on resize
  const reduced = useReducedMotion();

  // canvas sizing + poster
  useEffect(() => {
    const cv = ref.current;
    const ctx = cv.getContext('2d');
    const draw = (s) => {
      if (!s) return;
      src.current = s;
      ctx.drawImage(s, 0, 0, cv.width, cv.height); // box and sources are all 16:9
    };
    cv.drawFrame = draw;
    const size = () => {
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const w = Math.round(cv.clientWidth * dpr);
      const h = Math.round(cv.clientHeight * dpr);
      if (w && h && (w !== cv.width || h !== cv.height)) { cv.width = w; cv.height = h; draw(src.current); }
    };
    size();
    const ro = 'ResizeObserver' in window ? new ResizeObserver(size) : null;
    if (ro) ro.observe(cv);
    const img = new Image();
    img.decoding = 'async';
    img.src = POSTER;
    img.decode().then(() => { if (!src.current || src.current === img) draw(img); }, () => {});
    return () => { if (ro) ro.disconnect(); };
  }, []);

  // the loop itself
  useEffect(() => {
    const cv = ref.current;
    if (!start || reduced) return undefined;
    let v = null;
    let io = null;
    let raf = 0;
    let vfc = 0;
    let on = false;
    const frame = () => {
      if (!on) return;
      cv.drawFrame(v);
      if (v.requestVideoFrameCallback) vfc = v.requestVideoFrameCallback(frame);
      else raf = requestAnimationFrame(frame);
    };
    const play = () => {
      if (on) return;
      on = true;
      v.play().then(frame, () => { on = false; });
    };
    const stop = () => {
      on = false;
      cancelAnimationFrame(raf);
      if (v && v.cancelVideoFrameCallback && vfc) v.cancelVideoFrameCallback(vfc);
      if (v) v.pause();
    };
    const create = () => {
      v = document.createElement('video');
      v.muted = true;
      v.loop = true;
      v.playsInline = true;
      v.preload = 'auto';
      SOURCES.forEach(([s, type]) => {
        const el = document.createElement('source');
        el.src = s;
        el.type = type;
        v.appendChild(el);
      });
      io = new IntersectionObserver(([e]) => (e.isIntersecting ? play() : stop()), { threshold: 0 });
      io.observe(cv.closest('.hero') || cv);
    };
    const ric = window.requestIdleCallback || ((f) => setTimeout(f, 200));
    const cic = window.cancelIdleCallback || clearTimeout;
    const id = ric(create, { timeout: 1500 });
    return () => {
      cic(id);
      if (io) io.disconnect();
      stop();
      if (v) { v.removeAttribute('src'); v.querySelectorAll('source').forEach((s) => s.remove()); v.load(); }
    };
  }, [start, reduced]);

  return (
    <div className="hero-film" aria-hidden="true">
      <canvas ref={ref} />
      <div className="hero-scrim" />
    </div>
  );
}
