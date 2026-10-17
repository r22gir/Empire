/**
 * Work pipeline: Lead → Quote → Job → Cut → Install → Paid.
 * Pure mapping — no network, no live contacts. Used by the Work tab and tests.
 */

export const PIPELINE_STAGES = ['lead', 'quote', 'job', 'cut', 'install', 'paid'] as const;
export type PipelineStage = (typeof PIPELINE_STAGES)[number];

export interface PipelineRecord {
  id: string;
  kind: 'lead' | 'quote' | 'job' | 'project';
  title: string;
  subtitle?: string;
  status?: string;
  pipeline_stage?: string;
  business?: string;
  amount?: number | null;
  silentDays?: number | null;
  approved?: boolean;
  paid?: boolean;
  cutReady?: boolean;
  scheduled?: boolean;
}

export interface PipelineCard {
  id: string;
  stage: PipelineStage;
  title: string;
  subtitle: string;
  badge: string;
  primaryLabel: string;
  primaryAction: PipelineAction;
  href: string;
  business: string;
}

export type PipelineAction =
  | 'quote'
  | 'follow-up'
  | 'send-link'
  | 'take-deposit'
  | 'work-order'
  | 'mark-cut'
  | 'schedule'
  | 'pay-link'
  | 'open';

const CLOSED = new Set([
  'cancelled', 'canceled', 'closed', 'archived', 'lost', 'declined', 'rejected',
  'expired', 'void', 'dead', 'disqualified',
]);
const PAID = new Set(['paid', 'completed', 'complete', 'done', 'collected']);
const INSTALL = new Set(['install', 'installing', 'scheduled', 'schedule', 'on_site', 'onsite']);
const CUT = new Set(['cut', 'cutting', 'cut_ready', 'cutlist', 'yardage', 'work_order', 'work-order', 'ready_to_cut']);
const JOB = new Set(['job', 'accepted', 'approved', 'in_progress', 'production', 'make', 'making', 'open']);
const QUOTE = new Set(['quote', 'draft', 'sent', 'viewed', 'proposal', 'estimating']);
const LEAD = new Set(['lead', 'new', 'contacted', 'qualified', 'prospect']);

function norm(s?: string | null): string {
  return String(s || '').trim().toLowerCase().replace(/[\s-]+/g, '_');
}

export function classifyStage(record: PipelineRecord): PipelineStage | null {
  const status = norm(record.status);
  const stage = norm(record.pipeline_stage);
  if (CLOSED.has(status) || CLOSED.has(stage)) return null;
  if (record.paid || PAID.has(status) || PAID.has(stage) || status === 'paid') return 'paid';
  if (record.scheduled || INSTALL.has(status) || INSTALL.has(stage)) return 'install';
  if (record.cutReady || CUT.has(status) || CUT.has(stage)) return 'cut';
  if (record.kind === 'job' || JOB.has(status) || JOB.has(stage)) return 'job';
  if (record.kind === 'quote' || QUOTE.has(status) || QUOTE.has(stage) || record.approved) return 'quote';
  if (record.kind === 'lead' || LEAD.has(status) || LEAD.has(stage)) return 'lead';
  if (record.kind === 'project') return 'job';
  return 'lead';
}

export function nextAction(card: { stage: PipelineStage; status?: string; silentDays?: number | null; approved?: boolean }): {
  label: string;
  action: PipelineAction;
} {
  const status = norm(card.status);
  if (card.stage === 'lead') return { label: 'Quote it', action: 'quote' };
  if (card.stage === 'quote') {
    if (card.approved || status === 'approved' || status === 'accepted') {
      return { label: 'Take deposit → Job', action: 'take-deposit' };
    }
    if (status === 'draft') return { label: 'Send me a link', action: 'send-link' };
    if ((card.silentDays ?? 0) >= 7 || status === 'sent' || status === 'viewed') {
      return { label: 'Follow up → Job', action: 'follow-up' };
    }
    return { label: 'Send me a link', action: 'send-link' };
  }
  if (card.stage === 'job') return { label: 'Work order', action: 'work-order' };
  if (card.stage === 'cut') return { label: 'Mark cut', action: 'mark-cut' };
  if (card.stage === 'install') return { label: 'Schedule', action: 'schedule' };
  if (card.stage === 'paid') return { label: 'Pay link', action: 'pay-link' };
  return { label: 'Open', action: 'open' };
}

export function actionHref(action: PipelineAction, record: PipelineRecord): string {
  const id = encodeURIComponent(record.id);
  switch (action) {
    case 'quote':
      return `/?product=lead&section=quotes&id=${id}`;
    case 'follow-up':
      return `/?product=workroom&section=quotes&id=${id}`;
    case 'send-link':
      return `/?tab=max&screen=chat&ask=${encodeURIComponent('Send me a link for this quote')}`;
    case 'take-deposit':
      return `/?tab=money&product=pay&id=${id}`;
    case 'work-order':
      return `/?product=workroom&section=work-orders&id=${id}`;
    case 'mark-cut':
      return `/?product=workroom&section=templates&id=${id}`;
    case 'schedule':
      return `/?tab=today&screen=calendar&job=${id}`;
    case 'pay-link':
      return `/?tab=money&product=pay&id=${id}`;
    default:
      return record.kind === 'lead' ? `/?product=lead` : `/?product=workroom&section=jobs`;
  }
}

export function toPipelineCard(record: PipelineRecord): PipelineCard | null {
  const stage = classifyStage(record);
  if (!stage) return null;
  const next = nextAction({ stage, status: record.status, silentDays: record.silentDays, approved: record.approved });
  const badge = record.approved ? 'APPROVED' : (record.status || stage).replace(/[_-]+/g, ' ').toUpperCase();
  return {
    id: record.id,
    stage,
    title: record.title,
    subtitle: record.subtitle || '',
    badge,
    primaryLabel: next.label,
    primaryAction: next.action,
    href: actionHref(next.action, record),
    business: record.business || 'workroom',
  };
}

export function groupPipeline(records: PipelineRecord[]): Record<PipelineStage, PipelineCard[]> {
  const out: Record<PipelineStage, PipelineCard[]> = {
    lead: [], quote: [], job: [], cut: [], install: [], paid: [],
  };
  for (const rec of records) {
    const card = toPipelineCard(rec);
    if (card) out[card.stage].push(card);
  }
  return out;
}

export const STAGE_LABEL: Record<PipelineStage, string> = {
  lead: 'Lead',
  quote: 'Quote',
  job: 'Job',
  cut: 'Cut',
  install: 'Install',
  paid: 'Paid',
};

export const STAGE_KICK: Record<PipelineStage, string> = {
  lead: 'LeadForge',
  quote: 'Quote',
  job: 'Job hub',
  cut: 'Cut list',
  install: 'Organizer',
  paid: 'EmpirePay',
};
