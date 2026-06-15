// R1X-PUB-EMPIREBOX — module + workflow data.
// Source of truth: R1X-PUB-EMPIREBOX-COPY.md §2.D (module cards)
// and R1X-PUB-EMPIREBOX-COPY.md §2.E (workflows).
// Four public labels ONLY: Available / In active development /
// Founder preview / On the roadmap. RED ShipForge is intentionally omitted.

import type { LucideIcon } from 'lucide-react';
import {
  Stamp, Scissors, Hammer, HardHat, Calculator, Bot,
  Building2, RefreshCw, FileText, Mail, ShieldCheck, Cog,
  Users, ClipboardList, Tag, Sparkles, Wrench, ShoppingBag,
  Briefcase, CreditCard, Layers, BookOpen, Heart, PawPrint,
  Cpu, Bell, Network, Archive, Boxes, Database, Activity,
  DollarSign, ImageIcon, PencilRuler, HardDrive,
} from 'lucide-react';

export type PublicLabel = 'available' | 'development' | 'preview' | 'roadmap';

export type ModuleEntry = {
  id: string;
  name: string;
  icon: LucideIcon;
  status: PublicLabel;
  statusText: string;     // Public-facing pill text
  description: string;
  ctaLabel: string;
  ctaHref: string;
  verified: 'full' | 'partial' | 'founder' | 'vision';
  /** Optional aria-label for the card link. */
  ariaLabel?: string;
};

/**
 * Module grid. 32 GREEN/YELLOW modules from the registry + 2 PARKED roadmap
 * cards. RED ShipForge is excluded. The 5th row's MAX Continuity (phone
 * surface dead) and SupportForge (operator-only ORANGE) are NOT included
 * in the public set — they are internal-only and must not appear publicly.
 *
 * The list order roughly follows the COPY doc's section grouping.
 */
export const MODULES: ModuleEntry[] = [
  // ───── Documents & Compliance ─────
  {
    id: 'apostapp',
    name: 'ApostApp',
    icon: Stamp,
    status: 'available',
    statusText: 'Available',
    description:
      'Public document apostille and authentication intake, with status tracking, for Washington DC, Maryland, and Virginia.',
    ctaLabel: 'Start an ApostApp order →',
    ctaHref: 'https://apostapp.empirebox.store/apostille',
    verified: 'full',
    ariaLabel: 'ApostApp — start an order at apostapp.empirebox.store',
  },
  {
    id: 'apostapp-status',
    name: 'ApostApp status tracking',
    icon: FileText,
    status: 'available',
    statusText: 'Available',
    description:
      'A read-only public tracker where an ApostApp customer can check the current status of an order by reference number.',
    ctaLabel: 'Track an order →',
    ctaHref: 'https://apostapp.empirebox.store/apostille/status',
    verified: 'full',
  },
  {
    id: 'llcfactory',
    name: 'LLCFactory',
    icon: Building2,
    status: 'development',
    statusText: 'In active development',
    description:
      'Helps you form a US LLC end-to-end — name check, filing, operating agreement, EIN, and the documents most people need to apostille afterward.',
    ctaLabel: 'Request early access →',
    ctaHref: '#start',
    verified: 'partial',
  },
  {
    id: 'vendorops',
    name: 'VendorOps',
    icon: Network,
    status: 'development',
    statusText: 'In active development',
    description:
      'Coordinates the notaries, translators, couriers, and government offices that a document workflow touches.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'partial',
  },
  {
    id: 'transcriptforge',
    name: 'TranscriptForge',
    icon: ClipboardList,
    status: 'development',
    statusText: 'In active development',
    description:
      'Speech-to-text and structured meeting notes with a human approval gate before anything is filed.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'partial',
  },

  // ───── Business Formation ─────
  {
    id: 'empireassist',
    name: 'EmpireAssist',
    icon: Mail,
    status: 'preview',
    statusText: 'Founder preview',
    description:
      'A template-and-helper layer that drafts routine business writing — proposals, follow-up emails, social posts, customer replies — with operator review before anything is sent.',
    ctaLabel: 'Request Founder preview →',
    ctaHref: '#start',
    verified: 'partial',
  },
  {
    id: 'max',
    name: 'MAX',
    icon: Bot,
    status: 'preview',
    statusText: 'Founder preview',
    description:
      'The operator brain behind EmpireBox — coordinates modules, drafts responses, summarizes documents, and keeps the daily brief. Founder-only at this time.',
    ctaLabel: 'Request Founder preview →',
    ctaHref: '#start',
    verified: 'founder',
  },
  {
    id: 'owners-desk',
    name: "Owner's Desk",
    icon: Briefcase,
    status: 'preview',
    statusText: 'Founder preview',
    description:
      "A single dashboard that aggregates the day's work across modules — costs, tasks, messages, follow-ups.",
    ctaLabel: 'Request Founder preview →',
    ctaHref: '#start',
    verified: 'founder',
  },
  {
    id: 'max-avatar',
    name: 'MAX Avatar',
    icon: Sparkles,
    status: 'preview',
    statusText: 'Founder preview',
    description:
      'Text-to-speech avatar for operator-facing outputs. Founder-only at this time.',
    ctaLabel: 'Request Founder preview →',
    ctaHref: '#start',
    verified: 'founder',
  },
  {
    id: 'dashboard',
    name: 'Dashboard',
    icon: Activity,
    status: 'preview',
    statusText: 'Founder preview',
    description:
      'Composite view of MAX, desks, costs, and tasks. Founder-only at this time.',
    ctaLabel: 'Request Founder preview →',
    ctaHref: '#start',
    verified: 'founder',
  },

  // ───── Custom Work & Service ─────
  {
    id: 'workroom',
    name: 'Empire Workroom',
    icon: Scissors,
    status: 'available',
    statusText: 'Available',
    description:
      'Upholstery and drapery workflow — intake, materials, drawing references, and pricing for custom soft-goods work.',
    ctaLabel: 'See a sample project →',
    ctaHref: '#how-it-works',
    verified: 'full',
  },
  {
    id: 'woodcraft',
    name: 'WoodCraft',
    icon: Hammer,
    status: 'available',
    statusText: 'Available',
    description:
      'Furniture and CNC workflow — intake, cut lists, drawings, and pricing for custom wood and millwork.',
    ctaLabel: 'See a sample project →',
    ctaHref: '#how-it-works',
    verified: 'full',
  },
  {
    id: 'pricing-studio',
    name: 'Pricing Studio',
    icon: Calculator,
    status: 'available',
    statusText: 'Available',
    description:
      'A pricing engine that turns a project description and a target margin into a clean, defensible quote.',
    ctaLabel: 'See how it works →',
    ctaHref: '#how-it-works',
    verified: 'full',
  },
  {
    id: 'drawing-studio',
    name: 'Drawing Studio',
    icon: PencilRuler,
    status: 'preview',
    statusText: 'Founder preview',
    description:
      'Generates annotated schematics for fabrication — useful as a starting reference, not yet a finished client deliverable.',
    ctaLabel: 'Request Founder preview →',
    ctaHref: '#start',
    verified: 'partial',
  },
  {
    id: 'ai-vision',
    name: 'AI Vision',
    icon: ImageIcon,
    status: 'available',
    statusText: 'Available',
    description:
      'Image understanding for catalogs, materials, and reference photos — used by the Workroom and WoodCraft modules.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'full',
  },
  {
    id: 'recoveryforge',
    name: 'RecoveryForge',
    icon: Wrench,
    status: 'development',
    statusText: 'In active development',
    description:
      'Recovery and restoration workflow for damaged soft-goods, photos, and reference materials.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'partial',
  },
  {
    id: 'constructionforge',
    name: 'ConstructionForge',
    icon: HardHat,
    status: 'development',
    statusText: 'In active development',
    description:
      'A CRM for construction and land projects, with bilingual intake.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'partial',
  },
  {
    id: 'luxeforge',
    name: 'LuxeForge',
    icon: Tag,
    status: 'development',
    statusText: 'In active development',
    description:
      'A focused workflow for high-end custom work, with curated intake and quote handling.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'partial',
  },
  {
    id: 'storefront-forge',
    name: 'StoreFront Forge',
    icon: ShoppingBag,
    status: 'development',
    statusText: 'In active development',
    description:
      'A single-tenant point-of-sale for a service-led shop.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'partial',
  },

  // ───── Operations & Growth ─────
  {
    id: 'contractorforge',
    name: 'ContractorForge',
    icon: HardHat,
    status: 'development',
    statusText: 'In active development',
    description:
      'Coordinates service jobs — intake, scheduling, vendor routing, and follow-up — for contractors and service businesses.',
    ctaLabel: 'See a workflow →',
    ctaHref: '#how-it-works',
    verified: 'partial',
  },
  {
    id: 'leadforge',
    name: 'LeadForge',
    icon: Users,
    status: 'development',
    statusText: 'In active development',
    description:
      'Lead capture and follow-up, shared with the rest of the ecosystem so a lead can become a quote, a project, and an invoice without retyping.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'partial',
  },
  {
    id: 'forgecrm',
    name: 'ForgeCRM',
    icon: Users,
    status: 'available',
    statusText: 'Available',
    description:
      'Customer, contact, and lead records with a clean handoff into the other modules.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'full',
  },
  {
    id: 'socialforge',
    name: 'SocialForge',
    icon: Network,
    status: 'development',
    statusText: 'In active development',
    description:
      'A content and channel manager — drafts, calendar, and connected accounts, with operator approval before anything is published.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'partial',
  },
  {
    id: 'empirepay',
    name: 'EmpirePay',
    icon: CreditCard,
    status: 'development',
    statusText: 'In active development',
    description:
      'Payment links and a crypto rail alongside traditional methods, with a single ledger entry per transaction.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'partial',
  },
  {
    id: 'amp',
    name: 'AMP',
    icon: BookOpen,
    status: 'available',
    statusText: 'Available',
    description:
      'A standalone, bilingual personal-dev surface that is safe to share with a collaborator.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'full',
  },
  {
    id: 'archiveforge',
    name: 'ArchiveForge',
    icon: Archive,
    status: 'available',
    statusText: 'Available',
    description:
      'A clean archive for documents, drawings, and reference materials — searchable, auditable, and easy to retrieve.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'full',
  },
  {
    id: 'marketforge',
    name: 'MarketForge',
    icon: Boxes,
    status: 'development',
    statusText: 'In active development',
    description:
      'Cross-marketplace listing and inventory, shared with RelistApp for second-pass publishing.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'partial',
  },
  {
    id: 'relistapp',
    name: 'RelistApp',
    icon: RefreshCw,
    status: 'development',
    statusText: 'In active development',
    description:
      "Re-lists an existing item across marketplaces with operator approval before each post.",
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'partial',
  },
  {
    id: 'platformforge',
    name: 'PlatformForge',
    icon: Layers,
    status: 'available',
    statusText: 'Available',
    description:
      'The platform layer — Docker, module registry, system monitor — that keeps EmpireBox healthy in production.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'full',
  },
  {
    id: 'system',
    name: 'System',
    icon: Cog,
    status: 'available',
    statusText: 'Available',
    description:
      'A simple system monitor and developer panel for the operator.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'full',
  },
  {
    id: 'tokens-costs',
    name: 'Tokens & Costs',
    icon: DollarSign,
    status: 'preview',
    statusText: 'Founder preview',
    description:
      'Per-tenant cost tracking that lets the operator see what each module and desk actually costs to run.',
    ctaLabel: 'Request Founder preview →',
    ctaHref: '#start',
    verified: 'founder',
  },
  {
    id: 'notifications',
    name: 'Notifications',
    icon: Bell,
    status: 'available',
    statusText: 'Available',
    description:
      'A clean topbar unread-count and inbox experience, shared across the modules.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'full',
  },
  {
    id: 'ecosystem-catalog',
    name: 'Ecosystem Catalog',
    icon: Database,
    status: 'available',
    statusText: 'Available',
    description:
      'The structured catalog that the operator brain reads to know which module does what and how to route work.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'full',
  },
  {
    id: 'hardware',
    name: 'Hardware',
    icon: HardDrive,
    status: 'development',
    statusText: 'In active development',
    description:
      'A documentation and device-status surface for the on-prem hardware that runs EmpireBox. Operator-focused.',
    ctaLabel: 'See how it fits →',
    ctaHref: '#ecosystem',
    verified: 'partial',
  },

  // ───── On the roadmap (PARKED in registry) ─────
  {
    id: 'vetforge',
    name: 'VetForge',
    icon: ShieldCheck,
    status: 'roadmap',
    statusText: 'On the roadmap',
    description:
      'A focused module for veterinary practices, gated behind legal review for VA compliance.',
    ctaLabel: 'Join the waitlist →',
    ctaHref: '#start',
    verified: 'vision',
  },
  {
    id: 'petforge',
    name: 'PetForge',
    icon: PawPrint,
    status: 'roadmap',
    statusText: 'On the roadmap',
    description:
      'A focused module for pet-services businesses, not yet implemented.',
    ctaLabel: 'Join the waitlist →',
    ctaHref: '#start',
    verified: 'vision',
  },
];

/**
 * The 5 "How it works" examples from COPY §2.E.
 * Markers ([VERIFIED] / [VERIFIED_PARTIAL] / [VISION-ONLY]) are mapped to
 * three visual classes: `full`, `partial`, `vision`. A fourth `founder` class
 * is used for FOUNDER-ONLY modules.
 */
export type WorkflowStep = {
  title: string;
  body: string;
  /** Marker class — used to color the small inline badge. */
  marker: 'full' | 'partial' | 'vision' | 'founder';
  /** Optional explicit marker text override (e.g. "VERIFIED", "VERIFIED_PARTIAL"). */
  markerText?: string;
};
export type Workflow = {
  id: string;
  label: string;
  badge: string;     // e.g. "MOSTLY VERIFIED", "VERIFIED", "VERIFIED_PARTIAL", "FOUNDER-ONLY"
  steps: WorkflowStep[];
  honestLimits: string;
};

export const WORKFLOWS: Workflow[] = [
  {
    id: 'wf-apostille',
    label: 'Example 1 — Apostille',
    badge: 'Mostly verified',
    steps: [
      { title: 'Open the ApostApp intake', body: 'Visit apostapp.empirebox.store/apostille and fill in the intake — name, email, phone, document type, destination country, urgency.', marker: 'full' },
      { title: 'Upload the document', body: 'Submit the document you need apostilled. ApostApp accepts the common formats used for DC, MD, and VA submissions.', marker: 'full' },
      { title: 'Receive a written quote', body: 'The operator reviews your intake and sends back a written quote and a payment instruction. Payment is operator-mediated in v1, not Stripe-automated.', marker: 'partial', markerText: 'VERIFIED_PARTIAL' },
      { title: 'Pay via the operator’s standard methods', body: 'Pay using the operator’s standard payment methods (Zelle, Venmo, wire — as instructed). ApostApp does not run a self-service checkout.', marker: 'partial', markerText: 'VERIFIED_PARTIAL' },
      { title: 'Track the order by reference number', body: 'Use the public status page at apostapp.empirebox.store/apostille/status to follow progress.', marker: 'full' },
    ],
    honestLimits:
      'EmpireBox does not submit documents to government offices on the customer’s behalf. The operator (or a designated vendor) physically takes the document to the DC, MD, or VA Secretary of State office. Government processing times vary and are outside EmpireBox’s control.',
  },
  {
    id: 'wf-service-business',
    label: 'Example 2 — Service business',
    badge: 'Verified (in parts)',
    steps: [
      { title: 'Send the customer your intake link', body: 'ContractorForge creates the job from the customer’s answers — no retyping.', marker: 'partial' },
      { title: 'Review and lock the scope', body: 'Review the intake, ask the customer for any missing details, and lock the scope.', marker: 'partial' },
      { title: 'Build a quote with Pricing Studio', body: 'Materials, labor, margin, tax, lead time — Pricing Studio does the math.', marker: 'full' },
      { title: 'Send the quote; the customer accepts', body: 'When the customer accepts, the job becomes a project in the same record.', marker: 'partial' },
      { title: 'Track follow-ups and change orders', body: 'Follow-ups, change orders, and completion live in the same record — no scattered spreadsheets.', marker: 'partial' },
    ],
    honestLimits:
      'EmpireBox helps organize the workflow. It does not physically do the work, and it does not promise automated scheduling, automated payments, or automated customer messaging at this time. Operator review is required at every step.',
  },
  {
    id: 'wf-fabrication',
    label: 'Example 3 — Custom fabrication',
    badge: 'Verified (in parts)',
    steps: [
      { title: 'Capture measurements, photos, references', body: 'Capture the customer’s measurements, photos, and reference materials for the job.', marker: 'full' },
      { title: 'Start a project in Workroom or WoodCraft', body: 'Empire Workroom handles upholstery and drapery; WoodCraft handles furniture and millwork.', marker: 'full' },
      { title: 'Pull material and finish data', body: 'Pull fabric, finish, and dimension data. AI Vision can read reference photos for material identification.', marker: 'full' },
      { title: 'Generate a starting schematic', body: 'Drawing Studio produces a working-reference schematic — not a final client deliverable at this time.', marker: 'partial' },
      { title: 'Price with Pricing Studio', body: 'A clean, defensible quote is one click away once the parameters are set.', marker: 'full' },
    ],
    honestLimits:
      'EmpireBox does not run your CNC machine, your cutting table, or your sewing room. The drawing output is a working reference; final shop drawings remain the operator’s responsibility at this time.',
  },
  {
    id: 'wf-pricing',
    label: 'Example 4 — Pricing Studio',
    badge: 'Verified',
    steps: [
      { title: 'Describe the project', body: 'Items, materials, labor, target margin, tax region — the inputs Pricing Studio needs.', marker: 'full' },
      { title: 'Review the price', body: 'Pricing Studio returns a defensible number built from your inputs and the maintained catalog.', marker: 'full' },
      { title: 'Adjust and lock the price', body: 'Adjust assumptions if needed; lock the price; share the quote with your customer.', marker: 'full' },
    ],
    honestLimits:
      'The pricing engine is a tool. Final pricing decisions — including any discounts, market adjustments, or relationship pricing — are the operator’s call. The engine does not make those calls for you.',
  },
  {
    id: 'wf-operator',
    label: 'Example 5 — Operator brain',
    badge: 'Founder-only',
    steps: [
      { title: 'Route inbound calls, texts, and emails', body: 'MAX routes them to the operator brain for summarization and drafting.', marker: 'partial' },
      { title: 'Review the daily brief', body: 'What came in, what went out, what is overdue — at a glance.', marker: 'full' },
      { title: 'Approve, edit, or send drafts', body: 'Nothing leaves the system without operator review.', marker: 'partial' },
      { title: 'Add new tasks or follow-ups', body: 'New tasks and follow-ups live in the same place as the rest of the day’s work.', marker: 'full' },
    ],
    honestLimits:
      'This is a Founder preview surface at this time. EmpireBox does not make outbound calls or send messages on its own — the operator always approves before anything leaves the system.',
  },
];
