import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import type { AuthUser, UserRole } from '@/types/auth';
import * as authService from '@/services/authService';

const TOKEN_KEY = 'token';
const USER_KEY = 'auth_user';

function readStoredUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY));
  const user = ref<AuthUser | null>(readStoredUser());

  const isAuthenticated = computed(() => Boolean(token.value));

  function setSession(accessToken: string, u: AuthUser) {
    token.value = accessToken;
    user.value = u;
    localStorage.setItem(TOKEN_KEY, accessToken);
    localStorage.setItem(USER_KEY, JSON.stringify(u));
  }

  function clearSession() {
    token.value = null;
    user.value = null;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  function canSeeEmployee(): boolean {
    const r = user.value?.role;
    return r === 'employee' || r === 'both';
  }

  function canSeeAgent(): boolean {
    const r = user.value?.role;
    return r === 'agent' || r === 'both';
  }

  function canSeeKnowledge(): boolean {
    return Boolean(user.value);
  }

  async function login(username: string, password: string) {
    const data = await authService.login(username, password);
    setSession(data.access_token, data.user);
  }

  function logout() {
    clearSession();
  }

  return {
    token,
    user,
    isAuthenticated,
    setSession,
    clearSession,
    login,
    logout,
    canSeeEmployee,
    canSeeAgent,
    canSeeKnowledge,
  };
});
