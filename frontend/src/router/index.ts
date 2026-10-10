import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/useAuthStore';

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/pages/LoginPage.vue'),
      meta: { title: '登录' },
    },
    {
      path: '/',
      redirect: '/app/employee',
    },
    {
      path: '/app/employee',
      name: 'employee',
      component: () => import('@/pages/EmployeePage.vue'),
      meta: { title: '员工端', requiresAuth: true },
    },
    {
      path: '/app/agent',
      name: 'agent',
      component: () => import('@/pages/AgentPage.vue'),
      meta: { title: '坐席端', requiresAuth: true },
    },
    {
      path: '/app/knowledge',
      name: 'knowledge',
      component: () => import('@/pages/KnowledgePage.vue'),
      meta: { title: '知识库', requiresAuth: true },
    },
  ],
});

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore();

  if (to.meta.requiresAuth && !auth.token) {
    next({ path: '/login', query: { redirect: to.fullPath } });
    return;
  }

  if (to.path === '/login' && auth.token) {
    next((to.query.redirect as string) || '/app/employee');
    return;
  }

  if (auth.token) {
    if (to.path === '/app/employee' && !auth.canSeeEmployee()) {
      next(auth.canSeeAgent() ? '/app/agent' : '/app/knowledge');
      return;
    }
    if (to.path === '/app/agent' && !auth.canSeeAgent()) {
      next(auth.canSeeEmployee() ? '/app/employee' : '/app/knowledge');
      return;
    }
  }

  next();
});

router.afterEach((to) => {
  const t = (to.meta.title as string) || '智能客服';
  document.title = t;
});
