import { useEffect, useRef, useState } from 'react';
import { hero } from '../copy.js';
import { holdScroll } from '../motion.js';

// Full-screen player for the 16:9 film, sound on, captions on. A real modal <dialog>: the page
// behind is inert (focus stays inside), Esc closes it, and focus returns to the opener. The
// video is only mounted on first open, so nothing is fetched until someone asks for it.
export default function FilmDialog({ open, onClose, labelledBy }) {
  const dlg = useRef(null);
  const vid = useRef(null);
  const opener = useRef(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const el = dlg.current;
    if (open) {
      opener.current = document.activeElement;
      setMounted(true);
      if (!el.open) el.showModal();
      holdScroll(true);
    } else if (el.open) el.close();
  }, [open]);

  // start playback once the video exists (the click that opened the dialog allows sound)
  useEffect(() => {
    if (open && mounted && vid.current) vid.current.play().catch(() => {});
  }, [open, mounted]);

  useEffect(() => {
    const el = dlg.current;
    const onCloseEv = () => {
      if (vid.current) vid.current.pause();
      holdScroll(false);
      if (opener.current && opener.current.focus) opener.current.focus({ preventScroll: true });
      onClose();
    };
    el.addEventListener('close', onCloseEv);
    return () => el.removeEventListener('close', onCloseEv);
  }, [onClose]);

  // a click on the backdrop (the dialog box itself, outside the player) closes it
  const onClick = (e) => { if (e.target === dlg.current) dlg.current.close(); };

  return (
    <dialog ref={dlg} className="film-dlg" aria-labelledby={labelledBy} onClick={onClick}>
      <button type="button" className="film-close btn" onClick={() => dlg.current.close()} aria-keyshortcuts="Escape">
        {hero.filmClose}
      </button>
      {mounted && (
        <video ref={vid} className="film-vid" controls playsInline preload="metadata" poster="/film/poster.jpg">
          <source src="/film/xfed_film_16x9.mp4" type="video/mp4" />
          <track kind="captions" src="/film/xfed_film_16x9.en.vtt" srcLang="en" label="English" default />
        </video>
      )}
    </dialog>
  );
}
