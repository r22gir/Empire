/** Pure Organizer UI logic — calendar geometry, filters, overdue, parse. */

export type OrganizerKind =
  | 'job_milestone' | 'measure' | 'install' | 'pickup' | 'drop_off' | 'fitting'
  | 'delivery' | 'meeting' | 'appointment' | 'todo' | 'reminder' | 'followup'
  | 'material_order' | 'call' | 'deadline' | 'fabric_pickup' | 'loading_dock'
  | 'errand' | 'travel' | 'medical' | 'school' | 'legal' | 'admin' | 'social' | 'other';

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
  reminder_draft?: string | null;
  space_id?: string | null;
  column?: string | null;
  quote_id?: string | null;
  customer_id?: string | null;
  schedule_event_id?: string | null;
  reminder_at?: string | null;
  capture_id?: string | null;
  progress?: OrganizerProgress | null;
  record_links?: OrganizerRecordLink[];
  actions?: OrganizerAction[];
  money?: OrganizerMoney | null;
  waiting_on?: string | null;
  nudge_after_days?: number | null;
  invoice_id?: string | null;
  last_moved_at?: string | null;
  updated_at?: string | null;
  created_at?: string | null;
};

export type OrganizerProgress = {
  job_id?: string;
  total: number;
  done: number;
  open?: number;
  percent: number;
  fraction: string;
};

export type OrganizerMoney = {
  job_id?: string;
  deposit: number;
  paid: number;
  balance: number;
  margin?: number | null;
  total?: number;
  collected_fraction: string;
  quote_id?: string | null;
  invoice_id?: string | null;
  quote_href?: string | null;
  invoice_href?: string | null;
  read_only?: boolean;
};

export type OrganizerRecordLink = {
  kind: 'estimate' | 'client' | 'job' | 'calendar' | string;
  id: string;
  label: string;
  href: string;
};

export type OrganizerSpace = {
  slug: string;
  label: string;
  kind?: string;
  icon?: string;
  accent_color?: string;
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
  errand: 'Errand', travel: 'Travel', medical: 'Medical', school: 'School',
  legal: 'Legal', admin: 'Admin', social: 'Social', other: 'Other',
};

export const KIND_COLOR: Record<string, string> = {
  install: '#2563eb', measure: '#0891b2', pickup: '#d97706', drop_off: '#16a34a',
  delivery: '#ca8a04', fitting: '#7c3aed', meeting: '#4f46e5', appointment: '#0f766e',
  call: '#be185d', todo: '#57534e', reminder: '#b45309', followup: '#c2410c',
  deadline: '#b91c1c', material_order: '#7e22ce', job_milestone: '#334155',
  fabric_pickup: '#9333ea', loading_dock: '#dc2626', errand: '#6b7280',
  travel: '#0369a1', medical: '#be123c', school: '#15803d', legal: '#1e293b',
  admin: '#57534e', social: '#c026d3', other: '#52525b',
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
  opts: { jobId?: string; resourceId?: string; kind?: string; query?: string; spaceId?: string },
): OrganizerItem[] {
  return items.filter((it) => {
    if (opts.jobId && String(it.job_id || '') !== String(opts.jobId)) return false;
    if (opts.resourceId && !(it.assigned_resource_ids || []).includes(opts.resourceId)) return false;
    if (opts.kind && (it.kind || it.type) !== opts.kind) return false;
    if (opts.spaceId && String(it.space_id || '') !== String(opts.spaceId)) return false;
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
    ['medical', ['dentist', 'doctor', 'medical']], ['school', ['school', 'recital']],
    ['travel', ['flight', 'travel']], ['meeting', ['meeting']],
    ['legal', ['lawyer', 'notary', 'legal']],
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

export function showsWorkroomJobs(edition: { allows_workroom_jobs?: boolean } | null | undefined, spaceId?: string): boolean {
  if (!edition?.allows_workroom_jobs) return false;
  return !spaceId || spaceId === 'workroom';
}

export const SPACE_STYLE: Record<string, { icon: string; accent: string }> = {
  workroom: { icon: '🧵', accent: '#c2410c' },
  empire: { icon: '👑', accent: '#7c3aed' },
  family: { icon: '🏡', accent: '#16a34a' },
  personal: { icon: '✦', accent: '#0891b2' },
  ventures: { icon: '🚀', accent: '#d97706' },
  amp: { icon: '🎯', accent: '#2563eb' },
};

export function spaceStyle(space?: OrganizerSpace | string | null): { icon: string; accent: string; label: string; slug: string } {
  if (space && typeof space === 'object') {
    const fallback = SPACE_STYLE[space.slug] || { icon: '●', accent: '#57534e' };
    return {
      slug: space.slug,
      label: space.label || space.slug,
      icon: space.icon || fallback.icon,
      accent: space.accent_color || fallback.accent,
    };
  }
  const slug = String(space || '');
  const fallback = SPACE_STYLE[slug] || { icon: '●', accent: '#57534e' };
  return { slug, label: slug, ...fallback };
}

export type TodayBucket = 'overdue' | 'today' | 'upcoming';

export function todayBuckets(items: OrganizerItem[], today: string): Record<TodayBucket, OrganizerItem[]> {
  const horizon = (() => {
    const d = parseStamp(`${today}T00:00:00`) || new Date(`${today}T00:00:00`);
    d.setDate(d.getDate() + 14);
    return ymd(d);
  })();
  const overdue = overdueItems(items, `${today}T00:00:00`);
  const overdueIds = new Set(overdue.map((i) => i.id));
  const todayRows: OrganizerItem[] = [];
  const upcoming: OrganizerItem[] = [];
  for (const it of items) {
    if (overdueIds.has(it.id)) continue;
    if (['done', 'cancelled'].includes(String(it.status || ''))) continue;
    const day = (it.start_time || it.due_at || '').slice(0, 10);
    if (day === today) todayRows.push(it);
    else if (day > today && day <= horizon) upcoming.push(it);
  }
  return { overdue, today: todayRows, upcoming };
}

export const STATUS_COLUMNS = [
  { id: 'open', label: 'Open', statuses: ['open', 'planned', 'snoozed'] },
  { id: 'doing', label: 'Doing', statuses: ['in_progress', 'confirmed', 'waiting_on'] },
  { id: 'done', label: 'Done', statuses: ['done'] },
] as const;

export function columnForStatus(status?: string | null): string {
  const key = String(status || 'open');
  for (const col of STATUS_COLUMNS) {
    if ((col.statuses as readonly string[]).includes(key)) return col.id;
  }
  return key === 'cancelled' ? 'done' : 'open';
}

export function itemsInColumn(items: OrganizerItem[], column: string): OrganizerItem[] {
  return items.filter((it) => (it.column || columnForStatus(it.status)) === column);
}

export function dueForTodayColumn(column: TodayBucket, today: string): string {
  if (column === 'today') return `${today}T09:00:00`;
  const d = parseStamp(`${today}T00:00:00`) || new Date(`${today}T00:00:00`);
  d.setDate(d.getDate() + (column === 'upcoming' ? 1 : -1));
  return `${ymd(d)}T09:00:00`;
}

export function progressFromTasks(done: number, total: number): OrganizerProgress {
  const safeTotal = Math.max(0, total);
  const safeDone = Math.max(0, Math.min(done, safeTotal));
  return {
    total: safeTotal,
    done: safeDone,
    open: Math.max(0, safeTotal - safeDone),
    percent: safeTotal ? Math.round((100 * safeDone) / safeTotal) : 0,
    fraction: `${safeDone}/${safeTotal}`,
  };
}

export function inferSpaceClient(text: string, allowed: string[] = []): string | null {
  const raw = (text || '').toLowerCase();
  const rules: [string, RegExp][] = [
    ['workroom', /\b(workroom|install|fabric|drapery|measure|nelma)\b/],
    ['empire', /\b(empire|studio|command center|max)\b/],
    ['family', /\b(kids?|family|school|recital|soccer)\b/],
    ['personal', /\b(dentist|doctor|personal|gym|myself)\b/],
    ['ventures', /\b(venture|side project|other business)\b/],
    ['amp', /\b(amp|coaching|juan)\b/],
  ];
  for (const [slug, re] of rules) {
    if (re.test(raw) && (!allowed.length || allowed.includes(slug))) return slug;
  }
  return null;
}

export type PendingMail = {
  id: string;
  source: string;
  message_id: string;
  account?: string;
  from?: string;
  from_name?: string;
  from_email?: string;
  subject: string;
  preview?: string;
  waiting?: string;
  space_id?: string;
  job_title?: string;
  person_name?: string;
  suggested_reply?: string;
  open_href?: string;
  unread?: boolean;
};

export function pendingMailVisible(items: PendingMail[], snoozedIds: string[] = []): PendingMail[] {
  const hidden = new Set(snoozedIds);
  return items.filter((m) => !hidden.has(m.id));
}

export type OrgTheme = 'a' | 'b' | 'c';

export const ORG_THEMES: { id: OrgTheme; label: string; name: string }[] = [
  { id: 'a', label: 'Luxe', name: 'Luxe dark' },
  { id: 'b', label: 'Editorial', name: 'Editorial light' },
  { id: 'c', label: 'Command', name: 'Command dashboard' },
];

export const ORG_THEME_STORAGE = 'empire.orgTheme';

export function parseOrgTheme(value?: string | null): OrgTheme | null {
  const v = String(value || '').trim().toLowerCase();
  if (v === 'a' || v === 'luxe' || v === 'dark') return 'a';
  if (v === 'b' || v === 'editorial' || v === 'light') return 'b';
  if (v === 'c' || v === 'command' || v === 'dashboard') return 'c';
  return null;
}

export function resolveOrgTheme(query?: string | null, stored?: string | null): OrgTheme {
  return parseOrgTheme(query) || parseOrgTheme(stored) || 'a';
}

export const THEME_SPACE_ACCENTS: Record<OrgTheme, Record<string, string>> = {
  a: {
    workroom: '#d4a017', empire: '#c4b5fd', family: '#34d399',
    personal: '#38bdf8', ventures: '#fb923c', amp: '#60a5fa',
  },
  b: {
    workroom: '#8b5a3c', empire: '#6b5b7a', family: '#4f6f52',
    personal: '#4a6670', ventures: '#8a6d3b', amp: '#3d5a80',
  },
  c: {
    workroom: '#fb923c', empire: '#a78bfa', family: '#4ade80',
    personal: '#22d3ee', ventures: '#fbbf24', amp: '#60a5fa',
  },
};

export function themedSpaceStyle(
  space: OrganizerSpace | string | null | undefined,
  theme: OrgTheme = 'a',
): { icon: string; accent: string; label: string; slug: string } {
  const base = spaceStyle(space);
  const configured = typeof space === 'object' && space?.accent_color
    ? space.accent_color
    : '';
  const seeded = SPACE_STYLE[base.slug]?.accent;
  const custom = configured && configured !== seeded;
  return {
    ...base,
    accent: custom ? configured : (THEME_SPACE_ACCENTS[theme][base.slug] || base.accent),
  };
}

export function organizerKpis(input: {
  overdue: number;
  today: number;
  followups?: { followup_kind?: string; title?: string }[];
  doing?: number;
  jobs?: { status?: string }[];
  moneyItems?: { title?: string; kind?: string }[];
}): { overdue: number; dueToday: number; moneyWaiting: number; jobsInProgress: number } {
  const moneyRe = /deposit|unpaid|invoice|balance|retainer/i;
  const moneyFromFollow = (input.followups || []).filter((f) => moneyRe.test(`${f.followup_kind || ''} ${f.title || ''}`)).length;
  const moneyFromItems = (input.moneyItems || []).filter((it) => moneyRe.test(`${it.title || ''} ${it.kind || ''}`)).length;
  const jobsActive = (input.jobs || []).filter((j) => !['done', 'complete', 'cancelled', 'closed'].includes(String(j.status || '').toLowerCase())).length;
  return {
    overdue: input.overdue,
    dueToday: input.today,
    moneyWaiting: moneyFromFollow + moneyFromItems,
    jobsInProgress: Math.max(input.doing || 0, jobsActive),
  };
}

export function jobProgressFromItems(items: OrganizerItem[], jobId: string): OrganizerProgress | null {
  const linked = items.filter((it) => String(it.job_id || '') === String(jobId));
  if (!linked.length) return null;
  const done = linked.filter((it) => String(it.status || '') === 'done').length;
  return { ...progressFromTasks(done, linked.length), job_id: jobId };
}

export function formatOrganizerDate(d: Date): string {
  return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
}

export type ReviewBucket = 'slipped' | 'stuck' | 'next_week' | 'wins';

export function groupBySpace<T extends { space_id?: string | null }>(items: T[]): Record<string, T[]> {
  const out: Record<string, T[]> = {};
  for (const it of items) {
    const slug = String(it.space_id || 'personal');
    (out[slug] ||= []).push(it);
  }
  return out;
}

export function weeklyReview(
  items: OrganizerItem[],
  today: string,
): {
  slipped: OrganizerItem[];
  stuck: OrganizerItem[];
  next_week: OrganizerItem[];
  wins: OrganizerItem[];
  by_space: Record<string, Record<string, OrganizerItem[]>>;
  areas: string[];
  counts: { slipped: number; stuck: number; next_week: number; wins: number; areas: number };
  workroom_only: false;
} {
  const start = parseStamp(`${today}T00:00:00`) || new Date(`${today}T00:00:00`);
  const weekEnd = new Date(start);
  weekEnd.setDate(weekEnd.getDate() + 7);
  const weekStart = new Date(start);
  weekStart.setDate(weekStart.getDate() - weekStart.getDay() + 1);
  if (weekStart > start) weekStart.setDate(weekStart.getDate() - 7);
  const stuckBefore = new Date(start);
  stuckBefore.setDate(stuckBefore.getDate() - 7);
  const weekEndY = ymd(weekEnd);
  const weekStartY = ymd(weekStart);
  const stuckY = ymd(stuckBefore);
  const slipped: OrganizerItem[] = [];
  const stuck: OrganizerItem[] = [];
  const nextWeek: OrganizerItem[] = [];
  const wins: OrganizerItem[] = [];
  for (const it of items) {
    const status = String(it.status || '');
    const due = (it.due_at || it.start_time || '').slice(0, 10);
    const moved = String(it.last_moved_at || it.updated_at || it.due_at || it.start_time || '').slice(0, 10);
    if (status === 'done') {
      if (moved && moved >= weekStartY && moved <= today) wins.push(it);
      continue;
    }
    if (status === 'cancelled') continue;
    if (due && due < today) slipped.push(it);
    else if (due && due > today && due <= weekEndY) nextWeek.push(it);
    if (moved && moved <= stuckY) stuck.push(it);
  }
  const areas = [...new Set([...slipped, ...stuck, ...nextWeek, ...wins].map((i) => String(i.space_id || 'personal')))];
  return {
    slipped,
    stuck,
    next_week: nextWeek,
    wins,
    by_space: {
      slipped: groupBySpace(slipped),
      stuck: groupBySpace(stuck),
      next_week: groupBySpace(nextWeek),
      wins: groupBySpace(wins),
    },
    areas,
    counts: { slipped: slipped.length, stuck: stuck.length, next_week: nextWeek.length, wins: wins.length, areas: areas.length },
    workroom_only: false,
  };
}

export type ShutdownDestination = 'tomorrow' | 'later' | 'keep' | 'drop';

export function eveningShutdown(
  items: OrganizerItem[],
  today: string,
): {
  date: string;
  tomorrow: string;
  completed: OrganizerItem[];
  unfinished: OrganizerItem[];
  tomorrow_preview: OrganizerItem[];
  undated: OrganizerItem[];
  by_space: Record<string, Record<string, OrganizerItem[]>>;
  areas: string[];
  counts: { completed: number; unfinished: number; tomorrow: number; undated: number; areas: number };
  steps: string[];
  workroom_only: false;
} {
  const start = parseStamp(`${today}T00:00:00`) || new Date(`${today}T00:00:00`);
  const tmr = new Date(start);
  tmr.setDate(tmr.getDate() + 1);
  const tomorrow = ymd(tmr);
  const completed: OrganizerItem[] = [];
  const unfinished: OrganizerItem[] = [];
  const tomorrowPreview: OrganizerItem[] = [];
  const undated: OrganizerItem[] = [];
  for (const it of items) {
    const status = String(it.status || '');
    const due = (it.due_at || it.start_time || '').slice(0, 10);
    const moved = String(it.last_moved_at || it.updated_at || due).slice(0, 10);
    if (status === 'done' && (moved === today || due === today)) {
      completed.push(it);
      continue;
    }
    if (status === 'cancelled') continue;
    if (due === tomorrow) {
      tomorrowPreview.push(it);
      continue;
    }
    if (due === today || (due && due < today)) unfinished.push(it);
    else if (!due && !['done', 'cancelled'].includes(status)) undated.push(it);
  }
  const areas = [...new Set([...completed, ...unfinished, ...tomorrowPreview, ...undated].map((i) => String(i.space_id || 'personal')))];
  return {
    date: today,
    tomorrow,
    completed,
    unfinished,
    tomorrow_preview: tomorrowPreview,
    undated,
    by_space: {
      completed: groupBySpace(completed),
      unfinished: groupBySpace(unfinished),
      tomorrow: groupBySpace(tomorrowPreview),
      undated: groupBySpace(undated),
    },
    areas,
    counts: {
      completed: completed.length,
      unfinished: unfinished.length,
      tomorrow: tomorrowPreview.length,
      undated: undated.length,
      areas: areas.length,
    },
    steps: ['review', 'move', 'plan'],
    workroom_only: false,
  };
}

export function shutdownDueAt(destination: ShutdownDestination, today: string, later?: string | null): string | null {
  if (destination === 'tomorrow') {
    const d = parseStamp(`${today}T00:00:00`) || new Date(`${today}T00:00:00`);
    d.setDate(d.getDate() + 1);
    return `${ymd(d)}T09:00:00`;
  }
  if (destination === 'later') {
    const day = (later || '').slice(0, 10) || (() => {
      const d = parseStamp(`${today}T00:00:00`) || new Date(`${today}T00:00:00`);
      d.setDate(d.getDate() + 2);
      return ymd(d);
    })();
    return `${day}T09:00:00`;
  }
  return null;
}

export function applyShutdownMoves(
  items: OrganizerItem[],
  moves: { id: string; destination: ShutdownDestination; due_at?: string | null }[],
  today: string,
): OrganizerItem[] {
  const map = new Map(items.map((it) => [it.id, { ...it }]));
  for (const move of moves) {
    const row = map.get(move.id);
    if (!row) continue;
    if (move.destination === 'keep') continue;
    if (move.destination === 'drop') {
      row.status = 'cancelled';
      continue;
    }
    const due = shutdownDueAt(move.destination, today, move.due_at);
    if (due) {
      row.due_at = due;
      if (row.start_time) row.start_time = due;
      row.last_moved_at = today;
    }
  }
  return [...map.values()];
}

export function formatMoney(n?: number | null): string {
  if (n == null || Number.isNaN(Number(n))) return '—';
  const v = Number(n);
  const sign = v < 0 ? '-' : '';
  const abs = Math.abs(v);
  const dollars = Math.floor(abs);
  const cents = Math.round((abs - dollars) * 100);
  return cents ? `${sign}$${dollars}.${String(cents).padStart(2, '0')}` : `${sign}$${dollars}`;
}

export function formatOrganizerTime(iso?: string | null): string {
  if (!iso) return '';
  const t = iso.slice(11, 16);
  if (!t) return iso.slice(0, 10);
  const [h, m] = t.split(':').map((n) => parseInt(n, 10));
  if (!Number.isFinite(h)) return t;
  const suffix = h >= 12 ? 'PM' : 'AM';
  const hr = ((h + 11) % 12) + 1;
  return m ? `${hr}:${String(m).padStart(2, '0')} ${suffix}` : `${hr} ${suffix}`;
}

export function filterPendingMail(
  items: PendingMail[],
  opts: { spaceId?: string; query?: string; snoozedIds?: string[] } = {},
): PendingMail[] {
  const q = (opts.query || '').trim().toLowerCase();
  return pendingMailVisible(items, opts.snoozedIds).filter((m) => {
    if (opts.spaceId && m.space_id && m.space_id !== opts.spaceId) return false;
    if (!q) return true;
    const blob = `${m.subject} ${m.from_name || ''} ${m.from || ''} ${m.from_email || ''} ${m.preview || ''} ${m.person_name || ''} ${m.job_title || ''}`.toLowerCase();
    return blob.includes(q);
  });
}
