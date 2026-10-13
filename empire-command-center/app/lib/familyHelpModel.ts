export const REQUEST_TYPES = ['adjust', 'fix', 'create'] as const;
export type RequestType = (typeof REQUEST_TYPES)[number];

export const LOG_STATUSES = ['new', 'planned', 'in_progress', 'done', 'declined'] as const;
export type LogStatus = (typeof LOG_STATUSES)[number];

export const TYPE_LABEL: Record<RequestType, string> = {
  adjust: 'Adjust',
  fix: 'Fix',
  create: 'Create',
};

export const STATUS_LABEL: Record<LogStatus, string> = {
  new: 'New',
  planned: 'Planned',
  in_progress: 'In progress',
  done: 'Done',
  declined: 'Declined',
};

export const EDITION_WHO: Record<string, string> = {
  amp: 'Juan / Max-e',
  maxine: 'Camilo / Maxine',
};

export type HelpAttachment = {
  id: string;
  kind: string;
  filename: string;
  content_type?: string;
  size?: number;
};

export type HelpReply = {
  id: string;
  author: string;
  body: string;
  created_at: string;
};

export type WorkLogEntry = {
  id: string;
  kind: string;
  body: string;
  href?: string | null;
  href_label?: string | null;
  created_at: string;
};

export type HelpTicket = {
  id: string;
  edition: string;
  sender: string;
  who?: string;
  who_label?: string;
  assistant?: string;
  message: string;
  transcript?: string;
  summary?: string;
  context?: Array<{ role: string; content: string }>;
  status?: string;
  created_at: string;
  updated_at?: string;
  attachments?: HelpAttachment[];
  attachment_count?: number;
  replies?: HelpReply[];
  request_type?: RequestType;
  type?: RequestType;
  type_suggested?: RequestType;
  type_edited?: boolean;
  log_status?: LogStatus;
  studio_status?: LogStatus;
  unread?: boolean;
  seen_at?: string | null;
  organizer_task_id?: string | null;
  log?: WorkLogEntry[];
};

export function whoLabel(ticket: Pick<HelpTicket, 'edition' | 'who_label' | 'who'>): string {
  return ticket.who_label || EDITION_WHO[ticket.edition] || ticket.who || ticket.edition;
}

export function typeOf(ticket: HelpTicket): RequestType {
  const raw = ticket.request_type || ticket.type || ticket.type_suggested || 'adjust';
  return (REQUEST_TYPES as readonly string[]).includes(raw) ? (raw as RequestType) : 'adjust';
}

export function statusOf(ticket: HelpTicket): LogStatus {
  const raw = ticket.log_status || ticket.studio_status || 'new';
  return (LOG_STATUSES as readonly string[]).includes(raw) ? (raw as LogStatus) : 'new';
}

export type DraftKind = 'reply' | 'manual';

export type DraftScreen = {
  id: string;
  name: string;
  href: string;
  where?: string;
  label?: string;
  link?: string;
};

export type DraftStep = {
  n: number;
  text: string;
  href?: string | null;
  label?: string | null;
};

export type FamilyDraft = {
  kind: DraftKind;
  title?: string | null;
  body: string;
  steps?: DraftStep[];
  screens?: DraftScreen[];
  edition?: string;
  ticket_id?: string;
  model_used?: string;
  included_model?: boolean;
  would_send?: boolean;
  saved?: boolean;
};

export type HelpGuide = {
  id: string;
  edition: string;
  ticket_id?: string | null;
  title: string;
  body: string;
  steps?: DraftStep[];
  created_at: string;
  updated_at?: string;
};

export function usesManito(text: string): boolean {
  return /\bmanito\b/i.test(text || '');
}

export function hasForbiddenNames(text: string): boolean {
  return /\b(juan|camilo)\b/i.test(text || '');
}
