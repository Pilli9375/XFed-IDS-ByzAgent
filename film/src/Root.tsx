import React from 'react';
import { Composition, continueRender, delayRender } from 'remotion';
import { Film } from './Film';
import { HeroLoop, HERO_FRAMES } from './HeroLoop';
import { TL } from './motion';
import { fontsReady } from './fonts';

const handle = delayRender('fonts');
fontsReady.then(() => continueRender(handle));

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Film16x9" component={Film} durationInFrames={TL.durationInFrames} fps={TL.fps} width={1920} height={1080} defaultProps={{ silent: false }} />
    <Composition id="Film9x16" component={Film} durationInFrames={TL.durationInFrames} fps={TL.fps} width={1080} height={1920} defaultProps={{ silent: false }} />
    <Composition id="HeroLoop" component={HeroLoop} durationInFrames={HERO_FRAMES} fps={TL.fps} width={1600} height={900} />
  </>
);
