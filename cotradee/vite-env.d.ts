/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ENGINE_URL: string;
  readonly VITE_GATEWAY_HTTP_URL: string;
  readonly VITE_GATEWAY_WS_URL: string;
  readonly VITE_EXECUTION_URL: string;
  readonly VITE_MANAGEMENT_URL: string;
  readonly VITE_GOOGLE_OAUTH_ENABLED?: string;
  readonly VITE_OAUTH_CALLBACK_PATH?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
