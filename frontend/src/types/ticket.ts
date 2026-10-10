export type TicketStatus = 'open' | 'processing' | 'closed';

export interface TicketSummary {
  id: number;
  ticket_no: string;
  title: string;
  status: TicketStatus;
  category: string | null;
  created_at: string;
  updated_at: string;
}

export interface MessageItem {
  id: number;
  sender_role: 'user' | 'ai' | 'agent' | string;
  body: string;
  created_at: string;
}

export interface TicketDetail {
  ticket: TicketSummary;
  messages: MessageItem[];
}

/** POST /api/tickets/:id/ai-reply */
export interface AiReplyResult {
  answer: string;
  intent?: string | null;
  meta?: Record<string, unknown>;
}
