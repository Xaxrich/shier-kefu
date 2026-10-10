<script setup lang="ts">
import { onMounted, ref } from 'vue';
import AppShell from '@/components/AppShell.vue';
import * as knowledgeService from '@/services/knowledgeService';
import type { IngestJob, KbDocument } from '@/types/kb';

const documents = ref<KbDocument[]>([]);
const jobs = ref<IngestJob[]>([]);
const selectedDocId = ref<number | null>(null);
const loading = ref(true);
const uploading = ref(false);
const err = ref('');
const fileInput = ref<HTMLInputElement | null>(null);

function fmt(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false });
  } catch {
    return iso;
  }
}

function statusText(s: string): string {
  const m: Record<string, string> = {
    pending: '等待',
    processing: '处理中',
    success: '成功',
    failed: '失败',
  };
  return m[s] || s;
}

function cellMark(ok: boolean, status: string): string {
  if (status === 'failed') return '✗';
  if (status === 'success' && ok) return '✓';
  if (status === 'success') return '—';
  return '…';
}

async function refresh() {
  documents.value = await knowledgeService.listDocuments();
  jobs.value = await knowledgeService.listJobs();
}

async function boot() {
  loading.value = true;
  err.value = '';
  try {
    await refresh();
    if (documents.value.length > 0) {
      selectedDocId.value = documents.value[0].id;
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

function selectDoc(id: number) {
  selectedDocId.value = id;
}

function triggerFile() {
  fileInput.value?.click();
}

async function onFileChange(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;
  await doUpload(file);
}

async function onDrop(ev: DragEvent) {
  ev.preventDefault();
  const file = ev.dataTransfer?.files?.[0];
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.md')) {
    err.value = '仅支持 .md 文件';
    return;
  }
  await doUpload(file);
}

function onDragOver(ev: DragEvent) {
  ev.preventDefault();
}

async function doUpload(file: File) {
  if (!file.name.toLowerCase().endsWith('.md')) {
    err.value = '仅支持 .md 文件';
    return;
  }
  uploading.value = true;
  err.value = '';
  try {
    await knowledgeService.uploadMarkdown(file);
    await refresh();
    selectedDocId.value = documents.value[0]?.id ?? null;
  } catch (e) {
    err.value = e instanceof Error ? e.message : '上传失败';
  } finally {
    uploading.value = false;
  }
}

async function onRetry(job: IngestJob) {
  err.value = '';
  try {
    await knowledgeService.retryJob(job.id);
    await refresh();
  } catch (e) {
    err.value = e instanceof Error ? e.message : '重试失败';
  }
}
</script>

<template>
  <AppShell title="知识库" active="knowledge">
    <div class="kb">
      <aside class="kb__tree" aria-label="文件目录">
        <div class="kb__tree-title kb__tree-head">
          <span>已上传</span>
        </div>
        <p class="kb__note">入库为开发桩（同步写入）；向量检索与 RAG 在 B4 接入。</p>
        <p v-if="loading" class="kb__hint">加载中…</p>
        <template v-else-if="documents.length === 0">
          <p class="kb__empty-tree">暂无文件，请上传 .md</p>
        </template>
        <button
          v-for="d in documents"
          :key="d.id"
          type="button"
          class="kb__file"
          :class="{ 'kb__file--on': d.id === selectedDocId }"
          @click="selectDoc(d.id)"
        >
          {{ d.original_filename }}
        </button>
      </aside>
      <div class="kb__main">
        <section
          class="kb__upload"
          aria-label="上传 Markdown"
          @drop="onDrop"
          @dragover="onDragOver"
        >
          <p class="kb__upload-text">拖拽或选择文件，仅支持 <strong>.md</strong></p>
          <input
            ref="fileInput"
            type="file"
            accept=".md,text/markdown"
            class="kb__file-input"
            @change="onFileChange"
          />
          <button
            type="button"
            class="kb__upload-btn"
            :disabled="uploading"
            @click="triggerFile"
          >
            {{ uploading ? '上传中…' : '选择文件' }}
          </button>
        </section>
        <p v-if="err" class="kb__err" role="alert">{{ err }}</p>
        <section class="kb__table-wrap" aria-label="入库任务">
          <div class="kb__thead">
            <span>文件名</span>
            <span>上传时间</span>
            <span>状态</span>
            <span>向量</span>
            <span>关键词</span>
            <span>元数据</span>
            <span>操作</span>
          </div>
          <template v-if="!loading && jobs.length === 0">
            <div class="kb__row kb__row--empty">暂无入库任务</div>
          </template>
          <div
            v-for="j in jobs"
            :key="j.id"
            class="kb__row"
            :class="{ 'kb__row--bad': j.status === 'failed' }"
          >
            <span>{{ j.filename }}</span>
            <span>{{ fmt(j.created_at) }}</span>
            <span :class="j.status === 'success' ? 'kb__ok' : j.status === 'failed' ? 'kb__bad' : ''">
              {{ statusText(j.status) }}
            </span>
            <span>{{ cellMark(j.vector_ok, j.status) }}</span>
            <span>{{ cellMark(j.keyword_ok, j.status) }}</span>
            <span>{{ cellMark(j.metadata_ok, j.status) }}</span>
            <span class="kb__ops">
              <button
                v-if="j.status === 'failed'"
                type="button"
                class="kb__retry"
                @click="onRetry(j)"
              >
                重试
              </button>
              <span v-else class="kb__dash">—</span>
            </span>
          </div>
        </section>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.kb {
  display: flex;
  height: 100%;
  min-height: calc(100vh - 56px);
}
.kb__tree {
  width: 260px;
  flex-shrink: 0;
  padding: 16px;
  background: var(--color-surface-elevated);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.8125rem;
}
.kb__tree-title {
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
}
.kb__tree-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.kb__note {
  margin: 0 0 8px;
  font-size: 0.6875rem;
  line-height: 1.4;
  color: var(--color-text-muted);
}
.kb__hint {
  margin: 0;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}
.kb__empty-tree {
  margin: 0;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}
.kb__file {
  padding: 8px 10px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  text-align: left;
  padding-left: 12px;
  color: var(--color-text-secondary);
  font-size: 0.6875rem;
  cursor: pointer;
  font-family: var(--font-sans);
}
.kb__file:hover {
  background: #fafafa;
}
.kb__file--on {
  color: var(--color-primary);
  font-weight: 600;
  background: var(--color-row-selected);
}
.kb__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 20px 24px;
  gap: 16px;
}
.kb__upload {
  border: 1px dashed color-mix(in srgb, var(--color-primary) 35%, var(--color-border));
  border-radius: var(--radius-md);
  background: var(--color-bg-card);
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.kb__upload-text {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
}
.kb__file-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}
.kb__upload-btn {
  height: 36px;
  padding: 0 16px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  font-family: var(--font-sans);
}
.kb__upload-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
.kb__upload-btn:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}
.kb__err {
  margin: 0;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  color: #991b1b;
  background: #fef2f2;
  border: 1px solid #fecaca;
}
.kb__table-wrap {
  flex: 1;
  min-height: 200px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-elevated);
  overflow: auto;
}
.kb__thead {
  display: grid;
  grid-template-columns: 1.4fr 1fr 0.6fr 0.5fr 0.5fr 0.5fr 0.6fr;
  gap: 8px;
  padding: 10px 12px;
  font-size: 0.625rem;
  font-weight: 600;
  color: #52525b;
  background: var(--color-bg-page);
  border-bottom: 1px solid var(--color-border);
}
.kb__row {
  display: grid;
  grid-template-columns: 1.4fr 1fr 0.6fr 0.5fr 0.5fr 0.5fr 0.6fr;
  gap: 8px;
  align-items: center;
  padding: 10px 12px;
  font-size: 0.6875rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-card);
}
.kb__row--empty {
  display: block;
  text-align: center;
  color: var(--color-text-secondary);
  padding: 16px;
}
.kb__row--bad {
  background: #fff7ed;
  color: #9a3412;
}
.kb__ok {
  color: #15803d;
  font-weight: 600;
}
.kb__bad {
  font-weight: 600;
}
.kb__ops {
  display: flex;
  align-items: center;
}
.kb__dash {
  color: var(--color-text-muted);
}
.kb__retry {
  justify-self: start;
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  border-radius: var(--radius-sm);
  padding: 4px 10px;
  font-size: 0.6875rem;
  cursor: pointer;
  font-family: var(--font-sans);
}
.kb__retry:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}
</style>
