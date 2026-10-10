export type UserRole = 'employee' | 'agent' | 'both';

export interface AuthUser {
  username: string;
  role: UserRole;
}

export interface LoginResponseData {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

/** PyCore 标准成功包一层 */
export interface ApiEnvelope<T> {
  success: boolean;
  data: T | null;
  error?: string | null;
  error_code?: string | null;
  message?: string | null;
}
