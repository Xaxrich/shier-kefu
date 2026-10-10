<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import AppShell from '@/components/AppShell.vue';
import * as ticketService from '@/services/ticketService';
import type { TicketDetail, TicketSummary } from '@/types/ticket';

type TabKey = 'human' | 'ai';

const queue = ref<TicketSummary[]>([]);
const selectedId = ref<number | null>(null);
const detail = ref<TicketDetail | null>(null);
const loading = ref(true);
const sending = ref(false);
const err = ref('');
const draftHuman = ref('');
const draftAi = ref('');
const generatingAi = ref(false);
const activeTab = ref<TabKey>('human');

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

function queueLine(t: TicketSummary): string {
  return `${t.ticket_no} · ${t.title}`;
}

function whoLabel(role: string): string {
  if (role === 'user') return '员工';
  if (role === 'agent') return '坐席';
  return 'AI';
}

function whoClass(role: string): string {
  if (role === 'user') return 'ag__who--emp';
  if (role === 'agent') return 'ag__who--ag';
  return 'ag__who--ai';
}

async function loadQueue() {
  queue.value = await ticketService.listQueue();
}

async function loadDetail(id: number) {
  detail.value = await ticketService.getTicket(id);
}

async function boot() {
  loading.value = true;
  err.value = '';
  try {
    await loadQueue();
    if (queue.value.length > 0) {
      selectedId.value = queue.value[0].id;
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
    err.value = e instanceof Error ? e.message : '加载工单失败';
  }
});

function selectTicket(id: number) {
  selectedId.value = id;
}

function setTab(tab: TabKey) {
  activeTab.value = tab;
}

async function onSendHuman() {
  const text = draftHuman.value.trim();
  if (!text || selectedId.value === null || isClosed.value) return;
  sending.value = true;
  err.value = '';
  try {
    await ticketService.postMessage(selectedId.value, text);
    draftHuman.value = '';
    await loadDetail(selectedId.value);
    await loadQueue();
  } catch (e) {
    err.value = e instanceof Error ? e.message : '发送失败';
  } finally {
    sending.value = false;
  }
}

async function onCategoryChange(ev: Event) {
  const v = (ev.target as HTMLSelectElement).value;
  if (selectedId.value === null || isClosed.value) return;
  err.value = '';
  try {
    await ticketService.patchTicket(selectedId.value, { category: v });
    await loadDetail(selectedId.value);
    await loadQueue();
  } catch (e) {
    err.value = e instanceof Error ? e.message : '更新分类失败';
  }
}

async function onCloseTicket() {
  if (selectedId.value === null || isClosed.value) return;
  if (!window.confirm('确定结束工单？员工端将不可再发消息。')) return;
  err.value = '';
  try {
    await ticketService.patchTicket(selectedId.value, { close: true });
    await loadQueue();
    await loadDetail(selectedId.value);
  } catch (e) {
    err.value = e instanceof Error ? e.message : '结束工单失败';
  }
}

async function onGenerateAi() {
  if (selectedId.value === null || isClosed.value) return;
  generatingAi.value = true;
  err.value = '';
  try {
    const r = await ticketService.requestAiReply(selectedId.value);
    draftAi.value = r.answer;
    await loadDetail(selectedId.value);
    await loadQueue();
  } catch (e) {
    err.value = e instanceof Error ? e.message : '智能回答失败';
  } finally {
    generatingAi.value = false;
  }
}
</script>

<template>
  <AppShell title="坐席端" active="agent">
    <div class="ag">
      <aside class="ag__queue" aria-label="工单队列">
        <div class="ag__queue-head">
          <p class="ag__hint">筛选：待处理 · 处理中 · 已结束 · 关键字</p>
        </div>
        <div class="ag__thead" role="presentation">工单号 · 摘要 · 状态 · 时间</div>
        <p v-if="err && !detail" class="ag__err">{{ err }}</p>
        <p v-if="!loading && queue.length === 0" class="ag__empty">暂无工单。</p>
        <button
          v-for="t in queue"
          :key="t.id"
          type="button"
          class="ag__ticket"
          :class="{ 'ag__ticket--active': t.id === selectedId }"
          @click="selectTicket(t.id)"
        >
          <div class="ag__t-line">{{ queueLine(t) }}</div>
          <div class="ag__t-meta" :class="{ 'ag__t-meta--muted': t.status === 'closed' }">
            {{ statusLabel(t.status) }} · {{ fmt(t.updated_at) }}
          </div>
        </button>
      </aside>

      <section class="ag__thread" aria-label="工单对话">
        <template v-if="loading">
          <p class="ag__loading">加载中…</p>
        </template>
        <template v-else-if="detail">
          <p v-if="err" class="ag__err-inline">{{ err }}</p>
          <div class="ag__tabs" role="tablist">
            <button
              type="button"
              class="ag__tab"
              :class="{ 'ag__tab--on': activeTab === 'human' }"
              role="tab"
              :aria-selected="activeTab === 'human'"
              @click="setTab('human')"
            >
              人工回复
            </button>
            <button
              type="button"
              class="ag__tab"
              :class="{ 'ag__tab--on': activeTab === 'ai' }"
              role="tab"
              :aria-selected="activeTab === 'ai'"
              @click="setTab('ai')"
            >
              智能回答
            </button>
          </div>
          <div class="ag__msgs" role="log">
            <p v-for="m in detail.messages" :key="m.id" class="ag__line">
              <span class="ag__who" :class="whoClass(m.sender_role)">{{ whoLabel(m.sender_role) }}</span>{{ m.body }}
            </p>
          </div>
          <footer v-if="activeTab === 'human'" class="ag__foot">
            <label class="ag__sr" for="ag-reply">人工回复</label>
            <textarea
              id="ag-reply"
              v-model="draftHuman"
              class="ag__textarea"
              rows="2"
              placeholder="输入人工回复，将同步给员工…"
              :disabled="sending || isClosed"
            />
            <button
              type="button"
              class="ag__send"
              :disabled="sending || isClosed"
              @click="onSendHuman"
            >
              {{ sending ? '发送中…' : '发送' }}
            </button>
          </footer>
          <footer v-else class="ag__foot ag__foot--ai">
            <label class="ag__sr" for="ag-ai">智能回答</label>
            <textarea
              id="ag-ai"
              v-model="draftAi"
              class="ag__textarea"
              rows="2"
              readonly
              placeholder="点击「生成」：基于员工最后一条消息调用检索生成管线，结果会出现在上方对话区"
            />
            <button
              type="button"
              class="ag__send"
              :disabled="generatingAi || isClosed"
              @click="onGenerateAi"
            >
              {{ generatingAi ? '生成中…' : '生成' }}
            </button>
          </footer>
        </template>
        <template v-else>
          <p class="ag__empty-main">请选择左侧工单。</p>
        </template>
      </section>

      <aside v-if="detail" class="ag__panel" aria-label="工单属性">
        <div class="ag__panel-block">
          <div class="ag__panel-label">工单号</div>
          <div class="ag__panel-value">{{ detail.ticket.ticket_no }}</div>
        </div>
        <div class="ag__panel-block">
          <div class="ag__panel-label">状态</div>
          <div class="ag__panel-value">{{ statusLabel(detail.ticket.status) }}</div>
        </div>
        <div class="ag__panel-block">
          <label class="ag__panel-label" for="ag-cat">分类</label>
          <select
            id="ag-cat"
            class="ag__select"
            :value="detail.ticket.category ?? '其他'"
            :disabled="isClosed"
            @change="onCategoryChange"
          >
            <option value="产品咨询">产品咨询</option>
            <option value="账号问题">账号问题</option>
            <option value="故障报修">故障报修</option>
            <option value="其他">其他</option>
          </select>
        </div>
        <button type="button" class="ag__end" :disabled="isClosed" @click="onCloseTicket">
          结束工单
        </button>
        <p class="ag__warn">结束后员工端不可再发消息（与 PRD 一致）。</p>
      </aside>
    </div>
  </AppShell>
</template>

<style scoped>
.ag {
  display: flex;
  height: 100%;
  min-height: calc(100vh - 56px);
}
.ag__queue {
  width: 280px;
  flex-shrink: 0;
  padding: 12px;
  background: var(--color-surface-elevated);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ag__queue-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.ag__hint {
  margin: 0;
  font-size: 0.6875rem;
  color: var(--color-text-muted);
  flex: 1;
}
.ag__err {
  margin: 0;
  font-size: 0.75rem;
  color: #991b1b;
}
.ag__err-inline {
  margin: 0;
  padding: 8px 16px;
  font-size: 0.75rem;
  color: #991b1b;
  background: #fef2f2;
  border-bottom: 1px solid #fecaca;
}
.ag__empty {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
}
.ag__empty-main {
  margin: 0;
  padding: 24px;
  color: var(--color-text-secondary);
}
.ag__loading {
  margin: 0;
  padding: 24px;
  color: var(--color-text-secondary);
}
.ag__thead {
  font-size: 0.625rem;
  font-weight: 600;
  color: #52525b;
  padding: 8px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}
.ag__ticket {
  padding: 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  cursor: pointer;
  transition: border-color 0.12s ease;
  text-align: left;
  font-family: var(--font-sans);
}
.ag__ticket:hover {
  border-color: color-mix(in srgb, var(--color-primary) 25%, var(--color-border));
}
.ag__ticket:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}
.ag__ticket--active {
  background: var(--color-row-selected);
  border-color: var(--color-row-selected-border);
}
.ag__t-line {
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--color-text);
}
.ag__t-meta {
  font-size: 0.625rem;
  color: var(--color-tag-processing-text);
  margin-top: 2px;
}
.ag__t-meta--muted {
  color: var(--color-tag-closed-text);
}
.ag__thread {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-card);
}
.ag__tabs {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
}
.ag__tab {
  height: 28px;
  padding: 0 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  font-size: 0.75rem;
  color: #52525b;
  cursor: pointer;
  font-family: var(--font-sans);
}
.ag__tab--on {
  background: var(--color-row-selected);
  border-color: transparent;
  color: var(--color-primary);
  font-weight: 600;
}
.ag__tab:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}
.ag__msgs {
  flex: 1;
  overflow: auto;
  padding: 12px 16px;
  background: var(--color-surface-elevated);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ag__line {
  margin: 0;
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--color-text);
}
.ag__who {
  display: inline-block;
  min-width: 2.5rem;
  margin-right: 6px;
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
}
.ag__who--emp {
  color: #64748b;
}
.ag__who--ai {
  color: var(--color-primary);
}
.ag__who--ag {
  color: #0d9488;
}
.ag__foot {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--color-border);
  background: var(--color-bg-card);
}
.ag__sr {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}
.ag__textarea {
  flex: 1;
  min-height: 48px;
  resize: vertical;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font-size: 0.8125rem;
  font-family: var(--font-sans);
}
.ag__textarea:focus {
  outline: none;
  border-color: color-mix(in srgb, var(--color-primary) 55%, var(--color-border));
  box-shadow: var(--shadow-focus);
}
.ag__send {
  width: 72px;
  height: 36px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  font-family: var(--font-sans);
}
.ag__send:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}
.ag__send:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.ag__panel {
  width: 320px;
  flex-shrink: 0;
  padding: 16px;
  border-left: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--color-bg-card);
}
.ag__panel-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ag__panel-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}
.ag__panel-value {
  font-size: 0.8125rem;
  color: var(--color-text);
}
.ag__select {
  height: 36px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  padding: 0 10px;
  font-size: 0.8125rem;
  font-family: var(--font-sans);
  background: var(--color-bg-card);
}
.ag__select:focus {
  outline: none;
  box-shadow: var(--shadow-focus);
}
.ag__end {
  height: 40px;
  margin-top: 4px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-danger);
  background: var(--color-bg-card);
  color: var(--color-danger);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  font-family: var(--font-sans);
}
.ag__end:hover:not(:disabled) {
  background: var(--color-danger-bg);
}
.ag__end:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.ag__end:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-danger) 35%, transparent);
}
.ag__warn {
  margin: 0;
  font-size: 0.6875rem;
  line-height: 1.4;
  color: var(--color-text-muted);
}
</style>
