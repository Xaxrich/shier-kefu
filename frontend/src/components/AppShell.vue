<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/useAuthStore';
defineProps<{
  title: string;
  active: 'employee' | 'agent' | 'knowledge';
}>();

const router = useRouter();
const auth = useAuthStore();

const showEmployee = computed(() => auth.canSeeEmployee());
const showAgent = computed(() => auth.canSeeAgent());
const showKnowledge = computed(() => auth.canSeeKnowledge());
const displayName = computed(() => auth.user?.username ?? '用户');

function go(path: string) {
  void router.push(path);
}

function logout() {
  auth.logout();
  void router.push('/login');
}
</script>

<template>
  <div class="shell">
    <aside class="shell__nav" aria-label="主导航">
      <div class="shell__brand">智能客服</div>
      <nav class="shell__menu">
        <button
          v-if="showEmployee"
          type="button"
          class="shell__item"
          :class="{ 'shell__item--active': active === 'employee' }"
          @click="go('/app/employee')"
        >
          <span class="shell__bar" aria-hidden="true" />
          员工端
        </button>
        <button
          v-if="showAgent"
          type="button"
          class="shell__item"
          :class="{ 'shell__item--active': active === 'agent' }"
          @click="go('/app/agent')"
        >
          <span class="shell__bar" aria-hidden="true" />
          坐席端
        </button>
        <button
          v-if="showKnowledge"
          type="button"
          class="shell__item"
          :class="{ 'shell__item--active': active === 'knowledge' }"
          @click="go('/app/knowledge')"
        >
          <span class="shell__bar" aria-hidden="true" />
          知识库
        </button>
      </nav>
      <div class="shell__footer">
        <span class="shell__user">{{ displayName }}</span>
        <button type="button" class="shell__logout" @click="logout">退出登录</button>
      </div>
    </aside>
    <div class="shell__main">
      <header class="shell__top">
        <h1 class="shell__title">{{ title }}</h1>
        <span class="shell__meta">帮助 · {{ displayName }}</span>
      </header>
      <main class="shell__body">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  height: 100%;
  min-height: 100vh;
  background: var(--color-bg-card);
}
.shell__nav {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 20px 16px;
  gap: 10px;
  background: var(--color-bg-page);
  border-right: 1px solid var(--color-border);
}
.shell__brand {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
}
.shell__menu {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}
.shell__item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding: 0 12px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  font-size: 0.875rem;
  color: #52525b;
  cursor: pointer;
  text-align: left;
  font-family: var(--font-sans);
  transition: background 0.12s ease;
}
.shell__item:hover {
  background: #fafafa;
}
.shell__item:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}
.shell__item--active {
  background: var(--color-row-selected);
  color: var(--color-primary);
  font-weight: 600;
}
.shell__item--active .shell__bar {
  opacity: 1;
}
.shell__bar {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 24px;
  border-radius: 1px;
  background: var(--color-primary);
  opacity: 0;
}
.shell__footer {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}
.shell__logout {
  border: none;
  background: none;
  padding: 0;
  color: var(--color-primary);
  cursor: pointer;
  font-size: 0.75rem;
  text-align: left;
  font-family: var(--font-sans);
  border-radius: 4px;
}
.shell__logout:hover {
  text-decoration: underline;
}
.shell__logout:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}
.shell__main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.shell__top {
  height: 56px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-card);
}
.shell__title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text);
}
.shell__meta {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
}
.shell__body {
  flex: 1;
  min-height: 0;
  padding: 0;
  overflow: auto;
}
</style>
