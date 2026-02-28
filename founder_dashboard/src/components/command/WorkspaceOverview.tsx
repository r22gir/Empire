'use client';
import { ArrowRight } from 'lucide-react';

export interface EmpireApp {
  id: string;
  name: string;
  icon: string;
  description: string;
  color: string;          // accent color
  ready: boolean;         // fully built vs coming soon
  features?: string[];    // planned features for placeholder
}

export const EMPIRE_APPS: EmpireApp[] = [
  {
    id: 'workroomforge',
    name: 'WorkroomForge',
    icon: '🪡',
    description: 'Custom drapery workroom — quotes, customers, scheduling, materials',
    color: '#D4AF37',
    ready: true,
  },
  {
    id: 'marketforge',
    name: 'MarketForge',
    icon: '🛒',
    description: 'Multi-platform marketplace — listings, orders, inventory sync',
    color: '#22c55e',
    ready: false,
    features: ['Listing management', 'Price optimization', 'Inventory sync', 'Order processing', 'Amazon/eBay integration'],
  },
  {
    id: 'amp',
    name: 'AMP',
    icon: '📢',
    description: 'Apostol Marketing Platform — campaigns, clients, content creation',
    color: '#8B5CF6',
    ready: false,
    features: ['Campaign management', 'Client reporting', 'Content creation', 'Analytics dashboard', 'Ad spend tracking'],
  },
  {
    id: 'socialforge',
    name: 'SocialForge',
    icon: '🌐',
    description: 'Social media command center — scheduling, engagement, analytics',
    color: '#22D3EE',
    ready: false,
    features: ['Content scheduling', 'Hashtag research', 'Engagement tracking', 'Cross-platform analytics', 'Auto-responses'],
  },
  {
    id: 'luxeforge',
    name: 'LuxeForge',
    icon: '💎',
    description: 'Premium designer portal — high-end client projects',
    color: '#D946EF',
    ready: false,
    features: ['Designer dashboard', 'Client portal', 'Project gallery', 'Proposal templates', 'Premium CRM'],
  },
  {
    id: 'recoveryforge',
    name: 'RecoveryForge',
    icon: '🔄',
    description: 'Business recovery and continuity management',
    color: '#f59e0b',
    ready: false,
    features: ['Recovery workflows', 'Risk assessment', 'Backup monitoring', 'Incident response', 'Business continuity'],
  },
  {
    id: 'crm',
    name: 'CRM',
    icon: '👥',
    description: 'Customer relationship management across all forges',
    color: '#3b82f6',
    ready: false,
    features: ['Contact management', 'Deal tracking', 'Communication history', 'Customer segments', 'Lead scoring'],
  },
];

interface Props {
  onOpenWorkspace: (appId: string) => void;
}

export default function WorkspaceOverview({ onOpenWorkspace }: Props) {
  return (
    <div className="flex-1 overflow-y-auto p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold" style={{ color: 'var(--gold)' }}>Empire Workspaces</h2>
          <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Select a workspace to open its full dashboard</p>
        </div>

        {/* App grid */}
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {EMPIRE_APPS.map(app => (
            <button
              key={app.id}
              onClick={() => onOpenWorkspace(app.id)}
              className="group relative text-left rounded-xl p-4 transition-all"
              style={{
                background: 'var(--surface)',
                border: `1px solid var(--border)`,
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = app.color;
                e.currentTarget.style.boxShadow = `0 0 20px ${app.color}15`;
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'var(--border)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              {/* Coming Soon badge */}
              {!app.ready && (
                <span
                  className="absolute top-2 right-2 px-1.5 py-0.5 rounded text-[8px] font-bold uppercase"
                  style={{ background: `${app.color}20`, color: app.color, border: `1px solid ${app.color}40` }}
                >
                  Coming Soon
                </span>
              )}

              <div className="flex items-start gap-3">
                <span className="text-2xl">{app.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{app.name}</h3>
                    {app.ready && <span className="dot-online" />}
                  </div>
                  <p className="text-[11px] mt-1 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                    {app.description}
                  </p>
                </div>
              </div>

              {/* Open arrow */}
              <div
                className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ color: app.color }}
              >
                <ArrowRight className="w-4 h-4" />
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
