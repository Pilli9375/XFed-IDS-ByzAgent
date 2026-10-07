import { useEffect, useState } from 'react';
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
