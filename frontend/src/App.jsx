import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useHotSwapStatus } from './api/useHotSwapStatus';
import { ThemeContext, useThemeState } from './hooks/useTheme';
import Live from './views/Live';

// Three routes replace the eight Streamlit-era pages (see
// docs/dashboard_inventory/inventory.md for where each old panel went).
// Investigate and Limits are split out so Live's bundle stays small.
const Investigate = lazy(() => import('./views/Investigate'));
const Limits = lazy(() => import('./views/Limits'));

export default function App() {
  const theme = useThemeState();
  const hs = useHotSwapStatus();
  return (
    <ThemeContext.Provider value={theme}>
      <a className="skip-link" href="#main">Skip to content</a>
      <Routes>
        <Route path="/" element={<Live hs={hs} />} />
        <Route
          path="/investigate"
          element={
            <Suspense fallback={<div className="v-page" />}>
              <Investigate hs={hs} />
            </Suspense>
          }
        />
        <Route
          path="/limits"
          element={
            <Suspense fallback={<div className="v-page" />}>
              <Limits hs={hs} />
            </Suspense>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ThemeContext.Provider>
  );
}
