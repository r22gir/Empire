// Edition profile for the v3 shell and Max home. The main studio is Rafael's Empire.
// Family editions (Max-e / AMP, Maxine) override this in their own checkouts and only
// ever read their own backend, so nothing here leaks across editions.
export type RailKey = 'max' | 'workroom' | 'craft' | 'construction' | 'amp' | 'lead' | 'social' | 'market' | 'finance' | 'comms' | 'docs' | 'system';

export interface RailItem { key: RailKey; label: string; product?: string; screen?: string; href: string; hint: string }

export interface EditionProfile {
  id: string;
  ownerName: string;
  ownerInitials: string;
  assistantName: string;
  homeUser: string; // key for /home-center lists
  rail: RailItem[];
  /** neutral starter topics the user can add with one tap (nothing is pre-filled) */
  interestSuggestions: { name: string; icon: string }[];
  goalSuggestions: string[];
  askChips: string[];
}

const item = (key: RailKey, label: string, target: { product?: string; screen?: string; href?: string }, hint: string): RailItem => ({
  key, label, ...target,
  href: target.href || (target.product ? `/?product=${target.product}` : target.screen ? `/?screen=${target.screen}` : '/'),
  hint,
});

export const EDITION: EditionProfile = {
  id: 'empire',
  ownerName: 'Rafael',
  ownerInitials: 'RG',
  assistantName: 'Max',
  homeUser: 'owner',
  rail: [
    item('workroom', 'Workroom', { product: 'workroom' }, 'Drapery & upholstery: jobs, quotes, invoices'),
    item('craft', 'WoodCraft', { product: 'craft' }, 'CNC and woodwork jobs'),
    item('construction', 'Construct.', { product: 'construction' }, 'ConstructionForge projects and lots'),
    item('amp', 'Max-e', { product: 'amp' }, 'AMP coaching edition'),
    item('lead', 'LeadForge', { product: 'lead' }, 'Prospects, pipeline, approvals'),
    item('social', 'Social', { product: 'social' }, 'SocialForge posts and DMs'),
    item('market', 'Market', { product: 'market' }, 'MarketForge listings'),
    item('finance', 'Finance', { screen: 'invoices' }, 'Invoices, payments, overdue'),
    item('comms', 'Comms', { screen: 'inbox' }, 'Inbox and messages'),
    item('docs', 'Docs', { screen: 'final-docs' }, 'Final estimates, invoices, drawings'),
  ],
  interestSuggestions: [
    { name: 'AI & Tech', icon: 'cpu' }, { name: 'Markets', icon: 'trend' }, { name: 'Making & CNC', icon: 'tool' },
    { name: 'Real Estate', icon: 'home' }, { name: 'Health', icon: 'heart' }, { name: 'Design', icon: 'layers' },
  ],
  goalSuggestions: ['Read 12 books', 'Finish a certification', 'Ship a personal project'],
  askChips: ['Brief me on today', 'What needs my approval?', 'Research a topic for me'],
};

export const SYSTEM_ITEM: RailItem = item('system', 'System', { product: 'system' }, 'Services, health, improvements');
