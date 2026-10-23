import { API } from './api';
import { editionFromEnv, isFamilyEdition } from './edition';
import { currentHelpScreen, lastClientError, recordClientError } from './lastClientError';
export { familyHelpLabels } from './familyHelpCopy';
export { currentHelpScreen, lastClientError } from './lastClientError';
export {
  HELP_FILE_ACCEPT,
  HELP_MAX_FILE_BYTES,
  HELP_MAX_FILES,
  HELP_MAX_VOICE_BYTES,
  formatHelpBytes,
  inferHelpMime,
  validateHelpFile,
} from './familyHelpUpload';
import {
  HELP_MAX_FILES,
  HELP_MAX_VOICE_BYTES,
  formatHelpBytes,
  validateHelpFile,
} from './familyHelpUpload';

export function isFamilyHelpSurface(edition = editionFromEnv()): boolean {
  return isFamilyEdition(edition);
}

export type HelpStatus = 'new' | 'answered' | 'closed';

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
  usage_tokens?: number;
};

export type HelpUsage = {
  reply_tokens?: number;
  charged_to?: string;
  note?: string;
};

export type { FamilyRequestType } from './familyHelpRequest';
export { FAMILY_REQUEST_OFFER, classifyFamilyRequest, familyRequestOffer } from './familyHelpRequest';

export type HelpTicket = {
  id: string;
  edition: string;
  sender: string;
  message: string;
  transcript?: string;
  transcript_pending?: boolean;
  attachments_hidden?: boolean;
  attachments_revealed?: boolean;
  attachment_count?: number;
  request_type?: string;
  current_screen?: string;
  last_error?: string;
  context?: Array<{ role: string; content: string }>;
  status: HelpStatus;
  created_at: string;
  updated_at: string;
  attachments?: HelpAttachment[];
  replies?: HelpReply[];
  drafts?: HelpReply[];
  usage?: HelpUsage;
};

export function attachmentUrl(ticketId: string, attachmentId: string, founder: boolean): string {
  const base = founder
    ? `${API}/family-help/inbox/${ticketId}/attachments/${attachmentId}`
    : `${API}/family-help/tickets/${ticketId}/attachments/${attachmentId}`;
  return `${base}?_v=${Date.now()}`;
}

export async function fetchHelpStatus(): Promise<any> {
  const res = await fetch(`${API}/family-help/status`, { cache: 'no-store', credentials: 'include' });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchOwnTickets(): Promise<HelpTicket[]> {
  const res = await fetch(`${API}/family-help/tickets`, { cache: 'no-store', credentials: 'include' });
  if (!res.ok) return [];
  const data = await res.json();
  return data.tickets || [];
}

export async function fetchInbox(edition?: string): Promise<HelpTicket[]> {
  const q = edition ? `?edition=${encodeURIComponent(edition)}` : '';
  const res = await fetch(`${API}/family-help/inbox${q}`, { cache: 'no-store', credentials: 'include' });
  if (!res.ok) return [];
  const data = await res.json();
  return data.tickets || [];
}

export async function retryTranscript(ticketId: string, founder: boolean, language?: string): Promise<HelpTicket | null> {
  const path = founder
    ? `${API}/family-help/inbox/${ticketId}/transcribe`
    : `${API}/family-help/tickets/${ticketId}/transcribe`;
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ language: language || null }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return null;
  return data.ticket || null;
}

export async function revealInboxAttachments(ticketId: string): Promise<HelpTicket | null> {
  const res = await fetch(`${API}/family-help/inbox/${ticketId}/reveal-attachments`, {
    method: 'POST',
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return null;
  return data.ticket || null;
}

export async function createHelpTicket(input: {
  message: string;
  history: Array<{ role: string; content: string }>;
  files: File[];
  voice?: Blob | null;
  voiceName?: string;
  language?: string | null;
  requestType?: string | null;
  currentScreen?: string | null;
  lastError?: string | null;
}): Promise<{ ok: boolean; ticket?: HelpTicket; detail?: string }> {
  const rejected: string[] = [];
  const kept: File[] = [];
  for (const file of input.files || []) {
    const check = validateHelpFile(file);
    if (check.ok) kept.push(file);
    else rejected.push(`${file.name}: ${check.reason}`);
  }
  if (input.voice && input.voice.size > HELP_MAX_VOICE_BYTES) {
    return { ok: false, detail: `el audio supera ${formatHelpBytes(HELP_MAX_VOICE_BYTES)}` };
  }
  if (kept.length > HELP_MAX_FILES) {
    return { ok: false, detail: `máximo ${HELP_MAX_FILES} archivos` };
  }
  if (rejected.length && !kept.length && (input.files || []).length) {
    return { ok: false, detail: rejected.join(' ') };
  }
  const body = new FormData();
  body.append('message', input.message || '');
  body.append('history_json', JSON.stringify(input.history || []));
  if (input.language) body.append('language', input.language);
  if (input.requestType) body.append('request_type', input.requestType);
  const screen = (input.currentScreen || currentHelpScreen()).trim();
  const recentError = (input.lastError || lastClientError()).trim();
  if (screen) body.append('current_screen', screen);
  if (recentError) body.append('last_error', recentError);
  if (input.voice) {
    body.append('voice', input.voice, input.voiceName || 'recording.webm');
  }
  for (const file of kept) body.append('files', file, file.name);
  const res = await fetch(`${API}/family-help/tickets`, {
    method: 'POST',
    body,
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail || `HTTP ${res.status}`;
    recordClientError(detail);
    return { ok: false, detail };
  }
  return { ok: true, ticket: data.ticket };
}
