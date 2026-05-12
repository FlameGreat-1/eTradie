import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { STORAGE_KEYS } from '@/utils/constants';
import { useHasConsent } from '@/features/consent/useConsent';

type Theme = 'dark' | 'light';

interface ThemeState {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (t: Theme) => void;
}

const ThemeContext = createContext<ThemeState | undefined>(undefined);

/**
 * Resolve the initial theme without touching persistent storage:
 *   1. If the user has previously granted Functional consent AND a
 *      stored theme exists, this is read by a later effect (not here)
 *      so the bare component start state is determined purely by the
 *      OS preference.
 *   2. Otherwise fall back to the OS-level prefers-color-scheme.
 *   3. If that is also unavailable (very old browser / SSR) default
 *      to 'dark', which matches the rest of the app's visual baseline.
 */
function resolveOSTheme(): Theme {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return 'dark';
  }
  try {
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  } catch {
    return 'dark';
  }
}

/**
 * ThemeProvider — drives the `dark` / `light` class on <html> and
 * exposes a toggle hook to the rest of the SPA.
 *
 * Persistence is gated on Functional cookie consent. Without consent
 * the theme still works for the lifetime of the tab (component state)
 * but is NOT written to localStorage, so no persistent identifier is
 * created. When the user later GRANTS Functional consent we mirror
 * the current in-memory theme into localStorage so the next visit is
 * remembered. When the user REVOKES Functional consent we delete the
 * previously-stored key so the withdrawal removes the data, not just
 * stops future writes (ePrivacy Art. 5(3)).
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const hasFunctional = useHasConsent('functional');

  // Initial state is OS-derived and consent-independent. The effect
  // below promotes a stored value on mount only when consent is
  // present, which is the correct order: never reach into
  // localStorage at any point that consent says we shouldn't.
  const [theme, setThemeState] = useState<Theme>(() => resolveOSTheme());

  // Track the previous consent value so we can detect transitions and
  // act exactly once per transition rather than on every render.
  const prevConsent = useRef<boolean>(hasFunctional);

  // Apply the theme to the document on every change. This is the
  // strictly-necessary side-effect: it does NOT persist anything.
  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('dark', 'light');
    root.classList.add(theme);
  }, [theme]);

  // Consent-aware persistence. Three transitions to handle:
  //   none -> false (initial render with no consent): do nothing.
  //   false -> true (user just granted Functional): adopt any stored
  //                  theme so a previously-recorded choice survives,
  //                  and mirror the current theme so subsequent reads
  //                  are correct.
  //   true -> false (user just revoked Functional): delete the stored
  //                  key. The current tab keeps its theme; only the
  //                  persistent identifier is removed.
  useEffect(() => {
    const transitioned = prevConsent.current !== hasFunctional;
    prevConsent.current = hasFunctional;

    if (hasFunctional) {
      if (transitioned) {
        // Just granted. Prefer the stored value if any; otherwise mirror.
        try {
          const stored = localStorage.getItem(STORAGE_KEYS.THEME);
          if (stored === 'light' || stored === 'dark') {
            setThemeState(stored);
          } else {
            localStorage.setItem(STORAGE_KEYS.THEME, theme);
          }
        } catch {
          /* localStorage unavailable (private mode); silently skip. */
        }
        return;
      }
      // Steady-state with consent: keep the stored copy fresh.
      try {
        localStorage.setItem(STORAGE_KEYS.THEME, theme);
      } catch {
        /* swallow */
      }
      return;
    }

    if (transitioned && !hasFunctional) {
      // Just revoked. Remove the data; the in-memory theme stays.
      try {
        localStorage.removeItem(STORAGE_KEYS.THEME);
      } catch {
        /* swallow */
      }
    }
  }, [hasFunctional, theme]);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  const setTheme = useCallback((t: Theme) => setThemeState(t), []);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeState {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
