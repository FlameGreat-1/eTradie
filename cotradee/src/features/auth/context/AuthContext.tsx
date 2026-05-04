import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { setTokens, clearTokens, getAccessToken, getRefreshToken } from '@/lib/axios';
import { login as loginApi } from '../api/login';
import { register as registerApi } from '../api/register';
import { fetchProfile, logout as logoutApi } from '../api/profile';
import type { AuthUser, LoginRequest, RegisterRequest, TokenPair } from '../types';

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: LoginRequest) => Promise<void>;
  register: (payload: RegisterRequest) => Promise<void>;
  /**
   * Hydrate the session from a TokenPair obtained out-of-band
   * (currently: the Google OAuth callback). Behaves observably the
   * same as a successful password login: tokens are persisted, the
   * profile is fetched (or used directly if supplied), and the
   * AuthContext switches to authenticated.
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
    const token = getAccessToken();
    if (!token) {
      setIsLoading(false);
      return;
    }
    try {
      const profile = await fetchProfile();
      setUser(profile);
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = useCallback(async (payload: LoginRequest) => {
    const tokens = await loginApi(payload);
    setTokens(tokens.access_token, tokens.refresh_token);
    const profile = await fetchProfile();
    setUser(profile);
  }, []);

  const register = useCallback(async (payload: RegisterRequest) => {
    const res = await registerApi(payload);
    setTokens(res.tokens.access_token, res.tokens.refresh_token);
    setUser(res.user);
  }, []);

  const loginWithTokenPair = useCallback(async (tokens: TokenPair, presetUser?: AuthUser) => {
    setTokens(tokens.access_token, tokens.refresh_token);
    if (presetUser) {
      setUser(presetUser);
      return;
    }
    const profile = await fetchProfile();
    setUser(profile);
  }, []);

  const logout = useCallback(async () => {
    const refresh = getRefreshToken();
    try {
      await logoutApi(refresh || undefined);
    } finally {
      clearTokens();
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
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
