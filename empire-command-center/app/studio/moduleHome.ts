/**
 * Studio (founder) edition: where every existing module lives after declutter.
 * Nothing is deleted — daily path, Work pipeline, Settings/System, or the + sheet.
 * Family editions (AMP / Maxine) are not read or written here.
 */

export const STUDIO_TABS = ['max', 'today', 'work', 'money'] as const;
export type StudioTab = (typeof STUDIO_TABS)[number];

export type ModuleHome =
  | 'max'
  | 'today'
  | 'work'
  | 'work-pipeline'
  | 'work-clients'
  | 'work-docs'
  | 'money'
  | 'settings-system'
  | 'settings-planned'
  | 'plus-sheet';

export interface StudioModule {
  id: string;
  name: string;
  home: ModuleHome;
  /** How the founder opens it after declutter. */
  path: string;
  hiddenFromDaily: boolean;
  planned?: boolean;
}

/** Planned / stub verticals — hidden from the daily path, still in Settings. */
export const PLANNED_MODULE_IDS = ['vetforge', 'petforge', 'assist'] as const;

/** Dev and system tools — out of the daily path, in Settings → System. */
export const SYSTEM_MODULE_IDS = [
  'platform',
  'openclaw',
  'max-continuity',
  'tokens',
  'hardware',
  'dev',
  'recovery',
  'system',
  'improvements',
  'family-help',
  'minimax-usage',
] as const;

/** Duplicate schedule / money / client entries merged into one home each. */
export const MERGED_ENTRY_IDS = {
  schedule: ['schedule', 'calendar', 'organizer', 'tasks'],
  money: ['pay', 'invoices', 'finance', 'expenses', 'payments'],
  clients: ['crm', 'customers'],
} as const;

export const STUDIO_MODULES: StudioModule[] = [
  { id: 'owner', name: "Owner's Desk / typed chat", home: 'max', path: '/?tab=max&screen=chat', hiddenFromDaily: false },
  { id: 'voice', name: 'Live voice (single orb)', home: 'max', path: '/?tab=max', hiddenFromDaily: false },
  { id: 'max-avatar', name: 'MAX Avatar / Presentation', home: 'plus-sheet', path: '/?screen=presentation', hiddenFromDaily: false },
  { id: 'video', name: 'Video Call', home: 'plus-sheet', path: '/?screen=video', hiddenFromDaily: false },
  { id: 'telegram', name: 'Telegram', home: 'plus-sheet', path: '/?screen=telegram', hiddenFromDaily: false },
  { id: 'memory-bank', name: 'Memory Bank', home: 'plus-sheet', path: '/?screen=memory-bank', hiddenFromDaily: false },
  { id: 'research', name: 'Research desk', home: 'plus-sheet', path: '/?screen=research', hiddenFromDaily: false },
  { id: 'whatsapp', name: 'WhatsApp Chats', home: 'plus-sheet', path: '/?screen=whatsapp', hiddenFromDaily: false },

  { id: 'approvals', name: 'Approvals', home: 'today', path: '/?tab=today&need=approvals', hiddenFromDaily: false },
  { id: 'schedule', name: 'Organizer / Calendar / Schedule', home: 'today', path: '/?tab=today', hiddenFromDaily: false },
  { id: 'tasks', name: 'Tasks / Reminders', home: 'today', path: '/?tab=today&need=tasks', hiddenFromDaily: false },
  { id: 'daily-summary', name: 'Daily Summary', home: 'today', path: '/?tab=today', hiddenFromDaily: false },
  { id: 'inbox', name: 'Inbox / notifications', home: 'today', path: '/?screen=inbox', hiddenFromDaily: false },

  { id: 'lead', name: 'LeadForge', home: 'work-pipeline', path: '/?tab=work&stage=lead', hiddenFromDaily: false },
  { id: 'workroom', name: 'Empire Workroom', home: 'work', path: '/?tab=work&product=workroom', hiddenFromDaily: false },
  { id: 'craft', name: 'WoodCraft', home: 'work-pipeline', path: '/?tab=work&space=woodcraft', hiddenFromDaily: false },
  { id: 'construction', name: 'ConstructionForge', home: 'work-pipeline', path: '/?tab=work&space=construction', hiddenFromDaily: false },
  { id: 'quotes', name: 'Quotes / Quick Quote', home: 'work-pipeline', path: '/?tab=work&stage=quote', hiddenFromDaily: false },
  { id: 'pricing-studio', name: 'Pricing Studio', home: 'work', path: '/?screen=pricing-studio', hiddenFromDaily: false },
  { id: 'jobs', name: 'Jobs / Job hub / Work orders', home: 'work-pipeline', path: '/?tab=work&stage=job', hiddenFromDaily: false },
  { id: 'cut', name: 'Cut list / Yardage / Templates', home: 'work-pipeline', path: '/?tab=work&stage=cut', hiddenFromDaily: false },
  { id: 'install', name: 'Install / Organizer installs', home: 'work-pipeline', path: '/?tab=work&stage=install', hiddenFromDaily: false },
  { id: 'crm', name: 'ForgeCRM / Clients', home: 'work-clients', path: '/?tab=work&product=crm', hiddenFromDaily: false },
  { id: 'final-docs', name: 'Final Docs', home: 'work-docs', path: '/?tab=work&docs=1', hiddenFromDaily: false },
  { id: 'drawings', name: 'Drawing Studio', home: 'work', path: '/?product=drawings', hiddenFromDaily: false },
  { id: 'vision', name: 'AI Vision / Quote from photo', home: 'max', path: '/?tab=max&intent=photo', hiddenFromDaily: false },
  { id: 'storefront', name: 'StoreFront Forge', home: 'plus-sheet', path: '/?product=storefront', hiddenFromDaily: false },
  { id: 'luxe', name: 'LuxeForge', home: 'plus-sheet', path: '/?product=luxe', hiddenFromDaily: false },
  { id: 'vendorops', name: 'VendorOps', home: 'plus-sheet', path: '/?product=vendorops', hiddenFromDaily: false },
  { id: 'contractor', name: 'ContractorForge', home: 'plus-sheet', path: '/?product=contractor', hiddenFromDaily: false },
  { id: 'social', name: 'SocialForge', home: 'plus-sheet', path: '/?product=social', hiddenFromDaily: false },
  { id: 'market', name: 'MarketForge', home: 'plus-sheet', path: '/?product=market', hiddenFromDaily: false },
  { id: 'support', name: 'SupportForge', home: 'plus-sheet', path: '/?product=support', hiddenFromDaily: false },
  { id: 'ship', name: 'ShipForge', home: 'plus-sheet', path: '/?product=ship', hiddenFromDaily: false },
  { id: 'amp', name: 'AMP (open family edition)', home: 'plus-sheet', path: '/?product=amp', hiddenFromDaily: false },
  { id: 'archive', name: 'ArchiveForge', home: 'plus-sheet', path: '/?product=archive', hiddenFromDaily: false },
  { id: 'transcript', name: 'TranscriptForge', home: 'plus-sheet', path: '/?product=transcript', hiddenFromDaily: false },
  { id: 'relist', name: 'RelistApp', home: 'plus-sheet', path: '/?product=relist', hiddenFromDaily: false },
  { id: 'llc', name: 'LLCFactory', home: 'plus-sheet', path: '/?product=llc', hiddenFromDaily: false },
  { id: 'apost', name: 'ApostApp', home: 'plus-sheet', path: '/?product=apost', hiddenFromDaily: false },
  { id: 'business-profile', name: 'Business Profile', home: 'plus-sheet', path: '/?screen=business-profile', hiddenFromDaily: false },
  { id: 'company-setup', name: 'Company Setup', home: 'plus-sheet', path: '/?screen=company-setup', hiddenFromDaily: false },

  { id: 'pay', name: 'EmpirePay', home: 'money', path: '/?tab=money&product=pay', hiddenFromDaily: false },
  { id: 'invoices', name: 'Invoices / Finance', home: 'money', path: '/?tab=money&screen=invoices', hiddenFromDaily: false },
  { id: 'deposits', name: 'Deposits', home: 'money', path: '/?tab=money', hiddenFromDaily: false },

  { id: 'settings', name: 'Settings', home: 'settings-system', path: '/?screen=settings', hiddenFromDaily: false },
  { id: 'platform', name: 'PlatformForge', home: 'settings-system', path: '/?product=platform', hiddenFromDaily: true },
  { id: 'openclaw', name: 'OpenClaw', home: 'settings-system', path: '/?product=openclaw', hiddenFromDaily: true },
  { id: 'max-continuity', name: 'MAX Continuity', home: 'settings-system', path: '/?product=max-continuity', hiddenFromDaily: true },
  { id: 'tokens', name: 'Tokens & Costs', home: 'settings-system', path: '/?product=tokens', hiddenFromDaily: true },
  { id: 'hardware', name: 'Hardware', home: 'settings-system', path: '/?product=hardware', hiddenFromDaily: true },
  { id: 'dev', name: 'Developer Panel', home: 'settings-system', path: '/?product=dev', hiddenFromDaily: true },
  { id: 'recovery', name: 'RecoveryForge', home: 'settings-system', path: '/?product=recovery', hiddenFromDaily: true },
  { id: 'system', name: 'System health / Ollama / ticker', home: 'settings-system', path: '/?product=system', hiddenFromDaily: true },
  { id: 'improvements', name: 'Improvements', home: 'settings-system', path: '/?product=improvements', hiddenFromDaily: true },
  { id: 'family-help', name: 'Ayuda de ediciones familiares', home: 'settings-system', path: '/?screen=family-help', hiddenFromDaily: true },
  { id: 'minimax-usage', name: 'Uso MiniMax', home: 'settings-system', path: '/?screen=minimax-usage', hiddenFromDaily: true },
  { id: 'classic', name: 'Classic Command Center', home: 'settings-system', path: '/classic', hiddenFromDaily: true },

  { id: 'assist', name: 'EmpireAssist', home: 'settings-planned', path: '/?product=assist', hiddenFromDaily: true, planned: true },
  { id: 'vetforge', name: 'VetForge', home: 'settings-planned', path: '/?product=vetforge', hiddenFromDaily: true, planned: true },
  { id: 'petforge', name: 'PetForge', home: 'settings-planned', path: '/?product=petforge', hiddenFromDaily: true, planned: true },
];

export function moduleById(id: string): StudioModule | undefined {
  return STUDIO_MODULES.find((m) => m.id === id);
}

export function modulesForHome(home: ModuleHome): StudioModule[] {
  return STUDIO_MODULES.filter((m) => m.home === home);
}

export function isPlannedModule(id: string): boolean {
  return (PLANNED_MODULE_IDS as readonly string[]).includes(id);
}

export function isSystemModule(id: string): boolean {
  return (SYSTEM_MODULE_IDS as readonly string[]).includes(id);
}

export function dailySheetItemIds(ids: string[]): string[] {
  return ids.filter((id) => !isPlannedModule(id) && !isSystemModule(id));
}

export function plusSheetItemIds(ids: string[]): string[] {
  return ids.filter((id) => !isPlannedModule(id));
}

const WORK_PRODUCTS = new Set([
  'workroom', 'craft', 'construction', 'lead', 'crm', 'drawings', 'vision',
  'storefront', 'luxe', 'vendorops', 'contractor', 'social', 'market', 'support',
  'ship', 'amp', 'archive', 'transcript', 'relist', 'llc', 'apost',
]);
const MONEY_PRODUCTS = new Set(['pay']);
const MONEY_SCREENS = new Set(['invoices', 'invoice', 'costs']);
const TODAY_SCREENS = new Set(['calendar', 'tasks', 'inbox', 'mail']);
const MAX_SCREENS = new Set([
  'chat', 'presentation', 'video', 'telegram', 'memory-bank', 'research', 'whatsapp',
]);
const SYSTEM_PRODUCTS = new Set<string>(SYSTEM_MODULE_IDS);

export function tabForRoute(product?: string | null, screen?: string | null, tab?: string | null): StudioTab {
  if (tab && (STUDIO_TABS as readonly string[]).includes(tab)) return tab as StudioTab;
  if (screen && MONEY_SCREENS.has(screen)) return 'money';
  if (screen && TODAY_SCREENS.has(screen)) return 'today';
  if (screen && (MAX_SCREENS.has(screen) || screen === 'settings')) return 'max';
  if (product && SYSTEM_PRODUCTS.has(product)) return 'max';
  if (product && MONEY_PRODUCTS.has(product)) return 'money';
  if (product && WORK_PRODUCTS.has(product)) return 'work';
  if (product === 'owner' || product === 'max-avatar') return 'max';
  return 'max';
}

export function isStudioHomeRoute(product?: string | null, screen?: string | null, tab?: string | null): boolean {
  if (product || screen) return false;
  if (!tab || tab === 'max' || tab === 'today' || tab === 'work' || tab === 'money') return true;
  return false;
}

/** Workroom's 17 sections → 4 primary tabs. Other sections stay reachable via More. */
export const WORKROOM_PRIMARY_TABS = [
  { id: 'jobs', label: 'Jobs', sections: ['overview', 'jobhub', 'jobs', 'work-orders', 'creations', 'inventory', 'templates', 'tasks', 'analysis'] },
  { id: 'quotes', label: 'Quotes', sections: ['quotes'] },
  { id: 'clients', label: 'Clients', sections: ['customers'] },
  { id: 'docs', label: 'Docs', sections: ['docs'] },
] as const;

export const WORKROOM_MONEY_SECTIONS = ['finance', 'invoices', 'expenses', 'payments'] as const;
export const WORKROOM_TODAY_SECTIONS = ['schedule'] as const;

export function workroomPrimaryTab(section?: string | null): (typeof WORKROOM_PRIMARY_TABS)[number]['id'] {
  if (!section) return 'jobs';
  if ((WORKROOM_MONEY_SECTIONS as readonly string[]).includes(section)) return 'jobs';
  if ((WORKROOM_TODAY_SECTIONS as readonly string[]).includes(section)) return 'jobs';
  for (const tab of WORKROOM_PRIMARY_TABS) {
    if ((tab.sections as readonly string[]).includes(section) || tab.id === section) return tab.id;
  }
  return 'jobs';
}

export function navHref(item: { id: string; kind?: string; screen?: string }): string {
  const mapped = moduleById(item.id);
  if (mapped) return mapped.path;
  if (item.kind === 'daily-summary') return '/?tab=today';
  if (item.kind === 'screen' && item.screen) return `/?screen=${encodeURIComponent(item.screen)}`;
  return `/?product=${encodeURIComponent(item.id)}`;
}
