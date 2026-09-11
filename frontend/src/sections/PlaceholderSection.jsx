import Callout from '../components/Callout';
import Rule from '../components/Rule';
import SectionHeader from '../components/SectionHeader';
import { TEXT_FAINT } from '../theme/tokens';

// Every section renders this until its real data view is built. It still
// renders the section's actual header copy (ported from sections.py) --
// only the chart/table body is stubbed, never a fabricated number.
export default function PlaceholderSection({ eyebrow, title, lede }) {
  return (
    <>
      <SectionHeader eyebrow={eyebrow} title={title} lede={lede} />
      <Rule />
      <Callout tone={TEXT_FAINT}>
        This section's data view hasn't been built yet. The app shell, theme, and
        live backend connection are wired up first — charts and real numbers come next.
      </Callout>
    </>
  );
}
