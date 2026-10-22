/**
 * Shared 11-stage job pipeline helpers.
 * Used by Max home cards, Job Hub, Job Folder, and the kanban board.
 * Pure functions — tests pass mock records only.
 */

export interface KanbanStageSpec {
  key: string;
  label: string;
  color: string;
  bgLight: string;
}

export const KANBAN_STAGES: KanbanStageSpec[] = [
  { key: 'lead',             label: 'Lead',                  color: '#64748b', bgLight: '#f1f5f9' },
  { key: 'estimate_sent',    label: 'Estimate sent',         color: '#3b82f6', bgLight: '#eff6ff' },
  { key: 'deposit_paid',     label: 'Approved/Deposit paid', color: '#10b981', bgLight: '#ecfdf5' },
  { key: 'fabric_ordered',   label: 'Fabric ordered',        color: '#8b5cf6', bgLight: '#f5f3ff' },
  { key: 'fabric_picked_up', label: 'Fabric picked up',      color: '#d97706', bgLight: '#fffbeb' },
  { key: 'in_production',    label: 'In production',         color: '#06b6d4', bgLight: '#ecfeff' },
  { key: 'ready',            label: 'Ready',                 color: '#22c55e', bgLight: '#f0fdf4' },
  { key: 'scheduled',        label: 'Scheduled',             color: '#6366f1', bgLight: '#eef2ff' },
  { key: 'installed',        label: 'Installed/Delivered',   color: '#059669', bgLight: '#ecfdf5' },
  { key: 'final_invoice',    label: 'Final invoice',         color: '#b8960c', bgLight: '#fefce8' },
  { key: 'paid_closed',      label: 'Paid/Closed',           color: '#15803d', bgLight: '#f0fdf4' },
];

export const KANBAN_STAGE_KEYS = KANBAN_STAGES.map((s) => s.key);

const STAGE_ALIASES: Record<string, string> = {
  lead: 'lead',
  intake: 'lead',
  measuring: 'lead',
  designing: 'lead',
  new: 'lead',
  pending: 'lead',
  estimate_sent: 'estimate_sent',
  quoting: 'estimate_sent',
  quoted: 'estimate_sent',
  sent: 'estimate_sent',
  deposit_paid: 'deposit_paid',
  approved: 'deposit_paid',
  deposit_received: 'deposit_paid',
  accepted: 'deposit_paid',
  fabric_ordered: 'fabric_ordered',
  fabric_picked_up: 'fabric_picked_up',
  in_production: 'in_production',
  in_progress: 'in_production',
  cutting: 'in_production',
  sewing: 'in_production',
  fabrication: 'in_production',
  finishing: 'in_production',
  ready: 'ready',
  qc: 'ready',
  quality_check: 'ready',
  ready_for_install: 'ready',
  scheduled: 'scheduled',
  installed: 'installed',
  installing: 'installed',
  delivered: 'installed',
  completed: 'installed',
  complete: 'installed',
  final_invoice: 'final_invoice',
  invoiced: 'final_invoice',
  paid_closed: 'paid_closed',
  paid: 'paid_closed',
  closed: 'paid_closed',
  archived: 'paid_closed',
  done: 'paid_closed',
};

const CLOSED_STAGES = new Set(['paid_closed', 'closed', 'paid']);
const CANCELLED_STATUS = new Set(['cancelled', 'canceled']);

export type JobLike = Record<string, any>;

export function canonicalizeStage(raw?: string | null): string {
  const key = String(raw || '').trim().toLowerCase();
  if (!key) return 'lead';
  if (KANBAN_STAGE_KEYS.includes(key)) return key;
  return STAGE_ALIASES[key] || 'lead';
}

export function stageSpec(raw?: string | null): KanbanStageSpec {
  const key = canonicalizeStage(raw);
  return KANBAN_STAGES.find((s) => s.key === key) || KANBAN_STAGES[0];
}

export function stageLabel(raw?: string | null): string {
  return stageSpec(raw).label;
}

export function stageIndex(raw?: string | null): number {
  const key = canonicalizeStage(raw);
  const i = KANBAN_STAGE_KEYS.indexOf(key);
  return i < 0 ? 0 : i;
}

export function nextStage(raw?: string | null): KanbanStageSpec | null {
  const i = stageIndex(raw);
  return i >= 0 && i < KANBAN_STAGES.length - 1 ? KANBAN_STAGES[i + 1] : null;
}

export function isCancelledJob(job: JobLike): boolean {
  return CANCELLED_STATUS.has(String(job.status || '').toLowerCase());
}

export function isActiveJob(job: JobLike): boolean {
  if (!job || isCancelledJob(job)) return false;
  const stage = canonicalizeStage(job.canonical_stage || job.pipeline_stage || job.status);
  return !CLOSED_STAGES.has(stage);
}

export function businessLabel(raw?: string | null): string {
  const v = String(raw || '').toLowerCase();
  if (v === 'woodcraft' || v === 'craft') return 'WoodCraft';
  if (v === 'construction') return 'Construction';
  if (v === 'luxe') return 'Luxe';
  if (!v || v === 'workroom') return 'Workroom';
  return v.replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

const DATE_FIELDS = [
  'pickup_delivery_date',
  'scheduled_date',
  'install_date',
  'due_date',
  'site_visit_date',
  'production_start',
  'quote_date',
] as const;

export function jobNextDate(job: JobLike): string | null {
  for (const field of DATE_FIELDS) {
    const v = job[field];
    if (v) return String(v).slice(0, 10);
  }
  return null;
}

export function formatJobDate(iso?: string | null): string {
  if (!iso) return '';
  const raw = String(iso);
  const d = new Date(raw.includes('T') ? raw : `${raw.slice(0, 10)}T12:00:00`);
  if (Number.isNaN(d.getTime())) return raw.slice(0, 10);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function jobTotal(job: JobLike): number | null {
  const strip = job.payment_strip;
  const n = Number(
    strip?.total ?? job.quoted_amount ?? job.estimated_value ?? job.total_cost ?? job.invoiced_amount,
  );
  return Number.isFinite(n) && n > 0 ? n : null;
}

export function formatJobMoney(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return '';
  return `$${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

export interface HomeJobCard {
  id: string;
  name: string;
  client: string;
  phaseKey: string;
  phase: string;
  phaseColor: string;
  nextDate: string | null;
  nextDateLabel: string;
  total: number | null;
  totalLabel: string;
  business: string;
  href: string;
  quoteId?: string | null;
  estimateHref?: string | null;
}

export function jobDisplayName(job: JobLike): string {
  return String(job.title || job.job_number || job.name || `JOB-${job.id || ''}`).trim();
}

export function jobClientNames(job: JobLike): string[] {
  const names: string[] = [];
  const seen = new Set<string>();
  const push = (raw?: string | null) => {
    const name = String(raw || '').trim();
    if (!name) return;
    const key = name.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    names.push(name);
  };
  const clients = Array.isArray(job?.clients) ? job.clients : [];
  clients.forEach((c: any) => push(c?.name || c?.customer_name));
  if (!names.length) {
    push(job?.client_name);
    push(job?.customer_name);
  }
  return names;
}

export function jobClientName(job: JobLike): string {
  const names = jobClientNames(job);
  return names.length ? names.join(' · ') : 'Client';
}

export function toHomeJobCard(job: JobLike, hrefFor: (id: string) => string): HomeJobCard | null {
  if (!job?.id) return null;
  const spec = stageSpec(job.canonical_stage || job.pipeline_stage || job.status);
  const nextDate = jobNextDate(job);
  const total = jobTotal(job);
  return {
    id: String(job.id),
    name: jobDisplayName(job),
    client: jobClientName(job),
    phaseKey: spec.key,
    phase: spec.label,
    phaseColor: spec.color,
    nextDate,
    nextDateLabel: nextDate ? formatJobDate(nextDate) : '',
    total,
    totalLabel: formatJobMoney(total),
    business: businessLabel(job.business_unit || job.business || job.type),
    href: hrefFor(String(job.id)),
    quoteId: job.quote_id ? String(job.quote_id) : null,
    estimateHref: job.quote_id
      ? `/docs/view?src=${encodeURIComponent(`/api/v1/quotes-v2/${job.quote_id}/pdf`)}&title=${encodeURIComponent('Estimate')}`
      : null,
  };
}

export function activeJobCards(jobs: JobLike[] | null | undefined, hrefFor: (id: string) => string): HomeJobCard[] {
  return (jobs || [])
    .filter(isActiveJob)
    .map((j) => toHomeJobCard(j, hrefFor))
    .filter((c): c is HomeJobCard => !!c);
}

export interface PhaseHistoryEntry {
  at: string;
  from: string;
  to: string;
  summary: string;
  actor?: string;
}

export function phaseHistoryFromEvents(events: JobLike[] | null | undefined): PhaseHistoryEntry[] {
  return (events || [])
    .filter((e) => {
      const t = String(e.event_type || e.type || '').toLowerCase();
      return t === 'status_change' || t === 'stage_change' || /status:|phase|stage/i.test(String(e.summary || e.what || ''));
    })
    .map((e) => {
      const meta = typeof e.metadata === 'string' ? (() => { try { return JSON.parse(e.metadata); } catch { return {}; } })() : (e.metadata || {});
      const from = String(meta.from || '');
      const to = String(meta.to || '');
      return {
        at: String(e.created_at || e.at || ''),
        from,
        to,
        summary: String(e.summary || e.what || `Phase: ${from} → ${to}`),
        actor: e.actor && e.actor !== 'system' ? String(e.actor) : undefined,
      };
    })
    .sort((a, b) => String(b.at).localeCompare(String(a.at)));
}

export function stagePatchRequest(jobId: string, stage: string, notes?: string) {
  return {
    path: `/jobs/${encodeURIComponent(jobId)}/stage`,
    method: 'PATCH' as const,
    body: notes ? { stage, notes } : { stage },
  };
}

export function movedToast(jobName: string, fromStage: string, toStage: string): string {
  return `Moved ${jobName} from ${stageLabel(fromStage)} to ${stageLabel(toStage)}`;
}

export function jobContacts(job: JobLike, customer?: JobLike | null, extraClients?: JobLike[] | null): { name: string; role?: string; phone?: string; email?: string; address?: string; customer_id?: string }[] {
  const rows: { name: string; role?: string; phone?: string; email?: string; address?: string; customer_id?: string }[] = [];
  const seen = new Set<string>();
  const push = (c: { name?: string; role?: string; phone?: string; email?: string; address?: string; customer_id?: string }) => {
    const name = String(c.name || '').trim();
    const key = `${c.customer_id || ''}|${name}|${c.email || ''}|${c.phone || ''}`;
    if (!name && !c.email && !c.phone) return;
    if (seen.has(key)) return;
    seen.add(key);
    rows.push({
      name: name || 'Contact',
      role: c.role,
      phone: c.phone,
      email: c.email,
      address: c.address,
      customer_id: c.customer_id,
    });
  };
  const linked = [
    ...(Array.isArray(extraClients) ? extraClients : []),
    ...(Array.isArray(job.clients) ? job.clients : []),
  ];
  if (linked.length) {
    linked.forEach((c: any) => push({
      name: c.name || c.customer_name,
      role: c.role || 'contact',
      phone: c.phone,
      email: c.email,
      address: c.address,
      customer_id: String(c.customer_id || c.id || ''),
    }));
  } else {
    push({
      name: job.client_name || job.customer_name || customer?.name,
      role: 'Client',
      phone: job.client_phone || customer?.phone,
      email: job.client_email || customer?.email,
      address: job.client_address || customer?.address,
      customer_id: String(job.customer_id || customer?.id || ''),
    });
  }
  const extra = Array.isArray(job.contacts) ? job.contacts : [];
  extra.forEach((c: any) => push({
    name: c.name || c.full_name,
    role: c.role || c.title,
    phone: c.phone,
    email: c.email,
    address: c.address,
  }));
  return rows;
}
