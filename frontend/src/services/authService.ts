import api from './api';
import type { ApiEnvelope, LoginResponseData } from '@/types/auth';

export async function login(username: string, password: string): Promise<LoginResponseData> {
  const { data } = await api.post<ApiEnvelope<LoginResponseData>>('/api/auth/login', {
    username,
    password,
  });
  if (!data.success || !data.data) {
    throw new Error(data.error || data.message || '登录失败');
  }
  return data.data;
}
