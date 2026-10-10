<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/useAuthStore';

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const username = ref('');
const password = ref('');
const submitted = ref(false);
const loading = ref(false);
const formError = ref('');

const usernameError = computed(() => {
  if (!submitted.value) return '';
  return username.value.trim() ? '' : '请输入工号或邮箱';
});

const passwordError = computed(() => {
  if (!submitted.value) return '';
  return password.value ? '' : '请输入密码';
});

const canSubmit = computed(() => username.value.trim().length > 0 && password.value.length > 0);

async function onSubmit(e: Event) {
  e.preventDefault();
  submitted.value = true;
  formError.value = '';
  if (!canSubmit.value) return;
  loading.value = true;
  try {
    await auth.login(username.value.trim(), password.value);
    const redirect = (route.query.redirect as string) || '/app/employee';
    await router.replace(redirect);
  } catch (err) {
    const msg = err instanceof Error ? err.message : '登录失败，请检查账号密码或确认后端已启动';
    formError.value = msg;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login">
    <div class="login__panel" aria-labelledby="login-title">
      <div class="login__accent" aria-hidden="true" />
      <header class="login__head">
        <h1 id="login-title" class="login__title">智能客服</h1>
        <p class="login__lede">企业内部问答与工单协作</p>
      </header>

      <form class="login__form" novalidate @submit="onSubmit">
        <p v-if="formError" class="login__banner" role="alert">{{ formError }}</p>

        <div class="login__field">
          <label class="login__label" for="login-username">账号</label>
          <input
            id="login-username"
            v-model="username"
            class="login__input"
            :class="{ 'login__input--invalid': usernameError }"
            type="text"
            name="username"
            autocomplete="username"
            placeholder="工号或邮箱"
            aria-required="true"
            :aria-invalid="usernameError ? 'true' : 'false'"
            :aria-describedby="usernameError ? 'login-username-err' : undefined"
          />
          <p v-if="usernameError" id="login-username-err" class="login__hint login__hint--error" role="alert">
            {{ usernameError }}
          </p>
        </div>

        <div class="login__field">
          <label class="login__label" for="login-password">密码</label>
          <input
            id="login-password"
            v-model="password"
            class="login__input"
            :class="{ 'login__input--invalid': passwordError }"
            type="password"
            name="password"
            autocomplete="current-password"
            placeholder="••••••••"
            aria-required="true"
            :aria-invalid="passwordError ? 'true' : 'false'"
            :aria-describedby="passwordError ? 'login-password-err' : undefined"
          />
          <p v-if="passwordError" id="login-password-err" class="login__hint login__hint--error" role="alert">
            {{ passwordError }}
          </p>
        </div>

        <button class="login__submit" type="submit" :disabled="loading" :aria-busy="loading">
          {{ loading ? '登录中…' : '登录' }}
        </button>

        <p class="login__help" role="note">
          后端默认账号：<strong>demo</strong> / <strong>demo123</strong>（角色 both）。需先启动 API（见项目根
          <code class="login__code">.output/startup.md</code>）。
        </p>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(16px, 4vw, 32px);
  background: var(--color-bg-page);
}

.login__panel {
  position: relative;
  width: 100%;
  max-width: 400px;
  padding: 28px 28px 24px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  box-shadow: 0 1px 2px rgb(24 24 27 / 6%);
}

.login__accent {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 3px;
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  background: var(--color-primary);
}

.login__head {
  text-align: center;
  margin-bottom: 22px;
}

.login__title {
  margin: 0 0 6px;
  font-size: clamp(1.375rem, 2.5vw, 1.75rem);
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--color-text);
}

.login__lede {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--color-text-secondary);
}

.login__form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.login__banner {
  margin: 0;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  color: #991b1b;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.login__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.login__label {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--color-text-secondary);
}

.login__input {
  height: 40px;
  padding: 0 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: #fff;
  font-size: 0.875rem;
  font-family: var(--font-sans);
  color: var(--color-text);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.login__input::placeholder {
  color: var(--color-text-muted);
  text-transform: none;
  letter-spacing: normal;
}

.login__input:hover {
  border-color: color-mix(in srgb, var(--color-text-secondary) 35%, var(--color-border));
}

.login__input:focus {
  outline: none;
  border-color: color-mix(in srgb, var(--color-primary) 55%, var(--color-border));
  box-shadow: var(--shadow-focus);
}

.login__input--invalid {
  border-color: var(--color-danger);
  background: var(--color-danger-bg);
}

.login__hint {
  margin: 0;
  font-size: 0.75rem;
  line-height: 1.35;
}

.login__hint--error {
  color: var(--color-danger);
}

.login__submit {
  height: 40px;
  margin-top: 2px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: #fff;
  font-size: 0.875rem;
  font-weight: 600;
  font-family: var(--font-sans);
  cursor: pointer;
  transition:
    background 0.15s ease,
    transform 0.08s ease;
}

.login__submit:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.login__submit:focus {
  outline: none;
  box-shadow: var(--shadow-focus);
}

.login__submit:active:not(:disabled) {
  transform: translateY(1px);
}

.login__submit:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.login__help {
  margin: 4px 0 0;
  font-size: 0.75rem;
  line-height: 1.45;
  color: var(--color-text-muted);
  text-align: center;
}

.login__code {
  font-size: 0.6875rem;
  background: #f4f4f5;
  padding: 1px 4px;
  border-radius: 4px;
}
</style>
