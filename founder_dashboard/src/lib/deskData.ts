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
}

export const JOB_STATUSES: JobStatus[] = ['New', 'Cutting', 'Sewing', 'Installing', 'Complete'];

export const MOCK_JOBS: Job[] = [
  { id: 'j1', name: 'Master Bedroom Drapes',     client: 'Henderson',   status: 'Sewing',      dueDate: '2026-02-28', assignedTo: 'Maria G.' },
  { id: 'j2', name: 'Living Room Blinds',         client: 'Thornton',    status: 'Cutting',     dueDate: '2026-03-02', assignedTo: 'James K.' },
  { id: 'j3', name: 'Office Roman Shades',        client: 'Whitfield',   status: 'New',         dueDate: '2026-03-05', assignedTo: 'Unassigned' },
  { id: 'j4', name: 'Dining Room Valances',       client: 'Chen',        status: 'Installing',  dueDate: '2026-02-26', assignedTo: 'Carlos R.' },
  { id: 'j5', name: 'Guest Suite Shutters',       client: 'Abernathy',   status: 'Complete',    dueDate: '2026-02-24', assignedTo: 'Maria G.' },
  { id: 'j6', name: 'Kitchen Café Curtains',      client: 'Delgado',     status: 'New',         dueDate: '2026-03-01', assignedTo: 'Unassigned' },
  { id: 'j7', name: 'Nursery Blackout Shades',    client: 'Patterson',   status: 'Sewing',      dueDate: '2026-02-27', assignedTo: 'James K.' },
  { id: 'j8', name: 'Sunroom Sheers',             client: 'Okafor',      status: 'Cutting',     dueDate: '2026-03-04', assignedTo: 'Carlos R.' },
  { id: 'j9', name: 'Media Room Motorized',       client: 'Langston',    status: 'New',         dueDate: '2026-03-08', assignedTo: 'Maria G.' },
  { id: 'j10', name: 'Foyer Side Panels',         client: 'Rivera',      status: 'Complete',    dueDate: '2026-02-22', assignedTo: 'James K.' },
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
}

export interface Invoice {
  id: string;
  client: string;
  amount: number;
  status: 'paid' | 'pending' | 'overdue';
  dueDate: string;
}

export const MOCK_FINANCE = {
  revenueMTD: 47_850,
  revenueYTD: 142_300,
  expensesMTD: 18_920,
  outstandingInvoices: 23_400,
  profitMargin: 0.605,
};

export const MOCK_TRANSACTIONS: Transaction[] = [
  { id: 't1', date: '2026-02-25', description: 'Henderson – Master Bedroom Install',  amount: 4200, type: 'income',  category: 'Installation' },
  { id: 't2', date: '2026-02-24', description: 'Fabric Supplier – Silk Order',         amount: 1850, type: 'expense', category: 'Materials' },
  { id: 't3', date: '2026-02-23', description: 'Thornton – Deposit 50%',               amount: 3100, type: 'income',  category: 'Deposit' },
  { id: 't4', date: '2026-02-22', description: 'Shop Rent – February',                 amount: 2800, type: 'expense', category: 'Overhead' },
  { id: 't5', date: '2026-02-21', description: 'Chen – Final Payment',                 amount: 5600, type: 'income',  category: 'Completion' },
  { id: 't6', date: '2026-02-20', description: 'Hardware Supply Co.',                   amount: 920,  type: 'expense', category: 'Hardware' },
  { id: 't7', date: '2026-02-19', description: 'Abernathy – Shutters Install',         amount: 7200, type: 'income',  category: 'Installation' },
  { id: 't8', date: '2026-02-18', description: 'Insurance Premium',                    amount: 450,  type: 'expense', category: 'Insurance' },
];

export const MOCK_INVOICES: Invoice[] = [
  { id: 'inv1', client: 'Henderson',  amount: 8400,  status: 'paid',    dueDate: '2026-02-20' },
  { id: 'inv2', client: 'Thornton',   amount: 6200,  status: 'pending', dueDate: '2026-03-05' },
  { id: 'inv3', client: 'Whitfield',  amount: 4800,  status: 'pending', dueDate: '2026-03-10' },
  { id: 'inv4', client: 'Chen',       amount: 5600,  status: 'paid',    dueDate: '2026-02-22' },
  { id: 'inv5', client: 'Delgado',    amount: 3200,  status: 'overdue', dueDate: '2026-02-15' },
  { id: 'inv6', client: 'Patterson',  amount: 9400,  status: 'pending', dueDate: '2026-03-01' },
  { id: 'inv7', client: 'Langston',   amount: 12800, status: 'pending', dueDate: '2026-03-15' },
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

export interface Lead {
  id: string;
  client: string;
  projectType: string;
  estimatedValue: number;
  lastContact: string;
  stage: LeadStage;
  notes: string;
}

export const LEAD_STAGES: LeadStage[] = ['New Lead', 'Quoted', 'Follow-up', 'Won', 'Lost'];

export const MOCK_LEADS: Lead[] = [
  { id: 'l1',  client: 'Brooks',     projectType: 'Whole-Home Drapes',     estimatedValue: 18500, lastContact: '2026-02-25', stage: 'New Lead',   notes: 'Referred by Henderson' },
  { id: 'l2',  client: 'Yamamoto',   projectType: 'Office Blinds (12)',    estimatedValue: 9600,  lastContact: '2026-02-24', stage: 'Quoted',     notes: 'Commercial job, 12 windows' },
  { id: 'l3',  client: 'Martinez',   projectType: 'Master Suite Shades',   estimatedValue: 4200,  lastContact: '2026-02-22', stage: 'Follow-up',  notes: 'Waiting on fabric choice' },
  { id: 'l4',  client: 'Henderson',  projectType: 'Master Bedroom Drapes', estimatedValue: 8400,  lastContact: '2026-02-20', stage: 'Won',        notes: 'In production' },
  { id: 'l5',  client: 'Kim',        projectType: 'Motorized Shades',      estimatedValue: 15000, lastContact: '2026-02-23', stage: 'Quoted',     notes: 'High-end Lutron system' },
  { id: 'l6',  client: 'Davis',      projectType: 'Shutters 8-window',     estimatedValue: 6800,  lastContact: '2026-02-18', stage: 'Lost',       notes: 'Went with competitor' },
  { id: 'l7',  client: 'Singh',      projectType: 'Dining Valances',       estimatedValue: 3200,  lastContact: '2026-02-26', stage: 'New Lead',   notes: 'Wants consultation this week' },
  { id: 'l8',  client: 'Foster',     projectType: 'Nursery + Guest',       estimatedValue: 5400,  lastContact: '2026-02-21', stage: 'Follow-up',  notes: 'Sent samples, awaiting response' },
  { id: 'l9',  client: 'Abernathy',  projectType: 'Guest Suite Shutters',  estimatedValue: 7200,  lastContact: '2026-02-19', stage: 'Won',        notes: 'Complete, paid in full' },
  { id: 'l10', client: 'Nakamura',   projectType: 'Living Room Sheers',    estimatedValue: 2800,  lastContact: '2026-02-26', stage: 'New Lead',   notes: 'Walk-in inquiry' },
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
};

// ═══════════════════════════════════════════════════════════════
// DESK DEFINITIONS
// ═══════════════════════════════════════════════════════════════

export type DeskId =
  | 'operations' | 'finance' | 'sales' | 'design' | 'estimating'
  | 'clients' | 'contractors' | 'support' | 'marketing'
  | 'website' | 'it' | 'legal' | 'lab';

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

export interface Contractor {
  id: string;
  name: string;
  specialty: string;
  rate: number;
  phone: string;
  available: boolean;
  rating: number;
  jobsCompleted: number;
}

export const MOCK_CONTRACTORS: Contractor[] = [
  { id: 'ct1', name: 'Maria G.',   specialty: 'Sewing / Fabrication', rate: 55, phone: '(512) 555-0201', available: true,  rating: 4.9, jobsCompleted: 87 },
  { id: 'ct2', name: 'James K.',   specialty: 'Sewing / Cutting',    rate: 50, phone: '(512) 555-0202', available: true,  rating: 4.7, jobsCompleted: 62 },
  { id: 'ct3', name: 'Carlos R.',  specialty: 'Installation',        rate: 75, phone: '(512) 555-0203', available: false, rating: 4.8, jobsCompleted: 114 },
  { id: 'ct4', name: 'David M.',   specialty: 'Motorization',        rate: 85, phone: '(512) 555-0204', available: true,  rating: 4.6, jobsCompleted: 43 },
  { id: 'ct5', name: 'Ana S.',     specialty: 'Installation',        rate: 70, phone: '(512) 555-0205', available: true,  rating: 4.5, jobsCompleted: 38 },
  { id: 'ct6', name: 'Roberto L.', specialty: 'Heavy Drapery',       rate: 80, phone: '(512) 555-0206', available: false, rating: 4.9, jobsCompleted: 95 },
];

// ═══════════════════════════════════════════════════════════════
// SUPPORT
// ═══════════════════════════════════════════════════════════════

export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed';

export interface SupportTicket {
  id: string;
  client: string;
  issue: string;
  status: TicketStatus;
  priority: 'low' | 'medium' | 'high';
  createdAt: string;
  category: string;
}

export const TICKET_STATUSES: TicketStatus[] = ['open', 'in_progress', 'resolved', 'closed'];

export const MOCK_TICKETS: SupportTicket[] = [
  { id: 'tk1', client: 'Delgado',   issue: 'Cord mechanism jammed on Roman shade',    status: 'open',        priority: 'high',   createdAt: '2026-02-25', category: 'Mechanical' },
  { id: 'tk2', client: 'Chen',      issue: 'Slight color mismatch between panels',    status: 'in_progress', priority: 'medium', createdAt: '2026-02-24', category: 'Quality' },
  { id: 'tk3', client: 'Henderson', issue: 'Motorized shade not responding to remote', status: 'open',        priority: 'high',   createdAt: '2026-02-23', category: 'Motorization' },
  { id: 'tk4', client: 'Abernathy', issue: 'Request for additional holdback hardware', status: 'resolved',    priority: 'low',    createdAt: '2026-02-20', category: 'Hardware' },
  { id: 'tk5', client: 'Patterson', issue: 'Blackout lining letting light through edges', status: 'in_progress', priority: 'medium', createdAt: '2026-02-22', category: 'Quality' },
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
}

export const MOCK_POSTS: ContentPost[] = [
  { id: 'p1', title: 'Before/After: Henderson Master Suite',     platform: 'Instagram', status: 'published',  scheduledDate: '2026-02-24', engagement: 847 },
  { id: 'p2', title: '5 Tips for Choosing Drapery Fabric',       platform: 'Blog',      status: 'published',  scheduledDate: '2026-02-22', engagement: 312 },
  { id: 'p3', title: 'Spring Collection Fabric Reveal',          platform: 'Instagram', status: 'scheduled',  scheduledDate: '2026-03-01' },
  { id: 'p4', title: 'Client Testimonial: Abernathy Project',    platform: 'Facebook',  status: 'draft',      scheduledDate: '' },
  { id: 'p5', title: 'Motorized Shades Demo Reel',              platform: 'TikTok',    status: 'scheduled',  scheduledDate: '2026-03-03' },
  { id: 'p6', title: 'Design Trends 2026: Layered Treatments',  platform: 'Pinterest', status: 'draft',      scheduledDate: '' },
];
