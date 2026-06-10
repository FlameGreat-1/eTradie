import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { login as loginApi } from '../api/login';
import { register as registerApi } from '../api/register';
import { fetchProfile, logout as logoutApi } from '../api/profile';
import type { AuthUser, LoginRequest, RegisterRequest, TokenPair } from '../types';
import { AUTH_LOGOUT_BROADCAST_KEY } from '@/lib/axios';

// ---------------------------------------------------------------------------
// Cookie-auth context (Batch 11)
//
// Pre-Batch-11 this provider read access/refresh tokens from localStorage
// to decide whether to call fetchProfile on mount. Post-Batch-11 the
// tokens live in HttpOnly cookies that JS cannot read; the canonical
// way to ask 'am I logged in?' is to call the server. We always issue
// the request on mount: a 200 means an authenticated user, a 401 (or
// any other error) is treated as 'not logged in' and the SPA renders
// the public routes.
//
// login / register / loginWithTokenPair / logout no longer mutate any
// client-side token store. The TokenPair returned by the server is
// still part of the JSON body for backward compatibility with non-
// browser clients, but the browser ignores it: the gateway has
// already set the cookies on the same response.
// ---------------------------------------------------------------------------

/**
 * Explicit tri-state of the session, derived from (user, isLoading):
 *   'loading'       - the boot /auth/me probe has not resolved yet.
 *   'authenticated' - probe resolved and a user is present.
 *   'guest'         - probe resolved (or failed) and no user.
 *
 * Route guards read this single value instead of combining the two
 * booleans below, which removes the ambiguous "isLoading && isAuthenticated"
 * states each call site previously had to reason about. The booleans are
 * retained unchanged for existing consumers.
 */
export type AuthStatus = 'loading' | 'authenticated' | 'guest';

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  /** Derived tri-state; preferred over isAuthenticated/isLoading for routing. */
  status: AuthStatus;
  login: (payload: LoginRequest) => Promise<void>;
  register: (payload: RegisterRequest) => Promise<void>;
  /**
   * Hydrate the session from a successful OAuth callback. The cookies
   * have already been set server-side when this fires; the parameter
   * exists for API symmetry with the password login but its values
   * are not stored anywhere on the client.
   */
  loginWithTokenPair: (tokens: TokenPair, user?: AuthUser) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadUser = useCallback(async () => {
    try {
      const profile = await fetchProfile();
      setUser(profile);
    } catch {
      // 401 / network error / etc. All map to 'not logged in'.
      // No client-side state to clear: the cookies are HttpOnly,
      // and the server has either expired them or never set them.
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = useCallback(async (payload: LoginRequest) => {
    // /auth/login response sets access_token + refresh_token + csrf_token
    // cookies before returning. The TokenPair in the JSON body is
    // ignored by the browser; cookies are the canonical channel.
    await loginApi(payload);
    const profile = await fetchProfile();
    setUser(profile);
  }, []);

  const register = useCallback(async (payload: RegisterRequest) => {
    const res = await registerApi(payload);
    setUser(res.user);
  }, []);

  const loginWithTokenPair = useCallback(async (_tokens: TokenPair, presetUser?: AuthUser) => {
    // OAuth callback already returned with cookies set. The TokenPair
    // parameter is preserved for API compatibility but its values are
    // never stored — the browser only trusts the cookie jar.
    if (presetUser) {
      setUser(presetUser);
      return;
    }
    const profile = await fetchProfile();
    setUser(profile);
  }, []);

  const logout = useCallback(async () => {
    try {
      // No body: the refresh_token cookie carries the value the
      // server needs to revoke the session. After this returns,
      // the gateway has cleared all three cookies.
      await logoutApi();
    } finally {
      setUser(null);
      try {
        sessionStorage.removeItem('exoper_resume_pill_dismissed');
      } catch {}
      // Notify every other tab on this origin that the session has
      // ended so they can route themselves to /login. The current
      // tab's navigation is owned by whoever called logout()
      // (typically the Header's handleLogout, which calls navigate
      // afterwards), so we deliberately do NOT redirect here.
      // broadcastLogoutAndRedirect's same-origin storage write is
      // a no-op in the tab that authored it; the redirect inside
      // it is suppressed by the early-return below.
      try {
        // Set the broadcast value without redirecting THIS tab —
        // we let the caller decide where to navigate next. The key
        // is imported from @/lib/axios so both ends of the channel
        // share one source of truth; a rename there is a compile
        // error here.
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(
            AUTH_LOGOUT_BROADCAST_KEY,
            JSON.stringify({ reason: 'user', at: Date.now() }),
          );
        }
      } catch {
        /* storage may be disabled (private mode); the user-driven
           navigation from the calling component still completes
           and peer tabs will catch the signed-out state on their
           next /auth/me poll. */
      }
    }
  }, []);

  // Single source of truth for routing decisions. While the boot probe
  // is in flight we are 'loading'; once it settles we are either
  // 'authenticated' (user present) or 'guest' (no user). Derived here so
  // every guard reads the same resolved value.
  const status: AuthStatus = isLoading ? 'loading' : user ? 'authenticated' : 'guest';

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        status,
        login,
        register,
        loginWithTokenPair,
        logout,
        refreshUser: loadUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
