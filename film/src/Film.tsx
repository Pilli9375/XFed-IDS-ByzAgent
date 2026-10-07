import React from 'react';
import { AbsoluteFill, Sequence, staticFile } from 'remotion';
import { Audio } from '@remotion/media';
import { bf, TL } from './motion';
import { C } from './theme';
import { S1Hook, S2Learning, S3Uneven, S4Works } from './scenes/S1to4';
import { S5Agree } from './scenes/S5';
import { S6Trust } from './scenes/S6';
import { S7Proof } from './scenes/S7';
import { S8Close } from './scenes/S8';

const SCENES: Record<string, React.FC> = {
  S1: S1Hook, S2: S2Learning, S3: S3Uneven, S4: S4Works, S5: S5Agree, S6: S6Trust, S7: S7Proof, S8: S8Close,
};

export const Film: React.FC<{ silent?: boolean }> = ({ silent }) => (
  <AbsoluteFill style={{ background: C.cream }}>
    {TL.chapters.map((c) => {
      const Scene = SCENES[c.id];
      return (
        <Sequence key={c.id} name={`${c.id} · ${c.name}`} from={bf(c.start)} durationInFrames={bf(c.end) - bf(c.start)}>
          <Scene />
        </Sequence>
      );
    })}
    {!silent && <Audio src={staticFile('audio/score.wav')} />}
  </AbsoluteFill>
);
