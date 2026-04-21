import axios, { AxiosError, AxiosInstance } from 'axios';
import { env } from '@/config/env';

const TOKEN_KEY = 'etradie_access_token';
const REFRESH_KEY = 'etradie_refresh_token';

/** Read the current access token from localStorage. */
export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

/** Read the current refresh token from localStorage. */
export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

/** Persist tokens in localStorage after login/refresh. */
export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

/** Clear tokens on logout. */
export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

/* ─── Factory ───────────────────────────────────────────────── */

function createClient(baseURL: string): AxiosInstance {
  const client = axios.create({
    baseURL,
    timeout: 300_000,
    headers: { 'Content-Type': 'application/json' },
  });

  /* Inject Authorization header on every request */
  client.interceptors.request.use((config) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  /* Silent token refresh on 401 */
  let isRefreshing = false;
  let pendingQueue: Array<{
    resolve: (token: string) => void;
    reject: (err: unknown) => void;
  }> = [];

  const processQueue = (token: string | null, error?: unknown) => {
    pendingQueue.forEach((p) => {
      if (token) p.resolve(token);
      else p.reject(error);
    });
    pendingQueue = [];
  };

  client.interceptors.response.use(
    (res) => res,
    async (error: AxiosError) => {
      const original = error.config;
      if (!original || error.response?.status !== 401) {
        return Promise.reject(error);
      }

      /* Skip refresh loop for auth endpoints themselves */
      if (original.url?.startsWith('/auth/')) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          pendingQueue.push({ resolve, reject });
        }).then((newToken) => {
          original.headers.Authorization = `Bearer ${newToken}`;
          return client(original);
        });
      }

      isRefreshing = true;
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        clearTokens();
        window.location.href = '/login';
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(
          `${env.gatewayHttpUrl}/auth/refresh`,
          { refresh_token: refreshToken },
        );
        const newAccess = data.access_token;
        const newRefresh = data.refresh_token;
        setTokens(newAccess, newRefresh);
        processQueue(newAccess);

        original.headers.Authorization = `Bearer ${newAccess}`;
        return client(original);
      } catch (refreshError) {
        processQueue(null, refreshError);
        clearTokens();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    },
  );

  return client;
}

/* ─── Exported per-service clients ──────────────────────────── */

export const gatewayApi = createClient(env.gatewayHttpUrl);
export const engineApi = createClient(env.engineUrl);
export const executionApi = createClient(env.executionUrl);
export const managementApi = createClient(env.managementUrl);

export const api = {
  gateway: gatewayApi,
  engine: engineApi,
  execution: executionApi,
  management: managementApi,
} as const;
