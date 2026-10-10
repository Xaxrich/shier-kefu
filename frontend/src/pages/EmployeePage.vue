<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import AppShell from '@/components/AppShell.vue';
import * as ticketService from '@/services/ticketService';
import type { TicketDetail, TicketSummary } from '@/types/ticket';

const tickets = ref<TicketSummary[]>([]);
const selectedId = ref<number | null>(null);
const detail = ref<TicketDetail | null>(null);
const loading = ref(true);
const sending = ref(false);
const err = ref('');
const draft = ref('');

function fmt(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false });
  } catch {
    return iso;
  }
}

function statusLabel(s: string): string {
  if (s === 'open') return '待处理';
  if (s === 'processing') return '处理中';
  if (s === 'closed') return '已结束';
  return s;
}

const isClosed = computed(() => detail.value?.ticket.status === 'closed');

async function refreshList() {
  tickets.value = await ticketService.listMine();
}

async function loadDetail(id: number) {
  detail.value = await ticketService.getTicket(id);
}

async function boot() {
  loading.value = true;
  err.value = '';
  try {
    await refreshList();
    if (tickets.value.length > 0) {
      selectedId.value = tickets.value[0].id;
      await loadDetail(selectedId.value);
    } else {
      selectedId.value = null;
      detail.value = null;
    }
  } catch (e) {
    err.value = e instanceof Error ? e.message : '加载失败';
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void boot();
});

watch(selectedId, async (id) => {
  if (id === null) {
    detail.value = null;
    return;
  }
  err.value = '';
  try {
    await loadDetail(id);
  } catch (e) {
    err.value = e instanceof Error ? e.message : '加载会话失败';
  }
});

function selectSession(id: number) {
  selectedId.value = id;
}

async function onNewSession() {
  const title = window.prompt('新会话标题', '新会话');
  if (title === null) return;
  const t = title.trim() || '新会话';
  err.value = '';
  try {
    const created = await ticketService.createTicket(t);
    await refreshList();
    selectedId.value = created.id;
    await loadDetail(created.id);
  } catch (e) {
    err.value = e instanceof Error ? e.message : '创建失败';
  }
}

async function onSend() {
  const text = draft.value.trim();
  if (!text || selectedId.value === null || isClosed.value) return;
  sending.value = true;
  err.value = '';
  try {
    await ticketService.postMessage(selectedId.value, text);
    draft.value = '';
    await loadDetail(selectedId.value);
    try {
      await ticketService.requestAiReply(selectedId.value);
      await loadDetail(selectedId.value);
    } catch (aiErr) {
      err.value = aiErr instanceof Error ? aiErr.message : '智能回答失败';
    }
    await refreshList();
  } catch (e) {
    err.value = e instanceof Error ? e.message : '发送失败';
  } finally {
    sending.value = false;
  }
}

async function onTransfer() {
  if (selectedId.value === null || isClosed.value) return;
  err.value = '';
  try {
    await ticketService.transferToHuman(selectedId.value);
    await refreshList();
    await loadDetail(selectedId.value);
  } catch (e) {
    err.value = e instanceof Error ? e.message : '转人工失败';
  }
}

function roleLabel(role: string): string {
  if (role === 'user') return '';
  if (role === 'agent') return '坐席';
  return 'AI';
}

function isUser(role: string): boolean {
  return role === 'user';
}
</script>

<template>
  <AppShell title="员工端" active="employee">
    <div class="emp">
      <aside class="emp__list" aria-label="会话列表">
        <div class="emp__list-head">
          <span class="emp__list-title">会话</span>
        </div>
        <button type="button" class="emp__new" @click="onNewSession">新建会话</button>
        <p class="emp__filt" role="presentation">全部 · 进行中 · 已结束</p>
        <p v-if="err" class="emp__err" role="alert">{{ err }}</p>
        <p v-if="!loading && tickets.length === 0" class="emp__empty">暂无会话，点击「新建会话」开始。</p>
        <button
          v-for="s in tickets"
          :key="s.id"
          type="button"
          class="emp__row"
          :class="{ 'emp__row--on': s.id === selectedId }"
          @click="selectSession(s.id)"
        >
          <div class="emp__row-title">{{ s.title }}</div>
          <div class="emp__row-meta">{{ fmt(s.updated_at) }}</div>
          <span
            class="emp__tag"
            :class="{
              'emp__tag--proc': s.status === 'processing',
              'emp__tag--open': s.status === 'open',
              'emp__tag--done': s.status === 'closed',
            }"
          >
            {{ statusLabel(s.status) }}
          </span>
        </button>
      </aside>
      <section class="emp__chat" aria-label="当前会话">
        <template v-if="loading">
          <p class="emp__loading">加载中…</p>
        </template>
        <template v-else-if="detail">
          <header class="emp__hdr">
            <span class="emp__hdr-title">{{ detail.ticket.title }} · {{ detail.ticket.ticket_no }}</span>
            <div class="emp__hdr-actions">
              <RouterLink class="emp__link" to="/app/knowledge">知识库</RouterLink>
              <button type="button" class="emp__human" :disabled="isClosed" @click="onTransfer">
                转人工
              </button>
            </div>
          </header>
          <div class="emp__msgs" role="log" aria-live="polite">
            <template v-for="m in detail.messages" :key="m.id">
              <div
                class="emp__row-msg"
                :class="{ 'emp__row-msg--user': isUser(m.sender_role) }"
              >
                <div
                  class="emp__bubble"
                  :class="isUser(m.sender_role) ? 'emp__bubble--user' : 'emp__bubble--ai'"
                >
                  <span v-if="roleLabel(m.sender_role)" class="emp__role">{{
                    roleLabel(m.sender_role)
                  }}</span>
                  {{ m.body }}
                </div>
              </div>
            </template>
          </div>
          <footer class="emp__input" :class="{ 'emp__input--locked': isClosed }">
            <template v-if="isClosed">
              <p class="emp__closed-note" role="status">
                此会话已结束，仅可查看历史记录（PRD：closed 禁止发送）。
              </p>
            </template>
            <template v-else>
              <label class="emp__sr" for="emp-msg">输入消息</label>
              <textarea
                id="emp-msg"
                v-model="draft"
                class="emp__textarea"
                rows="2"
                placeholder="输入问题后点击发送"
                :disabled="sending"
                @keydown.enter.exact.prevent="onSend"
              />
              <button type="button" class="emp__send" :disabled="sending" @click="onSend">
                {{ sending ? '发送中…' : '发送' }}
              </button>
            </template>
          </footer>
        </template>
        <template v-else>
          <p class="emp__empty-main">请选择左侧会话或新建会话。</p>
        </template>
      </section>
    </div>
  </AppShell>
</template>

<style scoped>
.emp {
  display: flex;
  height: 100%;
  min-height: calc(100vh - 56px);
}
.emp__list {
  width: 320px;
  flex-shrink: 0;
  padding: 16px;
  background: var(--color-surface-elevated);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.emp__list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.emp__list-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}
.emp__new {
  height: 36px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-primary);
  background: var(--color-bg-card);
  color: var(--color-primary);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  font-family: var(--font-sans);
  transition:
    background 0.12s ease,
    color 0.12s ease;
}
.emp__new:hover {
  background: var(--color-row-selected);
}
.emp__new:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}
.emp__filt {
  margin: 0;
  font-size: 0.6875rem;
  color: var(--color-text-muted);
}
.emp__err {
  margin: 0;
  padding: 8px;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  color: #991b1b;
  background: #fef2f2;
  border: 1px solid #fecaca;
}
.emp__empty {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
}
.emp__empty-main {
  margin: 0;
  padding: 24px;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}
.emp__loading {
  margin: 0;
  padding: 24px;
  color: var(--color-text-secondary);
}
.emp__row {
  padding: 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  display: flex;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
  transition: border-color 0.12s ease;
  text-align: left;
  font-family: var(--font-sans);
}
.emp__row:hover {
  border-color: color-mix(in srgb, var(--color-primary) 25%, var(--color-border));
}
.emp__row:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}
.emp__row--on {
  background: var(--color-row-selected);
  border-color: var(--color-row-selected-border);
}
.emp__row-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text);
}
.emp__row-meta {
  font-size: 0.6875rem;
  color: var(--color-text-secondary);
}
.emp__tag {
  font-size: 0.625rem;
  font-weight: 600;
  align-self: flex-start;
  padding: 2px 6px;
  border-radius: 4px;
}
.emp__tag--proc {
  background: var(--color-tag-processing-bg);
  color: var(--color-tag-processing-text);
}
.emp__tag--open {
  background: #fff7ed;
  color: #c2410c;
}
.emp__tag--done {
  background: var(--color-tag-closed-bg);
  color: var(--color-tag-closed-text);
}
.emp__chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--color-bg-card);
}
.emp__hdr {
  min-height: 52px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border-bottom: 1px solid var(--color-border);
  gap: 12px;
}
.emp__hdr-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text);
  min-width: 0;
}
.emp__hdr-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}
.emp__link {
  font-size: 0.8125rem;
  color: var(--color-primary);
  text-decoration: none;
  border-radius: 4px;
}
.emp__link:hover {
  text-decoration: underline;
}
.emp__link:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}
.emp__human {
  height: 32px;
  padding: 0 14px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  font-family: var(--font-sans);
}
.emp__human:hover:not(:disabled) {
  background: var(--color-primary-hover);
}
.emp__human:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.emp__human:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}
.emp__msgs {
  flex: 1;
  overflow: auto;
  padding: 20px;
  background: var(--color-surface-elevated);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.emp__row-msg {
  display: flex;
  justify-content: flex-start;
}
.emp__row-msg--user {
  justify-content: flex-end;
}
.emp__bubble {
  max-width: min(520px, 100%);
  padding: 10px 12px;
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.emp__bubble--user {
  background: var(--color-primary);
  color: #fff;
}
.emp__bubble--ai {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  color: var(--color-text);
}
.emp__role {
  display: inline-block;
  margin-right: 6px;
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--color-text-muted);
  vertical-align: middle;
}
.emp__input {
  flex-shrink: 0;
  min-height: 88px;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--color-border);
  background: var(--color-bg-card);
}
.emp__input--locked {
  align-items: center;
  min-height: 72px;
}
.emp__closed-note {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
}
.emp__sr {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}
.emp__textarea {
  flex: 1;
  min-height: 56px;
  resize: vertical;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font-size: 0.8125rem;
  font-family: var(--font-sans);
  color: var(--color-text);
  line-height: 1.45;
}
.emp__textarea::placeholder {
  color: var(--color-text-muted);
}
.emp__textarea:focus {
  outline: none;
  border-color: color-mix(in srgb, var(--color-primary) 55%, var(--color-border));
  box-shadow: var(--shadow-focus);
}
.emp__send {
  width: 88px;
  height: 40px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: #fff;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  font-family: var(--font-sans);
  flex-shrink: 0;
}
.emp__send:hover:not(:disabled) {
  background: var(--color-primary-hover);
}
.emp__send:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.emp__send:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}
</style>
