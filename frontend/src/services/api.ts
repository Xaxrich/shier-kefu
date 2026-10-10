import axios from 'axios';

const raw = import.meta.env.VITE_API_BASE_URL as string | undefined;
/** 未配置时使用相对路径 /api，由 Vite dev/preview 代理到后端；需直连后端时再设完整 URL */
const base =
  raw !== undefined && String(raw).trim() !== ''
    ? String(raw).replace(/\/$/, '')
    : '';

export const api = axios.create({
  baseURL: base,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // 全局默认 JSON 会破坏 FormData 的 multipart boundary，后端会 422
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  }
  return config;
});

function formatValidationDetail(detail: unknown): string | null {
  if (!Array.isArray(detail)) return null;
  const parts = detail.map((item: { loc?: unknown[]; msg?: string }) => {
    const loc = Array.isArray(item.loc) ? item.loc.join('.') : '';
    const msg = item.msg ?? '';
    return loc ? `${loc}: ${msg}` : msg;
  });
  return parts.filter(Boolean).join('；') || null;
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('auth_user');
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    const status = error.response?.status;
    const data = error.response?.data as { detail?: unknown } | undefined;
    if (status === 422 && data?.detail) {
      const formatted = formatValidationDetail(data.detail);
      if (formatted) {
        error.message = formatted;
      }
    }
    return Promise.reject(error);
  },
);

export default api;
