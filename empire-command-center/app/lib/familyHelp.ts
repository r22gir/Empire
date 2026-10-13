import { API } from './api';
import type { HelpTicket, LogStatus, RequestType } from './familyHelpModel';

export * from './familyHelpModel';

export function attachmentUrl(ticketId: string, attachmentId: string): string {
  return `${API}/family-help/inbox/${ticketId}/attachments/${attachmentId}?_v=${Date.now()}`;
}

export async function fetchInbox(edition?: string): Promise<HelpTicket[]> {
  const q = edition ? `?edition=${encodeURIComponent(edition)}` : '';
  const res = await fetch(`${API}/family-help/inbox${q}`, { cache: 'no-store', credentials: 'include' });
  if (!res.ok) return [];
  const data = await res.json();
  return data.tickets || [];
}

export async function fetchUnreadCount(): Promise<number> {
  const res = await fetch(`${API}/family-help/unread-count`, { cache: 'no-store', credentials: 'include' });
  if (!res.ok) return 0;
  const data = await res.json();
  return Number(data.unread || 0);
}

export async function fetchTicket(ticketId: string): Promise<HelpTicket | null> {
  const res = await fetch(`${API}/family-help/inbox/${ticketId}`, { cache: 'no-store', credentials: 'include' });
  if (!res.ok) return null;
  const data = await res.json();
  return data.ticket || null;
}

export async function replyTicket(ticketId: string, body: string): Promise<HelpTicket | null> {
  const res = await fetch(`${API}/family-help/inbox/${ticketId}/reply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Family-Help-Confirm': 'si-enviar' },
    credentials: 'include',
    body: JSON.stringify({ body, author: 'Max', explicit_yes: true }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data.ticket || null;
}

export async function patchRequest(
  edition: string,
  ticketId: string,
  patch: { type?: RequestType; status?: LogStatus },
): Promise<HelpTicket | null> {
  const res = await fetch(`${API}/family-help/requests/${edition}/${ticketId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ request_type: patch.type, status: patch.status }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data.ticket || null;
}

export async function addWorkLog(
  edition: string,
  ticketId: string,
  body: { body: string; href?: string; href_label?: string; kind?: string },
): Promise<HelpTicket | null> {
  const res = await fetch(`${API}/family-help/requests/${edition}/${ticketId}/log`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data.ticket || null;
}

export async function createOrganizerTask(
  edition: string,
  ticketId: string,
): Promise<{ ticket: HelpTicket | null; task?: { id?: string; href?: string } }> {
  const res = await fetch(`${API}/family-help/requests/${edition}/${ticketId}/organizer-task`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return { ticket: data.ticket || null, task: data.task };
}
