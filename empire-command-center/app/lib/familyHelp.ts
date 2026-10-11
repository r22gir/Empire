import { API } from './api';
import { editionFromEnv, isFamilyEdition } from './edition';
export { familyHelpLabels } from './familyHelpCopy';

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
};

export type HelpTicket = {
  id: string;
  edition: string;
  sender: string;
  message: string;
  transcript?: string;
  context?: Array<{ role: string; content: string }>;
  status: HelpStatus;
  created_at: string;
  updated_at: string;
  attachments?: HelpAttachment[];
  replies?: HelpReply[];
  drafts?: HelpReply[];
};

export function familyHelpLabels(locale: string) {
  const es = (locale || 'es').toLowerCase().startsWith('es');
  return {
    ask: es ? 'Pedir ayuda a Max' : 'Ask Max for help',
    inbox: es ? 'Ayuda de ediciones familiares' : 'Family help',
    title: es ? 'Pedir ayuda a Max' : 'Ask Max for help',
    hint: es
      ? 'Escribe, graba un audio o adjunta una captura. Max (el de Rafael) lo verá. No se envían datos del Workroom.'
      : 'Type, record audio, or attach a screenshot. Rafael’s Max will see it. Workroom data is never sent.',
    message: es ? '¿Qué necesitas?' : 'What do you need?',
    send: es ? 'Enviar a Max' : 'Send to Max',
    sending: es ? 'Enviando…' : 'Sending…',
    voice: es ? 'Grabar audio' : 'Record audio',
    stopVoice: es ? 'Detener' : 'Stop',
    attach: es ? 'Adjuntar' : 'Attach',
    close: es ? 'Cerrar' : 'Close',
    sent: es ? 'Pedido enviado' : 'Request sent',
    replies: es ? 'Respuestas de Max' : 'Replies from Max',
    empty: es ? 'Aún no hay pedidos.' : 'No requests yet.',
    new: es ? 'Nuevo' : 'New',
    answered: es ? 'Respondido' : 'Answered',
    closedStatus: es ? 'Cerrado' : 'Closed',
    reply: es ? 'Responder' : 'Reply',
    sendReply: es ? 'Enviar respuesta' : 'Send reply',
    draft: es ? 'Borrador de Max' : 'Max draft',
    confirm: es ? 'Sí, enviar' : 'Yes, send',
    play: es ? 'Reproducir audio' : 'Play audio',
    transcript: es ? 'Transcripción' : 'Transcript',
    context: es ? 'Contexto del chat' : 'Chat context',
    files: es ? 'Archivos' : 'Files',
    needYes: es
      ? 'Max no envía ni cambia nada sin tu sí explícito.'
      : 'Max will not send or change anything without your explicit yes.',
    noApply: es
      ? 'Los arreglos de código van por un PR de cloud-agent. Este ticket no escribe en la edición familiar.'
      : 'Code fixes go through a cloud-agent PR. This ticket does not write to the family edition.',
  };
}

export function isFamilyHelpSurface(edition = editionFromEnv()): boolean {
  return isFamilyEdition(edition);
}

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

export async function createHelpTicket(input: {
  message: string;
  history: Array<{ role: string; content: string }>;
  files: File[];
  voice?: Blob | null;
  voiceName?: string;
  language?: string | null;
}): Promise<{ ok: boolean; ticket?: HelpTicket; detail?: string }> {
  const body = new FormData();
  body.append('message', input.message || '');
  body.append('history_json', JSON.stringify(input.history || []));
  if (input.language) body.append('language', input.language);
  if (input.voice) {
    body.append('voice', input.voice, input.voiceName || 'recording.webm');
  }
  for (const file of input.files) body.append('files', file, file.name);
  const res = await fetch(`${API}/family-help/tickets`, {
    method: 'POST',
    body,
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, detail: data.detail || `HTTP ${res.status}` };
  return { ok: true, ticket: data.ticket };
}
