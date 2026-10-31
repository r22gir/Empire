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
  /** Public image path (already published under /public). */
  image?: string;
  imageAlt?: string;
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
        image: '/workroom-showroom/photos/drapery-bay-cream-lounge.jpg',
        imageAlt: 'Custom drapery in a bay window',
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
        image: '/empirebox-landing/swatch-GHBVSAGE.png',
        imageAlt: 'Botanical vine linen swatch',
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
        image: '/workroom-showroom/photos/softgoods-trellis-corner.jpg',
        imageAlt: 'Decorative soft goods with trellis fabric',
        name: 'Empire pillow line',
        icon: Sparkles,
        status: 'roadmap',
        statusText: 'Coming soon',
        description: 'Ready-made decorative pillows sewn in our workroom from our own fabric collection.',
      },
      {
        id: 'luxeforge',
        image: '/workroom-showroom/photos/bed-cognac-panel-headboard.jpg',
        imageAlt: 'Cognac channel headboard',
        name: 'LuxeForge',
        icon: Gem,
        status: 'preview',
        statusText: 'Founder preview',
        description:
          'Design visualization for interiors — see fabrics and finishes on your own room before anything is cut.',
      },
      {
        id: 'woodworks',
        image: '/workroom-showroom/photos/woodcraft-chevron-island.jpg',
        imageAlt: 'Chevron-front custom island',
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
export const PROCESS_STEPS: { title: string; body: string; icon: LucideIcon; image: string; alt: string }[] = [
  { title: 'Measure & 3D design', body: 'We measure on site and model the piece in 3D so you approve proportions, finish, and fabric before anything is cut.', icon: PencilRuler, image: '/empirebox-landing/process-3d-design.jpg', alt: '3D model of a curved upholstered bench' },
  { title: 'CNC cutting', body: 'Panels and parts are cut on our CNC from the approved model — accurate to the drawing, repeatable, clean edges.', icon: Cpu, image: '/empirebox-landing/process-cnc-nest.jpg', alt: 'CNC nesting sheet with curved plywood parts' },
  { title: 'Build & upholster', body: 'Assembly, joinery, foam, and fabric work happen in our own workroom.', icon: Wrench, image: '/workroom-showroom/photos/banquette-teal-tufted-bench.jpg', alt: 'Tufted teal banquette bench' },
  { title: 'Finish & install', body: 'Hand finishing, final inspection, and installation in your space.', icon: CheckCircle2, image: '/workroom-showroom/photos/drapery-window-nook.jpg', alt: 'Installed drapery in a window nook' },
];

/** Recent work gallery — photos already published on the Workroom showroom. No client names/addresses. */
export const GALLERY: { src: string; title: string; tag: string }[] = [
  { src: '/workroom-showroom/photos/sheers-tall-living.jpg', title: 'Floor-to-ceiling sheers', tag: 'Workroom' },
  { src: '/workroom-showroom/photos/woodcraft-champagne-lounge.jpg', title: 'Champagne lounge millwork', tag: 'Woodworks' },
  { src: '/workroom-showroom/photos/banquette-plant-wall.jpg', title: 'Banquette with plant wall', tag: 'Workroom' },
  { src: '/workroom-showroom/photos/romans-bay-nook.jpg', title: 'Roman shades, bay nook', tag: 'Workroom' },
  { src: '/workroom-showroom/photos/bed-mauve-channel.jpg', title: 'Channel-tufted headboard', tag: 'Upholstery' },
  { src: '/workroom-showroom/photos/seating-herringbone-sectional.jpg', title: 'Herringbone sectional', tag: 'Upholstery' },
];

export const SWATCHES: { src: string; name: string; material: string }[] = [
  { src: '/empirebox-landing/swatch-GHBVSAGE.png', name: 'Botanical Vine · Sage', material: 'Linen' },
  { src: '/empirebox-landing/swatch-KDCIVORY.png', name: 'Damask Court · Ivory', material: 'Silk' },
  { src: '/empirebox-landing/swatch-V638.png', name: 'Cuaderno · Teak', material: 'Vinyl' },
  { src: '/empirebox-landing/swatch-54080000.png', name: 'Canvas · Navy', material: 'Cotton' },
  { src: '/empirebox-landing/swatch-GHQCIVORY.png', name: 'Quiet Check · Ivory', material: 'Linen' },
  { src: '/empirebox-landing/swatch-SVI001.png', name: 'Vintage Ale · Saddle', material: 'Vinyl' },
];
