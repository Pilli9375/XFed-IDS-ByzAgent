import { useEffect, useLayoutEffect, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import Lenis from 'lenis';

gsap.registerPlugin(ScrollTrigger);

const RM = '(prefers-reduced-motion: reduce)';
export const prefersReduced = () => typeof window !== 'undefined' && window.matchMedia && window.matchMedia(RM).matches;

export function useReducedMotion() {
  const [reduced, setReduced] = useState(prefersReduced);
  useEffect(() => {
    const mq = window.matchMedia(RM);
    const on = () => setReduced(mq.matches);
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);
  return reduced;
}

export function useMedia(query) {
  const [match, setMatch] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setMatch(mq.matches);
    on();
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, [query]);
  return match;
}

// true once the element has entered view (or come within rootMargin of it)
export function useInView(ref, { rootMargin = '0px', threshold = 0.18, once = true } = {}) {
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!('IntersectionObserver' in window)) { setInView(true); return; }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) { setInView(true); if (once) io.disconnect(); }
        else if (!once) setInView(false);
      });
    }, { rootMargin, threshold });
    io.observe(el);
    return () => io.disconnect();
  }, [ref, rootMargin, threshold, once]);
  return inView;
}

// ---- section curtains ---------------------------------------------------------
// Where the page changes colour, the next section's panel rises and widens into place,
// scrubbed by scroll. Its header reveals use AFTER_CURTAIN so they wait for the panel.
export const AFTER_CURTAIN = '0px 0px -35% 0px';

export function useCurtain(sectionRef, panelRef) {
  const reduced = useReducedMotion();
  useLayoutEffect(() => {
    if (reduced) return undefined;
    const sec = sectionRef.current;
    const el = panelRef.current;
    // rise less than the section's top padding, so the panel never uncovers its own text
    const rise = () => Math.max(24, Math.min(110, parseFloat(getComputedStyle(sec).paddingTop) - 24));
    const narrow = () => window.innerWidth < 760;
    const tw = gsap.fromTo(el, { y: rise, scaleX: () => (narrow() ? 0.96 : 0.9) }, {
      y: 0,
      scaleX: 1,
      ease: 'none',
      scrollTrigger: { trigger: sec, start: 'top bottom', end: 'top 50%', scrub: 0.5, invalidateOnRefresh: true },
    });
    return () => {
      if (tw.scrollTrigger) tw.scrollTrigger.kill();
      tw.kill();
      gsap.set(el, { clearProps: 'transform' });
    };
  }, [sectionRef, panelRef, reduced]);
}

// Lazy sections (trust grid, replay) change the page height after load; keep trigger positions true.
export function useRefreshOnResize() {
  useEffect(() => {
    if (!('ResizeObserver' in window)) return undefined;
    let t = 0;
    let last = document.body.scrollHeight;
    const ro = new ResizeObserver(() => {
      const h = document.body.scrollHeight;
      if (Math.abs(h - last) < 2) return;
      last = h;
      clearTimeout(t);
      t = setTimeout(() => ScrollTrigger.refresh(), 150);
    });
    ro.observe(document.body);
    return () => { clearTimeout(t); ro.disconnect(); };
  }, []);
}

// Mouse drag scrolls a horizontally overflowing box (the trust grid on narrow windows).
// Only while it overflows is it marked data-cursor="drag", which the custom cursor reads.
export function useDragScroll(ref) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const mark = () => {
      if (el.scrollWidth > el.clientWidth + 1) el.dataset.cursor = 'drag';
      else delete el.dataset.cursor;
    };
    mark();
    const ro = 'ResizeObserver' in window ? new ResizeObserver(mark) : null;
    if (ro) { ro.observe(el); if (el.firstElementChild) ro.observe(el.firstElementChild); }
    let x0 = 0; let s0 = 0; let down = false;
    const onDown = (e) => {
      if (e.pointerType !== 'mouse' || e.button !== 0 || !el.dataset.cursor) return;
      down = true; x0 = e.clientX; s0 = el.scrollLeft;
    };
    const onMove = (e) => { if (down) el.scrollLeft = s0 - (e.clientX - x0); };
    const onUp = () => { down = false; };
    el.addEventListener('pointerdown', onDown);
    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerup', onUp);
    return () => {
      if (ro) ro.disconnect();
      el.removeEventListener('pointerdown', onDown);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, [ref]);
}

// ---- smooth scrolling ---------------------------------------------------------
let lenis = null;

export function startSmoothScroll() {
  if (lenis || prefersReduced()) return () => {};
  lenis = new Lenis({ duration: 1.1, smoothWheel: true });
  lenis.on('scroll', ScrollTrigger.update);
  const tick = (time) => lenis && lenis.raf(time * 1000);
  gsap.ticker.add(tick);
  gsap.ticker.lagSmoothing(0);
  return () => {
    gsap.ticker.remove(tick);
    lenis.destroy();
    lenis = null;
  };
}

// Hold the page still while a modal is open (Lenis listens to wheel on window).
export function holdScroll(on) {
  document.documentElement.style.overflow = on ? 'hidden' : '';
  if (lenis) { if (on) lenis.stop(); else lenis.start(); }
}

export function scrollToY(y) {
  if (lenis) lenis.scrollTo(y, { duration: 1.2 });
  else window.scrollTo({ top: y, behavior: prefersReduced() ? 'auto' : 'smooth' });
}

export function scrollToId(id) {
  const el = document.getElementById(id);
  if (!el) return;
  if (lenis) {
    // Sections above can change height mid-scroll (lazy data arriving); land, then correct once.
    lenis.scrollTo(el, {
      duration: 1.2,
      onComplete: () => { if (lenis && Math.abs(el.getBoundingClientRect().top) > 2) lenis.scrollTo(el, { duration: 0.35 }); },
    });
  } else el.scrollIntoView({ behavior: prefersReduced() ? 'auto' : 'smooth' });
  // move keyboard focus to the section without scrolling again
  if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '-1');
  el.focus({ preventScroll: true });
  history.replaceState(null, '', '#' + id);
}

// In-page links (<a href="#id">) scroll smoothly and move focus to the target.
export function useAnchorScroll() {
  useEffect(() => {
    const onClick = (e) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = e.target.closest('a[href^="#"]');
      if (!a) return;
      const id = a.getAttribute('href').slice(1);
      if (!id || !document.getElementById(id)) return;
      e.preventDefault();
      scrollToId(id);
    };
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, []);
}

export { gsap, ScrollTrigger };
