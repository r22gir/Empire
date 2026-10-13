/** Canonical AI desk count — mirrors backend/app/services/max/desks/desk_registry.py */
export const CANONICAL_DESK_COUNT = 17;

export const REGISTERED_DESKS = [
  { id: 'forge', name: 'ForgeDesk', agent: 'Kai' },
  { id: 'market', name: 'MarketDesk', agent: 'Sofia' },
  { id: 'marketing', name: 'MarketingDesk', agent: 'Nova' },
  { id: 'sales', name: 'SalesDesk', agent: 'Aria' },
  { id: 'support', name: 'SupportDesk', agent: 'Luna' },
  { id: 'finance', name: 'FinanceDesk', agent: 'Sage' },
  { id: 'clients', name: 'ClientsDesk', agent: 'Elena' },
  { id: 'contractors', name: 'ContractorsDesk', agent: 'Marcus' },
  { id: 'it', name: 'ITDesk', agent: 'Orion' },
  { id: 'website', name: 'WebsiteDesk', agent: 'Zara' },
  { id: 'legal', name: 'LegalDesk', agent: 'Raven' },
  { id: 'lab', name: 'LabDesk', agent: 'Phoenix' },
  { id: 'innovation', name: 'InnovationDesk', agent: 'Spark' },
  { id: 'intake', name: 'IntakeDesk', agent: 'Zara' },
  { id: 'analytics', name: 'AnalyticsDesk', agent: 'Raven' },
  { id: 'quality', name: 'QualityDesk', agent: 'Phoenix' },
  { id: 'codeforge', name: 'CodeForgeDesk', agent: 'Atlas' },
] as const;

export function deskCountLabel(count: number = CANONICAL_DESK_COUNT): string {
  return `${count} desks`;
}
