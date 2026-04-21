export const env = {
  engineUrl: import.meta.env.VITE_ENGINE_URL || 'http://localhost:8000',
  gatewayHttpUrl: import.meta.env.VITE_GATEWAY_HTTP_URL || 'http://localhost:8080',
  gatewayWsUrl: import.meta.env.VITE_GATEWAY_WS_URL || 'ws://localhost:8080',
  executionUrl: import.meta.env.VITE_EXECUTION_URL || 'http://localhost:8081',
  managementUrl: import.meta.env.VITE_MANAGEMENT_URL || 'http://localhost:8083',
} as const;
