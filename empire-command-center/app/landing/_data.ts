// empirebox.store landing — module + process data (2026-10 rewrite).
// Three public groups: Home & design, Business tools, Documents.
// Retired/internal modules (Owner's Desk, Dashboard, System, Tokens & Costs,
// Hardware, PlatformForge, VetForge, PetForge, etc.) are intentionally omitted.
// ApostApp is its own separate service and is NOT linked to Workroom.

import type { LucideIcon } from 'lucide-react';
import {
  Stamp, Scissors, Hammer, Bot, RefreshCw, Sparkles, Palette, Gem,
  Target, Megaphone, PencilRuler, Cpu, Wrench, CheckCircle2,
} from 'lucide-react';

export type PublicLabel = 'available' | 'development' | 'preview' | 'roadmap';

export type ModuleEntry = {
  id: string;
  name: string;
  icon: LucideIcon;
  status: PublicLabel;
  statusText: string;
  description: string;
  /** Omit for coming-soon modules: card renders without a link (no dead anchors). */
  ctaLabel?: string;
  ctaHref?: string;
  ariaLabel?: string;
};

export type ModuleGroup = {
  id: string;
  title: string;
  intro: string;
  modules: ModuleEntry[];
};

export const GROUPS: ModuleGroup[] = [
  {
    id: 'home-design',
    title: 'Home & design',
    intro: 'Custom soft goods, fabrics, and woodwork for homes and commercial spaces.',
    modules: [
      {
        id: 'workroom',
        name: 'Empire Workroom',
        icon: Scissors,
        status: 'available',
        statusText: 'Available',
        description:
          'Custom drapery, roman shades, upholstery, and cushions — measured, drawn, quoted, and built in our own workroom.',
        ctaLabel: 'Visit the Workroom →',
        ctaHref: 'https://workroom.empirebox.store',
      },
      {
        id: 'fabrics',
        name: 'Empire Fine Fabrics',
        icon: Palette,
        status: 'available',
        statusText: 'Available',
        description:
          'Browse decorator fabrics by use and material — velvets, linens, silks, performance weaves, and vinyls.',
        ctaLabel: 'Shop fabrics →',
        ctaHref: 'https://fabrics.empirebox.store',
      },
      {
        id: 'pillows',
        name: 'Empire pillow line',
        icon: Sparkles,
        status: 'roadmap',
        statusText: 'Coming soon',
        description: 'Ready-made decorative pillows sewn in our workroom from our own fabric collection.',
      },
      {
        id: 'luxeforge',
        name: 'LuxeForge',
        icon: Gem,
        status: 'preview',
        statusText: 'Founder preview',
        description:
          'Design visualization for interiors — see fabrics and finishes on your own room before anything is cut.',
      },
      {
        id: 'woodworks',
        name: 'Empire Woodworks',
        icon: Hammer,
        status: 'roadmap',
        statusText: 'Coming soon',
        description:
          'Custom millwork and furniture — wall units, built-ins, benches, and panels, from 3D design to CNC cutting to hand finishing.',
        ariaLabel: 'Empire Woodworks — coming soon at woodworks.empirebox.store',
      },
    ],
  },
  {
    id: 'business-tools',
    title: 'Business tools',
    intro: 'The software we built to run our own shop, offered to other small service businesses.',
    modules: [
      {
        id: 'max',
        name: 'MAX',
        icon: Bot,
        status: 'preview',
        statusText: 'Founder preview',
        description:
          'An AI operations assistant that drafts quotes, summarizes messages, and keeps the daily brief — the operator approves everything.',
      },
      {
        id: 'leadforge',
        name: 'LeadForge',
        icon: Target,
        status: 'development',
        statusText: 'In active development',
        description: 'Finds and organizes prospective customers so follow-ups do not fall through the cracks.',
      },
      {
        id: 'socialforge',
        name: 'SocialForge',
        icon: Megaphone,
        status: 'development',
        statusText: 'In active development',
        description: 'Plans and drafts social posts from your finished work, with review before anything is published.',
      },
      {
        id: 'relistapp',
        name: 'RelistApp',
        icon: RefreshCw,
        status: 'development',
        statusText: 'In active development',
        description: 'Re-lists items across marketplaces with operator approval before each post.',
      },
    ],
  },
  {
    id: 'documents',
    title: 'Documents',
    intro: 'A separate service, unrelated to the design workroom.',
    modules: [
      {
        id: 'apostapp',
        name: 'ApostApp',
        icon: Stamp,
        status: 'available',
        statusText: 'Available',
        description:
          'Document apostille and authentication intake with order tracking, for Washington DC, Maryland, and Virginia.',
        ctaLabel: 'Go to ApostApp →',
        ctaHref: 'https://apostapp.empirebox.store/apostille',
        ariaLabel: 'ApostApp — separate document service at apostapp.empirebox.store',
      },
    ],
  },
];

/** Design → build process (Empire Woodworks / Workroom). */
export const PROCESS_STEPS: { title: string; body: string; icon: LucideIcon }[] = [
  { title: 'Measure & 3D design', body: 'We measure on site and model the piece in 3D so you approve proportions, finish, and fabric before anything is cut.', icon: PencilRuler },
  { title: 'CNC cutting', body: 'Panels and parts are cut on our CNC from the approved model — accurate to the drawing, repeatable, clean edges.', icon: Cpu },
  { title: 'Build & upholster', body: 'Assembly, joinery, foam, and fabric work happen in our own workroom.', icon: Wrench },
  { title: 'Finish & install', body: 'Hand finishing, final inspection, and installation in your space.', icon: CheckCircle2 },
];

/**
 * Recent work. Photos are PLACEHOLDERS until Rafael approves specific images
 * for public use. Never put client names or addresses here.
 */
export const RECENT_WORK: { id: string; title: string; category: string; blurb: string; photoNeeded: string }[] = [
  { id: 'walnut-wall-unit', title: 'Walnut wall unit', category: 'Empire Woodworks', blurb: 'Full-wall walnut media and storage unit, designed in 3D and CNC-cut.', photoNeeded: '3D render + CNC parts + installed photo (approved for public use)' },
  { id: 'banquette', title: 'Upholstered banquette seating', category: 'Workroom', blurb: 'U- and L-shaped bench seating with custom foam and fabric.', photoNeeded: 'Finished banquette photo (approved)' },
  { id: 'lobby-drapery', title: 'Commercial lobby drapery', category: 'Workroom', blurb: 'Drapery and window treatments for a commercial lobby.', photoNeeded: 'Installed drapery photo, no signage or address visible (approved)' },
  { id: 'roman-shades', title: 'Roman shades', category: 'Workroom', blurb: 'Lined roman shades, measured and built to the window.', photoNeeded: 'Finished shades photo (approved)' },
];
