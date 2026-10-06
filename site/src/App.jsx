import { useEffect, useState } from 'react';
import { startSmoothScroll, useAnchorScroll } from './motion.js';
import Loader from './sections/Loader.jsx';
import Nav from './sections/Nav.jsx';
import Hero from './sections/Hero.jsx';
import Story from './sections/Story.jsx';
import Marquee from './sections/Marquee.jsx';
import System from './sections/System.jsx';
import Explain from './sections/Explain.jsx';
import Trust from './sections/Trust.jsx';
import Replay from './sections/Replay.jsx';
import Limits from './sections/Limits.jsx';
import Footer from './sections/Footer.jsx';

// 'loading' (counter running) -> 'leaving' (panel sliding up, hero plays) -> 'done'
const initialPhase = () => (document.documentElement.classList.contains('with-loader') ? 'loading' : 'done');

export default function App() {
  const [phase, setPhase] = useState(initialPhase);

  useEffect(() => startSmoothScroll(), []);
  useAnchorScroll();

  return (
    <div className="page">
      {phase !== 'done' && <Loader phase={phase} setPhase={setPhase} />}
      <Nav />
      <main>
        <Hero play={phase !== 'loading'} count={phase === 'done'} />
        <Story />
        <Marquee />
        <System />
        <Explain />
        <Trust />
        <Replay />
        <Limits />
      </main>
      <Footer />
    </div>
  );
}
