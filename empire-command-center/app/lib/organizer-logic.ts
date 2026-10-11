/** Pure Organizer UI logic — calendar geometry, filters, overdue, parse. */

export type OrganizerKind =
  | 'job_milestone' | 'measure' | 'install' | 'pickup' | 'drop_off' | 'fitting'
  | 'delivery' | 'meeting' | 'appointment' | 'todo' | 'reminder' | 'followup'
  | 'material_order' | 'call' | 'deadline' | 'fabric_pickup' | 'loading_dock'
  | 'errand' | 'other';

export type OrganizerItem = {
  id: string;
  kind?: string;
  type?: string;
  title: string;
  start_time?: string | null;
  end_time?: string | null;
  due_at?: string | null;
  job_id?: string | null;
  location_address?: string | null;
  phone?: string | null;
  map_link?: string | null;
  call_link?: string | null;
  assigned_resource_ids?: string[];
  assigned_names?: string[];
  status?: string;
  source?: string;
  read_only?: boolean;
  followup_kind?: string | null;
  notes?: string | null;
  customer_vendor?: string | null;
  job_title?: string | null;
  capture_id?: string | null;
  reminder_draft?: string | null;
  actions?: OrganizerAction[];
};

export type OrganizerAction = {
  id: string;
  label: string;
  group: string;
  href?: string;
  draft?: boolean;
  requires_confirm?: boolean;
  performs?: string;
};

export const KIND_LABEL: Record<string, string> = {
  job_milestone: 'Milestone', measure: 'Measure', install: 'Install',
  pickup: 'Pickup', drop_off: 'Drop-off', fitting: 'Fitting', delivery: 'Delivery',
  meeting: 'Meeting', appointment: 'Appointment', todo: 'To-do', reminder: 'Reminder',
  followup: 'Follow-up', material_order: 'Material / ETA', call: 'Call',
  deadline: 'Deadline', fabric_pickup: 'Fabric pickup', loading_dock: 'Loading dock',
  errand: 'Errand', other: 'Other',
};

export const KIND_COLOR: Record<string, string> = {
  install: '#2563eb', measure: '#0891b2', pickup: '#d97706', drop_off: '#16a34a',
  delivery: '#ca8a04', fitting: '#7c3aed', meeting: '#4f46e5', appointment: '#0f766e',
  call: '#be185d', todo: '#57534e', reminder: '#b45309', followup: '#c2410c',
  deadline: '#b91c1c', material_order: '#7e22ce', job_milestone: '#334155',
  fabric_pickup: '#9333ea', loading_dock: '#dc2626', errand: '#6b7280', other: '#52525b',
};

export function ymd(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export function parseStamp(value?: string | null): Date | null {
  if (!value) return null;
  const t = Date.parse(value.includes('T') ? value : value.replace(' ', 'T'));
  return Number.isFinite(t) ? new Date(t) : null;
}

export function minutesSinceMidnight(d: Date): number {
  return d.getHours() * 60 + d.getMinutes();
}

export const DAY_START_MIN = 7 * 60;
export const DAY_END_MIN = 20 * 60;
export const PX_PER_MIN = 1.1;

export function eventLayout(item: OrganizerItem, day: string): { top: number; height: number; start: Date; end: Date } | null {
  const start = parseStamp(item.start_time || item.due_at);
  if (!start || ymd(start) !== day) return null;
  const end = parseStamp(item.end_time) || new Date(start.getTime() + 60 * 60 * 1000);
  const topMin = Math.max(0, minutesSinceMidnight(start) - DAY_START_MIN);
  const endMin = Math.max(topMin + 20, minutesSinceMidnight(end) - DAY_START_MIN);
  return {
    top: topMin * PX_PER_MIN,
    height: Math.max(22, (endMin - topMin) * PX_PER_MIN),
    start,
    end: end > start ? end : new Date(start.getTime() + 60 * 60 * 1000),
  };
}

export function snapMinutes(totalMin: number, step = 15): number {
  return Math.round(totalMin / step) * step;
}

export function timeFromOffset(day: string, offsetY: number, dayStartMin = DAY_START_MIN): string {
  const mins = snapMinutes(dayStartMin + offsetY / PX_PER_MIN);
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${day}T${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:00`;
}

export function addMinutesIso(iso: string, minutes: number): string {
  const d = parseStamp(iso);
  if (!d) return iso;
  return new Date(d.getTime() + minutes * 60000).toISOString().slice(0, 19);
}

export function weekDays(anchor: Date): Date[] {
  const start = new Date(anchor);
  start.setDate(start.getDate() - start.getDay());
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    return d;
  });
}

export function monthCells(anchor: Date): { date: Date | null; dateStr: string; inMonth: boolean }[] {
  const year = anchor.getFullYear();
  const month = anchor.getMonth();
  const first = new Date(year, month, 1);
  const startPad = first.getDay();
  const days = new Date(year, month + 1, 0).getDate();
  const cells: { date: Date | null; dateStr: string; inMonth: boolean }[] = [];
  for (let i = 0; i < startPad; i++) cells.push({ date: null, dateStr: '', inMonth: false });
  for (let d = 1; d <= days; d++) {
    const date = new Date(year, month, d);
    cells.push({ date, dateStr: ymd(date), inMonth: true });
  }
  while (cells.length % 7) cells.push({ date: null, dateStr: '', inMonth: false });
  return cells;
}

export function filterItems(
  items: OrganizerItem[],
  opts: { jobId?: string; resourceId?: string; kind?: string; query?: string },
): OrganizerItem[] {
  return items.filter((it) => {
    if (opts.jobId && String(it.job_id || '') !== String(opts.jobId)) return false;
    if (opts.resourceId && !(it.assigned_resource_ids || []).includes(opts.resourceId)) return false;
    if (opts.kind && (it.kind || it.type) !== opts.kind) return false;
    if (opts.query) {
      const q = opts.query.toLowerCase();
      const blob = `${it.title} ${it.customer_vendor || ''} ${it.location_address || ''} ${it.job_title || ''}`.toLowerCase();
      if (!blob.includes(q)) return false;
    }
    return true;
  });
}

export function overdueItems(items: OrganizerItem[], today: string): OrganizerItem[] {
  return items.filter((it) => {
    if (['done', 'cancelled'].includes(String(it.status || ''))) return false;
    const due = (it.due_at || it.start_time || '').slice(0, 19);
    return !!due && due < today;
  });
}

export function itemsOnDay(items: OrganizerItem[], day: string): OrganizerItem[] {
  return items.filter((it) => {
    const d = (it.start_time || it.due_at || '').slice(0, 10);
    return d === day;
  }).sort((a, b) => (a.start_time || a.due_at || '').localeCompare(b.start_time || b.due_at || ''));
}

export function parseQuickAddClient(text: string, today = new Date()): { kind: string; title: string; start_time: string | null } {
  const raw = text.trim();
  const lower = raw.toLowerCase();
  const kinds: [string, string[]][] = [
    ['install', ['install']], ['call', ['call']], ['pickup', ['pick up', 'pickup']],
    ['measure', ['measure']], ['followup', ['follow up', 'follow-up']],
    ['reminder', ['remind']], ['todo', ['todo', 'to-do', 'task']],
  ];
  let kind = 'appointment';
  for (const [k, keys] of kinds) {
    if (keys.some((x) => lower.includes(x))) { kind = k; break; }
  }
  let day = ymd(today);
  if (/\btomorrow\b/.test(lower)) {
    const t = new Date(today); t.setDate(t.getDate() + 1); day = ymd(t);
  }
  const wd = lower.match(/\b(sunday|monday|tuesday|wednesday|thursday|friday|saturday)\b/);
  if (wd) {
    const names = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
    const want = names.indexOf(wd[1]);
    const delta = (want - today.getDay() + 7) % 7;
    const t = new Date(today); t.setDate(t.getDate() + delta); day = ymd(t);
  }
  const tm = lower.match(/\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b/);
  let start: string | null = null;
  if (tm) {
    let h = parseInt(tm[1], 10);
    const m = parseInt(tm[2] || '0', 10);
    if (tm[3] === 'pm' && h < 12) h += 12;
    if (tm[3] === 'am' && h === 12) h = 0;
    start = `${day}T${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:00`;
  }
  return { kind, title: raw.slice(0, 80), start_time: start };
}

export function conflictCodes(conflicts: { code: string; message: string }[]): string {
  return conflicts.map((c) => c.message).join(' ');
}

export const ACTION_GROUPS = ['stop', 'job', 'followup', 'file', 'move'] as const;

export function groupActions(actions: OrganizerAction[] | undefined): Record<string, OrganizerAction[]> {
  const out: Record<string, OrganizerAction[]> = {};
  for (const a of actions || []) {
    const g = a.group || 'other';
    (out[g] ||= []).push(a);
  }
  return out;
}

export function parseOrganizerCommand(text: string): { command: string; tell_crew: boolean; tell_client: boolean } {
  const lower = (text || '').toLowerCase();
  let command = 'create';
  if (/\bmove\b|\breschedul/.test(lower)) command = 'move';
  else if (/\bsend (the )?quote\b|\bemail the estimate\b/.test(lower)) command = 'send_quote';
  else if (/\bdeposit\b/.test(lower) && /\b(request|send|ask)\b/.test(lower)) command = 'request_deposit';
  else if (/\border fabric\b|\bfabric order\b/.test(lower)) command = 'order_fabric';
  return {
    command,
    tell_crew: /\b(tell|notify|text|message)\b.+\bcrew\b|\bcrew\b.+\b(tell|notify|text)/.test(lower),
    tell_client: /\b(tell|text|email|notify)\b.+\b(client|customer|them|her|him)\b/.test(lower),
  };
}

export function isOrganizerCommand(text: string): boolean {
  const parsed = parseOrganizerCommand(text);
  return parsed.command !== 'create' || parsed.tell_crew || parsed.tell_client;
}

export function shouldOfferCrewDraft(moved: boolean, hadConflict: boolean): boolean {
  return !!moved && !hadConflict;
}
