export interface AuthUser {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'etradie';
  active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface RegisterResponse {
  user: AuthUser;
  tokens: TokenPair;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}
