// The film's only data entry point: the site's JSON files, imported directly (no copies).
import story from '../../site/public/data/story.json';
import headline from '../../site/public/data/headline.json';
import agreement from '../../site/public/data/agreement_by_alpha.json';
import ci from '../../site/public/data/ci.json';
import baselines from '../../site/public/data/baselines.json';
import byz from '../../site/public/data/byzagent_decisions.json';
import replay from '../../site/public/data/replay_alerts.json';
import fedprox from '../../site/public/data/fedprox_vs_fedavg.json';
import { build } from './numbers.js';
import { story as siteStory, footer as siteFooter, trust as siteTrust, replay as siteReplay, explain as siteExplain, hero as siteHero } from '../../site/src/copy.js';

type Built = {
  N: Record<string, string>;
  registry: { id: string; text: string; file: string; key: string; raw: unknown }[];
  raw: {
    perSeed: { seed: number; v: number }[];
    f1Std: number;
    comp: { total: number; slices: number[] }[];
    jac: number[];
    lows: number[];
    mal: number[];
    gA: number[][];
    gB: number[][];
    featSilo: number;
    featRound: number;
    nRounds: number;
    nSilos: number;
    agree: Record<string, number>;
    floor: [number, number];
    chance: number;
    ci: [number, number];
    f1: number;
    mkx: number;
  };
};

const built = build({ story, headline, agreement, ci, baselines, byz, replay, fedprox }) as unknown as Built;
export const N = built.N;
export const RAW = built.raw;
export const REGISTRY = built.registry;
export const COPY = { story: siteStory, footer: siteFooter, trust: siteTrust, replay: siteReplay, explain: siteExplain, hero: siteHero };
