import axios from 'axios';
import api from './api';
import type { ApiEnvelope } from '@/types/auth';
import type { AiReplyResult, TicketDetail, TicketSummary } from '@/types/ticket';

function unwrap<T>(env: ApiEnvelope<T>): T {
  if (!env.success || env.data === null) {
    throw new Error(env.error || env.message || '请求失败');
  }
  return env.data;
}

function apiErrorMessage(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const data = e.response?.data as { detail?: string } | undefined;
    if (data?.detail && typeof data.detail === 'string') return data.detail;
  }
  if (e instanceof Error) return e.message;
  return '请求失败';
}

export async function listMine(): Promise<TicketSummary[]> {
  const { data } = await api.get<ApiEnvelope<TicketSummary[]>>('/api/tickets/mine');
  return unwrap(data);
}

export async function listQueue(): Promise<TicketSummary[]> {
  const { data } = await api.get<ApiEnvelope<TicketSummary[]>>('/api/tickets/queue');
  return unwrap(data);
}

export async function getTicket(id: number): Promise<TicketDetail> {
  const { data } = await api.get<ApiEnvelope<TicketDetail>>(`/api/tickets/${id}`);
  return unwrap(data);
}

export async function createTicket(title: string): Promise<TicketSummary> {
  const { data } = await api.post<ApiEnvelope<TicketSummary>>('/api/tickets/', { title });
  return unwrap(data);
}

export async function postMessage(ticketId: number, content: string): Promise<void> {
  const { data } = await api.post<ApiEnvelope<unknown>>(`/api/tickets/${ticketId}/messages`, {
    content,
  });
  unwrap(data);
}

export async function transferToHuman(ticketId: number): Promise<TicketSummary> {
  const { data } = await api.post<ApiEnvelope<TicketSummary>>(
    `/api/tickets/${ticketId}/transfer`,
    {},
  );
  return unwrap(data);
}

export async function patchTicket(
  ticketId: number,
  body: { category?: string | null; close?: boolean },
): Promise<TicketSummary> {
  const { data } = await api.patch<ApiEnvelope<TicketSummary>>(`/api/tickets/${ticketId}`, body);
  return unwrap(data);
}

/** 基于最后一条用户消息走 QA / RAG 管线并写入 AI 气泡（需后端配置 llm_api_key）。 */
export async function requestAiReply(ticketId: number): Promise<AiReplyResult> {
  try {
    const { data } = await api.post<ApiEnvelope<AiReplyResult>>(
      `/api/tickets/${ticketId}/ai-reply`,
      {},
      { timeout: 120000 },
    );
    return unwrap(data);
  } catch (e) {
    throw new Error(apiErrorMessage(e));
  }
}
