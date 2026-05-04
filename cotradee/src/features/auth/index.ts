export { AuthProvider, useAuth } from './context/AuthContext';
export type {
  AuthUser,
  TokenPair,
  LoginRequest,
  RegisterRequest,
  OAuthStartRequest,
  OAuthStartResponse,
  OAuthCallbackRequest,
  OAuthCallbackResponse,
} from './types';
// The `AuthProvider` literal-union type lives at
// `@/features/auth/types` and is intentionally NOT re-exported here
// to avoid name-shadowing with the React component of the same name
// also exported above.
export {
  startGoogleOAuth,
  completeGoogleOAuth,
  startGoogleLink,
  completeGoogleLink,
  unlinkGoogle,
} from './api/oauth';
export { useGoogleOAuth } from './hooks/useGoogleOAuth';
export type {
  OAuthLinkStartRequest,
  OAuthLinkStartResponse,
  OAuthLinkCallbackRequest,
  OAuthLinkCallbackResponse,
} from './types';
