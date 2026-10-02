import Callout from './Callout';
import { ALERT, WARN } from '../theme/tokens';

// Shared by Detect and Explain (both read useEvalRows). Renders nothing when
// every row loaded. `allFailed` -> the original hard-error wording; otherwise a
// plain partial-failure note. Either way Retry re-fetches only the failed ids.
export default function EvalRowsStatus({ failed, retrying, retry, allFailed }) {
  if (failed.length === 0) return null;
  const ids = failed.map((f) => f.id).join(', ');
  return (
    <div data-eval-rows-status={allFailed ? 'all-failed' : 'partial'}>
      <Callout tone={allFailed ? ALERT : WARN}>
        {allFailed ? (
          <>Could not load evaluation rows: {failed[0].error}</>
        ) : (
          <>
            {failed.length} of 14 evaluation rows could not be loaded (GET /shap id{failed.length > 1 ? 's' : ''}{' '}
            {ids}: {failed[0].error}). Only the rows that loaded are offered below; nothing is
            substituted for the missing ones.
          </>
        )}
        <div style={{ height: 'var(--sp-sm)' }} />
        <button type="button" className="xf-retry-btn" disabled={retrying} onClick={retry}>
          {retrying ? 'Retrying…' : 'Retry'}
        </button>
      </Callout>
      <div style={{ height: 'var(--sp-sm)' }} />
    </div>
  );
}
