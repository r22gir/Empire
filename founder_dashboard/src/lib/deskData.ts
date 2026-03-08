/* ── Mock Data for AI Business Desks ──────────────────────────── */

// ═══════════════════════════════════════════════════════════════
// OPERATIONS
// ═══════════════════════════════════════════════════════════════

export type JobStatus = 'New' | 'Cutting' | 'Sewing' | 'Installing' | 'Complete';

export interface Job {
  id: string;
  name: string;
  client: string;
  status: JobStatus;
  dueDate: string;
  assignedTo: string;
  treatmentType: string;
  fabric: string;
  dimensions: string;
  notes: string;
  orderDate: string;
  installerNotes: string;
  quoteId: string;
}

export const JOB_STATUSES: JobStatus[] = ['New', 'Cutting', 'Sewing', 'Installing', 'Complete'];

export const MOCK_JOBS: Job[] = [
  { id: 'j1', name: 'Master Bedroom Drapes',     client: 'Henderson',   status: 'Sewing',      dueDate: '2026-02-28', assignedTo: 'Maria G.',  treatmentType: 'Drapes',   fabric: 'Imperial Silk – Luxe',   dimensions: '96"W x 108"H (2 panels)', notes: 'Client prefers pinch pleat, double-width fullness', orderDate: '2026-02-10', installerNotes: 'Rod already mounted, confirm bracket spacing', quoteId: 'Q-2026-041' },
  { id: 'j2', name: 'Living Room Blinds',         client: 'Thornton',    status: 'Cutting',     dueDate: '2026-03-02', assignedTo: 'James K.',  treatmentType: 'Blinds',   fabric: 'Solar Screen – Performance', dimensions: '72"W x 60"H (3 windows)', notes: 'Cordless lift, inside mount', orderDate: '2026-02-14', installerNotes: 'Verify window depth for inside mount ≥ 2.5"', quoteId: 'Q-2026-043' },
  { id: 'j3', name: 'Office Roman Shades',        client: 'Whitfield',   status: 'New',         dueDate: '2026-03-05', assignedTo: 'Unassigned', treatmentType: 'Shades',  fabric: 'Linen Cloud – Natural',  dimensions: '48"W x 54"H (2 windows)', notes: 'Flat fold roman, privacy lining', orderDate: '2026-02-20', installerNotes: '', quoteId: 'Q-2026-047' },
  { id: 'j4', name: 'Dining Room Valances',       client: 'Chen',        status: 'Installing',  dueDate: '2026-02-26', assignedTo: 'Carlos R.', treatmentType: 'Valances', fabric: 'Jacquard Gold – Luxe',   dimensions: '120"W x 18"H', notes: 'Box pleat valance, matching tiebacks', orderDate: '2026-02-05', installerNotes: 'Board mount above existing casing', quoteId: 'Q-2026-038' },
  { id: 'j5', name: 'Guest Suite Shutters',       client: 'Abernathy',   status: 'Complete',    dueDate: '2026-02-24', assignedTo: 'Maria G.',  treatmentType: 'Shutters', fabric: 'N/A – Basswood',         dimensions: '36"W x 60"H (4 windows)', notes: '3.5" louvers, white finish', orderDate: '2026-01-28', installerNotes: 'Completed on schedule, client signed off', quoteId: 'Q-2026-032' },
  { id: 'j6', name: 'Kitchen Café Curtains',      client: 'Delgado',     status: 'New',         dueDate: '2026-03-01', assignedTo: 'Unassigned', treatmentType: 'Drapes',  fabric: 'Cotton Ivory – Classic', dimensions: '36"W x 36"H (2 panels)', notes: 'Rod pocket, café-length', orderDate: '2026-02-22', installerNotes: '', quoteId: 'Q-2026-049' },
  { id: 'j7', name: 'Nursery Blackout Shades',    client: 'Patterson',   status: 'Sewing',      dueDate: '2026-02-27', assignedTo: 'James K.',  treatmentType: 'Shades',  fabric: 'Blackout Midnight – Performance', dimensions: '52"W x 64"H', notes: 'Full blackout, child-safe cordless', orderDate: '2026-02-12', installerNotes: 'Ceiling mount per client request', quoteId: 'Q-2026-044' },
  { id: 'j8', name: 'Sunroom Sheers',             client: 'Okafor',      status: 'Cutting',     dueDate: '2026-03-04', assignedTo: 'Carlos R.', treatmentType: 'Drapes',  fabric: 'Sheer Whisper – Ethereal', dimensions: '180"W x 96"H (6 panels)', notes: 'Ripplefold on track, 100% fullness', orderDate: '2026-02-18', installerNotes: 'Track system arrives 3/1, coordinate install', quoteId: 'Q-2026-046' },
  { id: 'j9', name: 'Media Room Motorized',       client: 'Langston',    status: 'New',         dueDate: '2026-03-08', assignedTo: 'Maria G.',  treatmentType: 'Shades',  fabric: 'Blackout Midnight – Performance', dimensions: '110"W x 72"H', notes: 'Lutron Sivoia QS, integration with home automation', orderDate: '2026-02-24', installerNotes: 'Coordinate with client AV contractor', quoteId: 'Q-2026-051' },
  { id: 'j10', name: 'Foyer Side Panels',         client: 'Rivera',      status: 'Complete',    dueDate: '2026-02-22', assignedTo: 'James K.',  treatmentType: 'Drapes',  fabric: 'Velvet Noir – Luxe',     dimensions: '24"W x 96"H (2 panels)', notes: 'Stationary panels, decorative hardware', orderDate: '2026-02-01', installerNotes: 'Installed, final photos taken', quoteId: 'Q-2026-036' },
];

// ═══════════════════════════════════════════════════════════════
// FINANCE
// ═══════════════════════════════════════════════════════════════

export interface Transaction {
  id: string;
  date: string;
  description: string;
  amount: number;
  type: 'income' | 'expense';
  category: string;
  relatedJob: string;
  receipt: string;
  notes: string;
}

export interface InvoiceLineItem {
  description: string;
  qty: number;
  rate: number;
  amount: number;
}

export interface Invoice {
  id: string;
  client: string;
  amount: number;
  status: 'paid' | 'pending' | 'overdue';
  dueDate: string;
  lineItems: InvoiceLineItem[];
  paidDate: string;
  notes: string;
}

export const MOCK_FINANCE = {
  revenueMTD: 47_850,
  revenueYTD: 142_300,
  expensesMTD: 18_920,
  outstandingInvoices: 23_400,
  profitMargin: 0.605,
};

export const MOCK_TRANSACTIONS: Transaction[] = [
  { id: 't1', date: '2026-02-25', description: 'Henderson – Master Bedroom Install',  amount: 4200, type: 'income',  category: 'Installation', relatedJob: 'j1', receipt: 'REC-0425', notes: 'Final install payment' },
  { id: 't2', date: '2026-02-24', description: 'Fabric Supplier – Silk Order',         amount: 1850, type: 'expense', category: 'Materials',    relatedJob: 'j1', receipt: 'PO-1192',  notes: 'Imperial Silk 12 yards' },
  { id: 't3', date: '2026-02-23', description: 'Thornton – Deposit 50%',               amount: 3100, type: 'income',  category: 'Deposit',      relatedJob: 'j2', receipt: 'REC-0424', notes: '50% deposit on blinds project' },
  { id: 't4', date: '2026-02-22', description: 'Shop Rent – February',                 amount: 2800, type: 'expense', category: 'Overhead',      relatedJob: '',   receipt: 'RENT-0226', notes: 'Monthly lease payment' },
  { id: 't5', date: '2026-02-21', description: 'Chen – Final Payment',                 amount: 5600, type: 'income',  category: 'Completion',    relatedJob: 'j4', receipt: 'REC-0423', notes: 'Balance due on valance project' },
  { id: 't6', date: '2026-02-20', description: 'Hardware Supply Co.',                   amount: 920,  type: 'expense', category: 'Hardware',      relatedJob: '',   receipt: 'PO-1188',  notes: 'Brackets, rings, and rods' },
  { id: 't7', date: '2026-02-19', description: 'Abernathy – Shutters Install',         amount: 7200, type: 'income',  category: 'Installation',  relatedJob: 'j5', receipt: 'REC-0422', notes: 'Shutters paid in full' },
  { id: 't8', date: '2026-02-18', description: 'Insurance Premium',                    amount: 450,  type: 'expense', category: 'Insurance',     relatedJob: '',   receipt: 'INS-Q1',   notes: 'Quarterly business insurance' },
];

export const MOCK_INVOICES: Invoice[] = [
  { id: 'inv1', client: 'Henderson',  amount: 8400,  status: 'paid',    dueDate: '2026-02-20', paidDate: '2026-02-19', notes: 'Paid via bank transfer', lineItems: [{ description: 'Imperial Silk fabric (12 yds)', qty: 12, rate: 85, amount: 1020 }, { description: 'Fabrication – pinch pleat drapes', qty: 2, rate: 1200, amount: 2400 }, { description: 'Lining – blackout', qty: 12, rate: 28, amount: 336 }, { description: 'Hardware – decorative rod + rings', qty: 1, rate: 420, amount: 420 }, { description: 'Installation', qty: 1, rate: 4224, amount: 4224 }] },
  { id: 'inv2', client: 'Thornton',   amount: 6200,  status: 'pending', dueDate: '2026-03-05', paidDate: '', notes: '50% deposit received', lineItems: [{ description: 'Solar Screen fabric (8 yds)', qty: 8, rate: 42, amount: 336 }, { description: 'Fabrication – roller blinds x3', qty: 3, rate: 650, amount: 1950 }, { description: 'Hardware – brackets + chains', qty: 3, rate: 85, amount: 255 }, { description: 'Installation', qty: 1, rate: 3659, amount: 3659 }] },
  { id: 'inv3', client: 'Whitfield',  amount: 4800,  status: 'pending', dueDate: '2026-03-10', paidDate: '', notes: 'Awaiting fabric selection confirmation', lineItems: [{ description: 'Linen Cloud fabric (6 yds)', qty: 6, rate: 45, amount: 270 }, { description: 'Fabrication – roman shades x2', qty: 2, rate: 980, amount: 1960 }, { description: 'Privacy lining', qty: 6, rate: 22, amount: 132 }, { description: 'Hardware + installation', qty: 1, rate: 2438, amount: 2438 }] },
  { id: 'inv4', client: 'Chen',       amount: 5600,  status: 'paid',    dueDate: '2026-02-22', paidDate: '2026-02-21', notes: 'Paid in full, final payment', lineItems: [{ description: 'Jacquard Gold fabric (8 yds)', qty: 8, rate: 95, amount: 760 }, { description: 'Fabrication – box pleat valance', qty: 1, rate: 1800, amount: 1800 }, { description: 'Hardware – board mount', qty: 1, rate: 180, amount: 180 }, { description: 'Installation + tiebacks', qty: 1, rate: 2860, amount: 2860 }] },
  { id: 'inv5', client: 'Delgado',    amount: 3200,  status: 'overdue', dueDate: '2026-02-15', paidDate: '', notes: 'Reminder sent 2/20, no response', lineItems: [{ description: 'Cotton Ivory fabric (4 yds)', qty: 4, rate: 28, amount: 112 }, { description: 'Fabrication – café curtains', qty: 2, rate: 580, amount: 1160 }, { description: 'Hardware – café rod', qty: 1, rate: 95, amount: 95 }, { description: 'Installation', qty: 1, rate: 1833, amount: 1833 }] },
  { id: 'inv6', client: 'Patterson',  amount: 9400,  status: 'pending', dueDate: '2026-03-01', paidDate: '', notes: 'Due on completion of install', lineItems: [{ description: 'Blackout Midnight fabric (7 yds)', qty: 7, rate: 58, amount: 406 }, { description: 'Fabrication – blackout shade', qty: 1, rate: 2200, amount: 2200 }, { description: 'Cordless lift mechanism', qty: 1, rate: 380, amount: 380 }, { description: 'Installation + ceiling mount', qty: 1, rate: 6414, amount: 6414 }] },
  { id: 'inv7', client: 'Langston',   amount: 12800, status: 'pending', dueDate: '2026-03-15', paidDate: '', notes: 'Motorization project, milestone billing', lineItems: [{ description: 'Blackout Midnight fabric (10 yds)', qty: 10, rate: 58, amount: 580 }, { description: 'Lutron Sivoia QS motor', qty: 1, rate: 4200, amount: 4200 }, { description: 'Fabrication – motorized shade', qty: 1, rate: 3500, amount: 3500 }, { description: 'Installation + AV integration', qty: 1, rate: 4520, amount: 4520 }] },
];

export const MOCK_REVENUE_TREND = [
  { month: 'Sep', revenue: 32000, expenses: 14200 },
  { month: 'Oct', revenue: 38500, expenses: 16800 },
  { month: 'Nov', revenue: 41200, expenses: 15500 },
  { month: 'Dec', revenue: 29800, expenses: 13200 },
  { month: 'Jan', revenue: 52400, expenses: 19800 },
  { month: 'Feb', revenue: 47850, expenses: 18920 },
];

// ═══════════════════════════════════════════════════════════════
// SALES
// ═══════════════════════════════════════════════════════════════

export type LeadStage = 'New Lead' | 'Quoted' | 'Follow-up' | 'Won' | 'Lost';

export interface LeadInteraction {
  date: string;
  type: 'call' | 'email' | 'meeting' | 'text';
  summary: string;
}

export interface Lead {
  id: string;
  client: string;
  projectType: string;
  estimatedValue: number;
  lastContact: string;
  stage: LeadStage;
  notes: string;
  phone: string;
  email: string;
  interactions: LeadInteraction[];
}

export const LEAD_STAGES: LeadStage[] = ['New Lead', 'Quoted', 'Follow-up', 'Won', 'Lost'];

export const MOCK_LEADS: Lead[] = [
  { id: 'l1',  client: 'Brooks',     projectType: 'Whole-Home Drapes',     estimatedValue: 18500, lastContact: '2026-02-25', stage: 'New Lead',   notes: 'Referred by Henderson', phone: '(512) 555-0301', email: 'brooks@email.com', interactions: [{ date: '2026-02-25', type: 'call', summary: 'Initial inquiry, interested in whole-home treatment' }, { date: '2026-02-25', type: 'email', summary: 'Sent lookbook and pricing guide' }] },
  { id: 'l2',  client: 'Yamamoto',   projectType: 'Office Blinds (12)',    estimatedValue: 9600,  lastContact: '2026-02-24', stage: 'Quoted',     notes: 'Commercial job, 12 windows', phone: '(512) 555-0302', email: 'yamamoto@corp.com', interactions: [{ date: '2026-02-20', type: 'meeting', summary: 'On-site measurement, 12 standard windows' }, { date: '2026-02-24', type: 'email', summary: 'Sent quote Q-2026-052, awaiting approval' }] },
  { id: 'l3',  client: 'Martinez',   projectType: 'Master Suite Shades',   estimatedValue: 4200,  lastContact: '2026-02-22', stage: 'Follow-up',  notes: 'Waiting on fabric choice', phone: '(512) 555-0303', email: 'martinez@email.com', interactions: [{ date: '2026-02-15', type: 'meeting', summary: 'Consultation at home, showed fabric samples' }, { date: '2026-02-22', type: 'text', summary: 'Followed up on fabric selection, will decide by Friday' }] },
  { id: 'l4',  client: 'Henderson',  projectType: 'Master Bedroom Drapes', estimatedValue: 8400,  lastContact: '2026-02-20', stage: 'Won',        notes: 'In production', phone: '(512) 555-0101', email: 'henderson@email.com', interactions: [{ date: '2026-02-10', type: 'email', summary: 'Quote approved, deposit received' }, { date: '2026-02-20', type: 'call', summary: 'Confirmed fabric arrived, production starting' }] },
  { id: 'l5',  client: 'Kim',        projectType: 'Motorized Shades',      estimatedValue: 15000, lastContact: '2026-02-23', stage: 'Quoted',     notes: 'High-end Lutron system', phone: '(512) 555-0305', email: 'kim@email.com', interactions: [{ date: '2026-02-18', type: 'meeting', summary: 'Home visit, discussed Lutron Sivoia QS options' }, { date: '2026-02-23', type: 'email', summary: 'Sent detailed motorization quote with AV integration' }] },
  { id: 'l6',  client: 'Davis',      projectType: 'Shutters 8-window',     estimatedValue: 6800,  lastContact: '2026-02-18', stage: 'Lost',       notes: 'Went with competitor', phone: '(512) 555-0306', email: 'davis@email.com', interactions: [{ date: '2026-02-12', type: 'meeting', summary: 'On-site measurement for 8 windows' }, { date: '2026-02-18', type: 'call', summary: 'Client chose competitor, price was lower by ~15%' }] },
  { id: 'l7',  client: 'Singh',      projectType: 'Dining Valances',       estimatedValue: 3200,  lastContact: '2026-02-26', stage: 'New Lead',   notes: 'Wants consultation this week', phone: '(512) 555-0307', email: 'singh@email.com', interactions: [{ date: '2026-02-26', type: 'call', summary: 'Incoming call, wants valances for dining room, scheduling visit' }] },
  { id: 'l8',  client: 'Foster',     projectType: 'Nursery + Guest',       estimatedValue: 5400,  lastContact: '2026-02-21', stage: 'Follow-up',  notes: 'Sent samples, awaiting response', phone: '(512) 555-0308', email: 'foster@email.com', interactions: [{ date: '2026-02-14', type: 'meeting', summary: 'Consultation, needs blackout for nursery + sheers for guest room' }, { date: '2026-02-21', type: 'email', summary: 'Mailed fabric samples, follow up next week' }] },
  { id: 'l9',  client: 'Abernathy',  projectType: 'Guest Suite Shutters',  estimatedValue: 7200,  lastContact: '2026-02-19', stage: 'Won',        notes: 'Complete, paid in full', phone: '(512) 555-0106', email: 'abernathy@email.com', interactions: [{ date: '2026-02-01', type: 'email', summary: 'Quote approved' }, { date: '2026-02-19', type: 'call', summary: 'Project complete, client very satisfied' }] },
  { id: 'l10', client: 'Nakamura',   projectType: 'Living Room Sheers',    estimatedValue: 2800,  lastContact: '2026-02-26', stage: 'New Lead',   notes: 'Walk-in inquiry', phone: '(512) 555-0310', email: 'nakamura@email.com', interactions: [{ date: '2026-02-26', type: 'meeting', summary: 'Walk-in at showroom, interested in sheer drapery for living room' }] },
];

// ═══════════════════════════════════════════════════════════════
// DESIGN
// ═══════════════════════════════════════════════════════════════

export type TreatmentType = 'drapes' | 'blinds' | 'shades' | 'shutters' | 'valances';

export interface FabricSwatch {
  id: string;
  name: string;
  collection: string;
  color: string;
  pricePerYard: number;
  treatment: TreatmentType;
}

export const TREATMENT_TYPES: { value: TreatmentType; label: string; icon: string }[] = [
  { value: 'drapes',   label: 'Drapes',   icon: '🪟' },
  { value: 'blinds',   label: 'Blinds',   icon: '▤' },
  { value: 'shades',   label: 'Shades',   icon: '◻' },
  { value: 'shutters', label: 'Shutters', icon: '⊞' },
  { value: 'valances', label: 'Valances', icon: '〰' },
];

export const MOCK_FABRICS: FabricSwatch[] = [
  { id: 'f1', name: 'Imperial Silk',     collection: 'Luxe',       color: '#8B7355', pricePerYard: 85,  treatment: 'drapes' },
  { id: 'f2', name: 'Velvet Noir',       collection: 'Luxe',       color: '#2C2C2C', pricePerYard: 72,  treatment: 'drapes' },
  { id: 'f3', name: 'Linen Cloud',       collection: 'Natural',    color: '#E8E0D0', pricePerYard: 45,  treatment: 'drapes' },
  { id: 'f4', name: 'Sheer Whisper',     collection: 'Ethereal',   color: '#F5F0EB', pricePerYard: 32,  treatment: 'drapes' },
  { id: 'f5', name: 'Canvas Dune',       collection: 'Natural',    color: '#C4A77D', pricePerYard: 38,  treatment: 'shades' },
  { id: 'f6', name: 'Bamboo Weave',      collection: 'Organic',    color: '#9B8B6E', pricePerYard: 52,  treatment: 'shades' },
  { id: 'f7', name: 'Blackout Midnight',  collection: 'Performance',color: '#1A1A2E', pricePerYard: 58,  treatment: 'shades' },
  { id: 'f8', name: 'Solar Screen',       collection: 'Performance',color: '#7B7B7B', pricePerYard: 42,  treatment: 'blinds' },
  { id: 'f9', name: 'Cotton Ivory',       collection: 'Classic',    color: '#FFFFF0', pricePerYard: 28,  treatment: 'valances' },
  { id: 'f10',name: 'Jacquard Gold',      collection: 'Luxe',       color: '#C5A55A', pricePerYard: 95,  treatment: 'valances' },
];

// ═══════════════════════════════════════════════════════════════
// ESTIMATING
// ═══════════════════════════════════════════════════════════════

export type FabricGrade = 'Standard' | 'Premium' | 'Luxe';

export const FABRIC_GRADES: { grade: FabricGrade; multiplier: number; label: string }[] = [
  { grade: 'Standard', multiplier: 1.0,  label: '$28–45/yd' },
  { grade: 'Premium',  multiplier: 1.6,  label: '$45–72/yd' },
  { grade: 'Luxe',     multiplier: 2.4,  label: '$72–95/yd' },
];

export const BASE_PRICES: Record<TreatmentType, { material: number; labor: number; hardware: number }> = {
  drapes:   { material: 180, labor: 120, hardware: 45 },
  blinds:   { material: 95,  labor: 65,  hardware: 35 },
  shades:   { material: 140, labor: 85,  hardware: 40 },
  shutters: { material: 250, labor: 150, hardware: 60 },
  valances: { material: 90,  labor: 55,  hardware: 25 },
};

// ═══════════════════════════════════════════════════════════════
// DESK PROMPTS
// ═══════════════════════════════════════════════════════════════

export const DESK_PROMPTS: Record<string, string> = {
  operations:  'You are MAX, the Operations Manager for a premium drapery workroom. You help track active jobs from order to installation. You know fabric lead times (typically 2-4 weeks), standard production time (3-5 business days for most treatments), and installation scheduling. When discussing jobs, always reference the job number, client name, and current stage. Be concise and action-oriented.',
  finance:     'You are MAX, the Financial Controller for a premium drapery business. You help track revenue, expenses, outstanding invoices, and profitability per job. You understand drapery business economics: typical margins are 40-60% on materials, labor costs for seamstresses and installers, and overhead. Always be precise with numbers and flag overdue payments.',
  sales:       'You are MAX, the Sales Director for a premium drapery company. You help manage the sales pipeline from initial inquiry to closed deal. Track lead sources and always suggest follow-up timing. Help draft professional client communications in English or Spanish.',
  design:      'You are MAX, the Design Consultant for a premium drapery workroom. You help with window treatment selection, fabric recommendations, and photo-based measurements using AI vision. You know treatment types, fullness ratios, stack-back calculations, and mounting options.',
  estimating:  'You are MAX, the Estimating Specialist for a premium drapery workroom. You build detailed quotes with line-item pricing. You know fabric pricing, lining costs, labor rates per treatment type, hardware costs, and installation fees. Always itemize quotes clearly.',
  clients:     'You are MAX, the Client Relations Manager for a premium drapery company. You maintain detailed client records including contact info, property addresses, past orders, fabric preferences, and communication history. Always be warm and personable — clients are the lifeblood of the business.',
  contractors: 'You are MAX, the Contractor Coordinator for a premium drapery company. You manage relationships with installers, seamstresses, and other contractors. You track their availability, pay rates, specialties, and reliability scores. Help schedule installations efficiently.',
  support:     'You are MAX, the Customer Support Manager for a premium drapery company. You handle service requests, warranty claims, and customer concerns professionally. Common issues: uneven hems, cord/chain malfunctions, motorization problems, fabric fading, hardware loosening. Always prioritize customer satisfaction.',
  marketing:   'You are MAX, the Marketing Director for a premium drapery company. You create engaging content for Instagram, Facebook, Pinterest, and the website. Help draft captions, plan content calendars, and suggest hashtag strategies for the home décor space.',
  website:     'You are MAX, the Web Manager for a premium drapery company. You help manage the company website, SEO for local service businesses, Google Business Profile optimization, portfolio updates, and review management. Help write compelling web copy.',
  it:          'You are MAX, the Systems Administrator for the Empire platform. You monitor service health across all ports. You help with deployments, troubleshooting, log analysis, and system optimization. The Switchboard enforces a 3-server limit. Always prioritize system stability.',
  legal:       'You are MAX, the Legal Assistant for a premium drapery business. You help manage contracts, proposals, terms and conditions, and compliance documents. You understand standard drapery industry contract terms. Always recommend professional legal review for important documents.',
  lab:         'You are MAX in experimental mode. This is the R&D Lab where we test new AI capabilities, prototype features, and experiment with integrations. Be creative and exploratory — suggest new automations, test features, and brainstorm improvements. Nothing here affects production data.',
  costs:       'You are MAX, the AI Cost Analyst for the Empire platform. You track API spending across all providers (xAI Grok, Claude, Groq, Ollama). You help analyze cost trends, suggest optimizations (like switching to cheaper models for simple tasks), and monitor budget usage. Provide clear cost breakdowns and alert on spending anomalies.',
};

// ═══════════════════════════════════════════════════════════════
// DESK DEFINITIONS
// ═══════════════════════════════════════════════════════════════

export type DeskId =
  | 'operations' | 'finance' | 'sales' | 'design' | 'estimating'
  | 'clients' | 'contractors' | 'support' | 'marketing'
  | 'website' | 'it' | 'legal' | 'lab' | 'costs';

export interface DeskDefinition {
  id: DeskId;
  name: string;
  icon: string;
  lucideIcon: string;
  description: string;
  color: string;
  shortcut: string;
}

export const BUSINESS_DESKS: DeskDefinition[] = [
  { id: 'operations',  name: 'Operations',   icon: '⚙️', lucideIcon: 'ClipboardList',  description: 'Production & scheduling',    color: '#D4AF37',  shortcut: 'Alt+1' },
  { id: 'finance',     name: 'Finance',      icon: '💰', lucideIcon: 'DollarSign',     description: 'Revenue & invoicing',        color: '#22C55E',  shortcut: 'Alt+2' },
  { id: 'sales',       name: 'Sales',        icon: '📈', lucideIcon: 'TrendingUp',     description: 'Leads & pipeline',           color: '#8B5CF6',  shortcut: 'Alt+3' },
  { id: 'design',      name: 'Design',       icon: '🎨', lucideIcon: 'Palette',        description: 'Treatments & fabrics',       color: '#EC4899',  shortcut: 'Alt+4' },
  { id: 'estimating',  name: 'Estimating',   icon: '🧮', lucideIcon: 'Calculator',     description: 'Quotes & pricing',           color: '#F59E0B',  shortcut: 'Alt+5' },
  { id: 'clients',     name: 'Clients',      icon: '👥', lucideIcon: 'Users',          description: 'Customer database',          color: '#06B6D4',  shortcut: 'Alt+6' },
  { id: 'contractors', name: 'Contractors',  icon: '🔧', lucideIcon: 'Wrench',         description: 'Installers & scheduling',    color: '#F97316',  shortcut: 'Alt+7' },
  { id: 'support',     name: 'Support',      icon: '🎧', lucideIcon: 'Headphones',     description: 'Service & warranty',         color: '#EF4444',  shortcut: 'Alt+8' },
  { id: 'marketing',   name: 'Marketing',    icon: '📢', lucideIcon: 'Megaphone',      description: 'Content & campaigns',        color: '#A855F7',  shortcut: 'Alt+9' },
  { id: 'website',     name: 'Website',      icon: '🌐', lucideIcon: 'Globe',          description: 'SEO & portfolio',            color: '#14B8A6',  shortcut: 'Alt+0' },
  { id: 'it',          name: 'IT / Systems', icon: '🖥️', lucideIcon: 'Server',         description: 'Health & monitoring',        color: '#6366F1',  shortcut: 'Ctrl+Alt+1' },
  { id: 'legal',       name: 'Legal',        icon: '⚖️', lucideIcon: 'Scale',          description: 'Contracts & compliance',     color: '#78716C',  shortcut: 'Ctrl+Alt+2' },
  { id: 'lab',         name: 'R&D Lab',      icon: '🧪', lucideIcon: 'FlaskConical',   description: 'Experiments & prototypes',   color: '#E11D48',  shortcut: 'Ctrl+Alt+3' },
  { id: 'costs',       name: 'AI Costs',     icon: '📊', lucideIcon: 'BarChart3',      description: 'API cost tracking',          color: '#D4AF37',  shortcut: 'Ctrl+Alt+4' },
];

// ═══════════════════════════════════════════════════════════════
// CLIENTS
// ═══════════════════════════════════════════════════════════════

export interface Client {
  id: string;
  name: string;
  email: string;
  phone: string;
  address: string;
  totalJobs: number;
  totalSpent: number;
  lastContact: string;
  status: 'active' | 'prospect' | 'inactive';
}

export const MOCK_CLIENTS: Client[] = [
  { id: 'c1', name: 'Henderson',  email: 'henderson@email.com',  phone: '(512) 555-0101', address: '1234 Oak Hill Dr', totalJobs: 3, totalSpent: 18400, lastContact: '2026-02-25', status: 'active' },
  { id: 'c2', name: 'Thornton',   email: 'thornton@email.com',   phone: '(512) 555-0102', address: '567 Elm St',       totalJobs: 1, totalSpent: 6200,  lastContact: '2026-02-24', status: 'active' },
  { id: 'c3', name: 'Whitfield',  email: 'whitfield@email.com',  phone: '(512) 555-0103', address: '890 Cedar Ln',     totalJobs: 0, totalSpent: 0,     lastContact: '2026-02-22', status: 'prospect' },
  { id: 'c4', name: 'Chen',       email: 'chen@email.com',       phone: '(512) 555-0104', address: '321 Maple Ave',    totalJobs: 2, totalSpent: 11200, lastContact: '2026-02-22', status: 'active' },
  { id: 'c5', name: 'Delgado',    email: 'delgado@email.com',    phone: '(512) 555-0105', address: '654 Pine Rd',      totalJobs: 1, totalSpent: 3200,  lastContact: '2026-02-18', status: 'active' },
  { id: 'c6', name: 'Abernathy',  email: 'abernathy@email.com',  phone: '(512) 555-0106', address: '987 Birch Ct',     totalJobs: 2, totalSpent: 14400, lastContact: '2026-02-19', status: 'active' },
  { id: 'c7', name: 'Patterson',  email: 'patterson@email.com',  phone: '(512) 555-0107', address: '147 Walnut Way',   totalJobs: 1, totalSpent: 9400,  lastContact: '2026-02-21', status: 'active' },
  { id: 'c8', name: 'Langston',   email: 'langston@email.com',   phone: '(512) 555-0108', address: '258 Spruce Dr',    totalJobs: 0, totalSpent: 0,     lastContact: '2026-02-23', status: 'prospect' },
];

// ═══════════════════════════════════════════════════════════════
// CONTRACTORS
// ═══════════════════════════════════════════════════════════════

export interface ContractorPayRecord {
  date: string;
  amount: number;
  job: string;
}

export interface Contractor {
  id: string;
  name: string;
  specialty: string;
  rate: number;
  phone: string;
  available: boolean;
  rating: number;
  jobsCompleted: number;
  skills: string[];
  payHistory: ContractorPayRecord[];
  notes: string;
}

export const MOCK_CONTRACTORS: Contractor[] = [
  { id: 'ct1', name: 'Maria G.',   specialty: 'Sewing / Fabrication', rate: 55, phone: '(512) 555-0201', available: true,  rating: 4.9, jobsCompleted: 87, skills: ['Pinch pleat', 'Ripplefold', 'Roman shades', 'Box pleat valances'], notes: 'Most reliable fabricator, handles all premium jobs', payHistory: [{ date: '2026-02-20', amount: 1650, job: 'Henderson Drapes' }, { date: '2026-02-14', amount: 1200, job: 'Abernathy Shutters' }, { date: '2026-02-05', amount: 980, job: 'Rivera Side Panels' }] },
  { id: 'ct2', name: 'James K.',   specialty: 'Sewing / Cutting',    rate: 50, phone: '(512) 555-0202', available: true,  rating: 4.7, jobsCompleted: 62, skills: ['Cutting', 'Pattern layout', 'Blackout lining', 'Basic sewing'], notes: 'Fast cutter, good with pattern matching', payHistory: [{ date: '2026-02-22', amount: 1400, job: 'Patterson Shades' }, { date: '2026-02-15', amount: 900, job: 'Okafor Sheers' }] },
  { id: 'ct3', name: 'Carlos R.',  specialty: 'Installation',        rate: 75, phone: '(512) 555-0203', available: false, rating: 4.8, jobsCompleted: 114, skills: ['Drapery installation', 'Board mount', 'Track systems', 'Motorized shades'], notes: 'Currently on Chen dining room install, back 2/27', payHistory: [{ date: '2026-02-18', amount: 2200, job: 'Chen Valances' }, { date: '2026-02-10', amount: 1800, job: 'Henderson Install' }] },
  { id: 'ct4', name: 'David M.',   specialty: 'Motorization',        rate: 85, phone: '(512) 555-0204', available: true,  rating: 4.6, jobsCompleted: 43, skills: ['Lutron integration', 'Somfy motors', 'Smart home setup', 'AV coordination'], notes: 'Go-to for all motorization projects, Lutron certified', payHistory: [{ date: '2026-02-12', amount: 3200, job: 'Langston Motorized' }, { date: '2026-01-28', amount: 2600, job: 'External project' }] },
  { id: 'ct5', name: 'Ana S.',     specialty: 'Installation',        rate: 70, phone: '(512) 555-0205', available: true,  rating: 4.5, jobsCompleted: 38, skills: ['Blinds installation', 'Shutter mounting', 'Inside mount', 'Outside mount'], notes: 'Good backup installer, prefers smaller jobs', payHistory: [{ date: '2026-02-08', amount: 950, job: 'Whitfield Shades' }] },
  { id: 'ct6', name: 'Roberto L.', specialty: 'Heavy Drapery',       rate: 80, phone: '(512) 555-0206', available: false, rating: 4.9, jobsCompleted: 95, skills: ['Heavy drapery', 'Motorized tracks', 'Commercial installs', 'Multi-story work'], notes: 'On vacation until 3/3, specializes in heavy/large-scale work', payHistory: [{ date: '2026-02-05', amount: 3800, job: 'Commercial project' }, { date: '2026-01-22', amount: 2400, job: 'Okafor Sheers (track)' }] },
];

// ═══════════════════════════════════════════════════════════════
// SUPPORT
// ═══════════════════════════════════════════════════════════════

export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed';

export interface TicketResolution {
  date: string;
  action: string;
  by: string;
}

export interface SupportTicket {
  id: string;
  client: string;
  issue: string;
  status: TicketStatus;
  priority: 'low' | 'medium' | 'high';
  createdAt: string;
  category: string;
  assignedTo: string;
  resolutionHistory: TicketResolution[];
}

export const TICKET_STATUSES: TicketStatus[] = ['open', 'in_progress', 'resolved', 'closed'];

export const MOCK_TICKETS: SupportTicket[] = [
  { id: 'tk1', client: 'Delgado',   issue: 'Cord mechanism jammed on Roman shade',    status: 'open',        priority: 'high',   createdAt: '2026-02-25', category: 'Mechanical', assignedTo: 'Carlos R.', resolutionHistory: [{ date: '2026-02-25', action: 'Ticket created, client called in', by: 'System' }] },
  { id: 'tk2', client: 'Chen',      issue: 'Slight color mismatch between panels',    status: 'in_progress', priority: 'medium', createdAt: '2026-02-24', category: 'Quality', assignedTo: 'Maria G.', resolutionHistory: [{ date: '2026-02-24', action: 'Ticket created from client email', by: 'System' }, { date: '2026-02-25', action: 'Reviewed photos, dye lot variance confirmed. Ordering replacement panel.', by: 'Maria G.' }] },
  { id: 'tk3', client: 'Henderson', issue: 'Motorized shade not responding to remote', status: 'open',        priority: 'high',   createdAt: '2026-02-23', category: 'Motorization', assignedTo: 'David M.', resolutionHistory: [{ date: '2026-02-23', action: 'Ticket created, client reported remote unresponsive', by: 'System' }, { date: '2026-02-24', action: 'Scheduled site visit for 2/27', by: 'David M.' }] },
  { id: 'tk4', client: 'Abernathy', issue: 'Request for additional holdback hardware', status: 'resolved',    priority: 'low',    createdAt: '2026-02-20', category: 'Hardware', assignedTo: 'Ana S.', resolutionHistory: [{ date: '2026-02-20', action: 'Ticket created, client wants matching holdbacks', by: 'System' }, { date: '2026-02-21', action: 'Ordered matching holdback hardware from supplier', by: 'Ana S.' }, { date: '2026-02-24', action: 'Hardware delivered and installed. Client satisfied.', by: 'Ana S.' }] },
  { id: 'tk5', client: 'Patterson', issue: 'Blackout lining letting light through edges', status: 'in_progress', priority: 'medium', createdAt: '2026-02-22', category: 'Quality', assignedTo: 'Carlos R.', resolutionHistory: [{ date: '2026-02-22', action: 'Ticket created, light leaking at side edges', by: 'System' }, { date: '2026-02-23', action: 'Site visit completed. Need to add side channels for full blackout.', by: 'Carlos R.' }] },
];

// ═══════════════════════════════════════════════════════════════
// MARKETING
// ═══════════════════════════════════════════════════════════════

export type PostStatus = 'draft' | 'scheduled' | 'published';

export interface ContentPost {
  id: string;
  title: string;
  platform: string;
  status: PostStatus;
  scheduledDate: string;
  engagement?: number;
  content: string;
  hashtags: string[];
  notes: string;
}

export const MOCK_POSTS: ContentPost[] = [
  { id: 'p1', title: 'Before/After: Henderson Master Suite',     platform: 'Instagram', status: 'published',  scheduledDate: '2026-02-24', engagement: 847, content: 'Swipe to see the stunning transformation of the Henderson master suite! Imperial Silk pinch pleat drapes in a rich gold tone bring warmth and elegance to this beautiful space. Every detail matters — from the double-width fullness to the custom decorative hardware.', hashtags: ['#drapery', '#interiordesign', '#beforeandafter', '#windowtreatments', '#luxuryhome', '#austintx'], notes: 'Top-performing post this month. Reuse format for future before/after content.' },
  { id: 'p2', title: '5 Tips for Choosing Drapery Fabric',       platform: 'Blog',      status: 'published',  scheduledDate: '2026-02-22', engagement: 312, content: 'Choosing the right fabric for your window treatments can feel overwhelming. Here are our top 5 tips: 1) Consider light control needs 2) Match fabric weight to treatment style 3) Always order samples 4) Think about maintenance 5) Consider the room\'s purpose. Read on for detailed guidance from our design team.', hashtags: ['#draperydesign', '#fabricselection', '#interiordesigntips', '#windowtreatments'], notes: 'Good SEO performance, link from Instagram stories.' },
  { id: 'p3', title: 'Spring Collection Fabric Reveal',          platform: 'Instagram', status: 'scheduled',  scheduledDate: '2026-03-01', content: 'Spring is here and so are fresh new fabrics! Introducing our 2026 Spring Collection featuring organic linens, airy sheers, and vibrant botanical prints. Available now in our showroom — come feel the difference quality makes.', hashtags: ['#springcollection', '#newfabrics', '#drapery', '#interiordesign', '#showroom'], notes: 'Coordinate with showroom display update on same day.' },
  { id: 'p4', title: 'Client Testimonial: Abernathy Project',    platform: 'Facebook',  status: 'draft',      scheduledDate: '', content: '"We couldn\'t be happier with our new shutters! The team was professional, on time, and the quality is outstanding. Highly recommend!" — The Abernathy Family. See the full guest suite transformation featuring custom basswood shutters with 3.5" louvers.', hashtags: ['#clienttestimonial', '#shutters', '#customwindowtreatments', '#happyclients'], notes: 'Waiting for client photo approval before publishing.' },
  { id: 'p5', title: 'Motorized Shades Demo Reel',              platform: 'TikTok',    status: 'scheduled',  scheduledDate: '2026-03-03', content: 'Watch motorized shades in action! One tap and the entire room transforms. Featuring Lutron Sivoia QS integration with smart home automation. Perfect for media rooms, bedrooms, and hard-to-reach windows.', hashtags: ['#motorizedshades', '#smarthome', '#lutron', '#windowtreatments', '#homeautomation', '#tiktok'], notes: 'Film at Langston project once installed. 30-second reel format.' },
  { id: 'p6', title: 'Design Trends 2026: Layered Treatments',  platform: 'Pinterest', status: 'draft',      scheduledDate: '', content: 'Layered window treatments are THE trend for 2026. Combine sheer drapes with roller shades for ultimate light control and style. Our design team creates custom layered solutions that are both beautiful and functional. Pin for inspiration!', hashtags: ['#designtrends2026', '#layeredtreatments', '#windowdesign', '#pinterestinspiration', '#drapery'], notes: 'Create 5 pin graphics from showroom photos. Vertical format.' },
];
