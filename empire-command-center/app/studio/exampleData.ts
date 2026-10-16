/**
 * EXAMPLE-only fixtures for Studio screenshots and empty-state previews.
 * No real contacts, phones, emails, or live amounts.
 */
import type { PipelineRecord } from './pipeline';

export const EXAMPLE_MARK = 'EXAMPLE';

export const EXAMPLE_OWNER = 'Rafael';

export const EXAMPLE_INTENTS = [
  { id: 'today', label: "What's on today" },
  { id: 'photo', label: 'Quote from photo' },
  { id: 'link', label: 'Send me a link' },
] as const;

export const EXAMPLE_TRANSCRIPT = "What's on today and send me the route.";

export const EXAMPLE_NEEDS = [
  { id: 'ex-appr-1', kind: 'APPROVAL', title: 'Email to Client A', mark: EXAMPLE_MARK },
  { id: 'ex-od-1', kind: 'OVERDUE', title: 'INV-#### · $—', mark: EXAMPLE_MARK },
  { id: 'ex-qt-1', kind: 'QUOTE', title: 'EST-#### no reply 7+ days', mark: EXAMPLE_MARK },
];

export const EXAMPLE_SCHEDULE = [
  { id: 'ex-sch-1', time: '10:00', title: 'Install · Client B', detail: 'Navigate · Call · Do', mark: EXAMPLE_MARK },
  { id: 'ex-sch-2', time: '14:30', title: 'Measure · Client C', detail: 'Navigate · Call · Do', mark: EXAMPLE_MARK },
];

export const EXAMPLE_MONEY = {
  toCollect: '$—',
  depositsDue: '—',
  paidMtd: '$—',
  mark: EXAMPLE_MARK,
};

export const EXAMPLE_PIPELINE: PipelineRecord[] = [
  { id: 'ex-lead-a', kind: 'lead', title: 'Client A', subtitle: 'Drapery', status: 'new', business: 'workroom' },
  { id: 'ex-lead-b', kind: 'lead', title: 'Client B', subtitle: 'Banquette', status: 'new', business: 'workroom' },
  { id: 'ex-lead-c', kind: 'lead', title: 'Client C', subtitle: 'Roman shades', status: 'contacted', business: 'workroom' },
  { id: 'ex-qt-a', kind: 'quote', title: 'EST-#### · Client A', subtitle: 'Drapery · sent, no reply', status: 'sent', silentDays: 8, business: 'workroom' },
  { id: 'ex-qt-b', kind: 'quote', title: 'EST-#### · Client B', subtitle: 'Banquette · draft ready', status: 'draft', business: 'workroom' },
  { id: 'ex-qt-c', kind: 'quote', title: 'EST-#### · Client C', subtitle: 'Roman shades · approved', status: 'approved', approved: true, business: 'workroom' },
  { id: 'ex-job-a', kind: 'job', title: 'JOB-#### · Client A', subtitle: 'Drapery · Living room', status: 'in_progress', business: 'workroom' },
  { id: 'ex-job-b', kind: 'job', title: 'JOB-#### · Client B', subtitle: 'Banquette · Kitchen', status: 'accepted', business: 'workroom' },
  { id: 'ex-cut-d', kind: 'job', title: 'CNC panel · Client D', subtitle: 'Toolpath ready', status: 'cut_ready', cutReady: true, business: 'woodcraft' },
  { id: 'ex-inst-e', kind: 'job', title: 'JOB-#### · Client E', subtitle: 'Drapery', status: 'scheduled', scheduled: true, business: 'workroom' },
  { id: 'ex-paid-f', kind: 'job', title: 'JOB-#### · Client F', subtitle: 'Drapery', status: 'paid', paid: true, business: 'workroom' },
  { id: 'ex-cf-1', kind: 'project', title: 'Project · Lot ##', subtitle: 'Phase update', status: 'open', business: 'construction' },
];

export const EXAMPLE_JOB_CONTEXT = {
  number: 'JOB-####',
  client: 'Client A',
  mark: EXAMPLE_MARK,
  status: 'CUT',
  lines: [
    { area: 'Living room · Drapery', qty: '—', sqft: '—', total: '$—' },
    { area: 'Dining · Roman shade', qty: '—', sqft: '—', total: '$—' },
    { area: 'Deposit 50%', qty: '', sqft: '', total: '$—' },
    { area: 'Balance', qty: '', sqft: '', total: '$—' },
  ],
  note: 'Cut list is ready. Fabric cut uses wood + 2 × allowance for 2" foam.',
};

export const EXAMPLE_WORK_ROWS = [
  { space: 'Empire Workroom', items: [
    { title: 'JOB-#### · Client A', detail: 'Drapery · Living room', badge: 'CUT' },
    { title: 'JOB-#### · Client B', detail: 'Banquette · Kitchen', badge: 'INSTALL' },
    { title: 'JOB-#### · Client C', detail: 'Roman shades', badge: 'QUOTE' },
  ]},
  { space: 'WoodCraft', items: [
    { title: 'CNC panel · Client D', detail: 'Toolpath ready', badge: 'MAKE' },
  ]},
  { space: 'ConstructionForge', items: [
    { title: 'Project · Lot ##', detail: 'Phase update', badge: 'OPEN' },
  ]},
];

export function useExampleMode(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return new URLSearchParams(window.location.search).get('example') === '1';
  } catch {
    return false;
  }
}
