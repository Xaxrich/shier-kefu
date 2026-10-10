import api from './api';
import type { ApiEnvelope } from '@/types/auth';
import type { IngestJob, KbDocument, UploadKbResult } from '@/types/kb';

function unwrap<T>(env: ApiEnvelope<T>): T {
  if (!env.success || env.data === null) {
    throw new Error(env.error || env.message || '请求失败');
  }
  return env.data;
}

export async function listDocuments(): Promise<KbDocument[]> {
  const { data } = await api.get<ApiEnvelope<KbDocument[]>>('/api/kb/documents');
  return unwrap(data);
}

export async function listJobs(): Promise<IngestJob[]> {
  const { data } = await api.get<ApiEnvelope<IngestJob[]>>('/api/kb/jobs');
  return unwrap(data);
}

export async function uploadMarkdown(file: File): Promise<UploadKbResult> {
  const fd = new FormData();
  fd.append('file', file);
  const { data } = await api.post<ApiEnvelope<UploadKbResult>>('/api/kb/upload', fd);
  return unwrap(data);
}

export async function retryJob(jobId: number): Promise<IngestJob> {
  const { data } = await api.post<ApiEnvelope<IngestJob>>(`/api/kb/jobs/${jobId}/retry`);
  return unwrap(data);
}
