import { createContext, useCallback, useContext, useEffect, useState } from 'react';

export const THEMES = [
  { id: 'deep-sea', label: 'Deep Sea' },
  { id: 'aubergine', label: 'Aubergine' },
  { id: 'porcelain', label: 'Porcelain' },
];
const KEY = 'xfed-theme';

function readSaved() {
  try {
    const v = window.localStorage.getItem(KEY);
    return THEMES.some((t) => t.id === v) ? v : THEMES[0].id;
  } catch {
    return THEMES[0].id;
  }
}

export const ThemeContext = createContext(null);

// `epoch` counts theme switches: views replay the loading bloom on each one.
export function useThemeState() {
  const [theme, setThemeRaw] = useState(readSaved);
  const [epoch, setEpoch] = useState(0);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  const setTheme = useCallback((id) => {
    setThemeRaw(id);
    setEpoch((e) => e + 1);
    try {
      window.localStorage.setItem(KEY, id);
    } catch {
      // storage blocked: the choice still applies for this page view
    }
  }, []);
  return { theme, setTheme, epoch };
}

export function useTheme() {
  return useContext(ThemeContext);
}
