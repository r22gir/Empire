'use client';
import { useState } from 'react';
import { ServiceHealth, SystemStats, AIModel, BrainStatus, TokenStats, AIDeskStatus } from '@/lib/types';
import { Activity, Coins, BrainCircuit, Server, Layers, PenTool, Users, ChevronRight, X, BarChart3 } from 'lucide-react';
import SystemStatusPanel from './SystemStatusPanel';
import TokenCostPanel from './TokenCostPanel';
import OllamaBrainPanel from './OllamaBrainPanel';
import AIDeskGrid from './AIDeskGrid';
import EmpireBoxPanel from './EmpireBoxPanel';
import ForgePanel from './ForgePanel';
import CrmPanel from './CrmPanel';

interface Props {
  systemStats: SystemStats | null;
  serviceHealth: ServiceHealth;
  backendOnline: boolean;
  models: AIModel[];
  brainStatus: BrainStatus | null;
  tokenStats: TokenStats | null;
  aiDeskStatuses: AIDeskStatus[];
  visible?: boolean;
  onClose?: () => void;
}

type PanelId = 'system' | 'tokens' | 'desks' | 'brain' | 'services' | 'forge' | 'crm';

const PANEL_ITEMS: { id: PanelId; label: string; icon: typeof Activity; color: string }[] = [
  { id: 'system',   label: 'System',   icon: Activity,     color: 'var(--cyan)' },
  { id: 'tokens',   label: 'Tokens',   icon: Coins,        color: 'var(--gold)' },
  { id: 'desks',    label: 'AI Desks', icon: Layers,       color: 'var(--purple)' },
  { id: 'brain',    label: 'Brain',    icon: BrainCircuit,  color: '#22c55e' },
  { id: 'services', label: 'Services', icon: Server,        color: '#f59e0b' },
  { id: 'forge',    label: 'Forge',    icon: PenTool,       color: '#ec4899' },
  { id: 'crm',      label: 'CRM',     icon: Users,         color: '#06b6d4' },
];

export default function RightColumn({
  systemStats, serviceHealth, backendOnline, models, brainStatus, tokenStats, aiDeskStatuses,
  visible = true, onClose,
}: Props) {
  const [activePanel, setActivePanel] = useState<PanelId | null>(null);

  if (!visible) return null;

  const togglePanel = (id: PanelId) => {
    setActivePanel(prev => prev === id ? null : id);
  };

  /* Quick status summary for the stat bar */
  const cpuPct = systemStats?.cpu?.percent ?? 0;
  const ramPct = systemStats?.memory?.percent ?? 0;

  return (
    <div className="absolute right-0 top-0 bottom-0 z-20 flex items-start" style={{ pointerEvents: 'none' }}>
      {/* Floating stat pills — always visible */}
      <div className="flex flex-col items-end gap-2 p-3" style={{ pointerEvents: 'auto' }}>
        {/* Quick system summary pill */}
        <div
          className="stat-pill cursor-pointer"
          onClick={() => togglePanel('system')}
          style={{
            borderColor: activePanel === 'system' ? 'var(--cyan-border)' : undefined,
            background: activePanel === 'system' ? 'var(--cyan-pale)' : undefined,
          }}
          onMouseEnter={e => { if (activePanel !== 'system') e.currentTarget.style.borderColor = 'var(--cyan-border)'; }}
          onMouseLeave={e => { if (activePanel !== 'system') e.currentTarget.style.borderColor = 'var(--glass-border)'; }}
        >
          <div className="w-2 h-2 rounded-full" style={{ background: cpuPct > 80 ? '#ef4444' : cpuPct > 50 ? '#f59e0b' : '#22c55e' }} />
          <span style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>
            CPU {cpuPct}% | RAM {ramPct}%
          </span>
        </div>

        {/* Panel trigger pills */}
        {PANEL_ITEMS.map(item => (
          <button
            key={item.id}
            onClick={() => togglePanel(item.id)}
            className="stat-pill transition-all"
            style={{
              borderColor: activePanel === item.id ? item.color : undefined,
              background: activePanel === item.id ? `${item.color}11` : undefined,
              pointerEvents: 'auto',
              cursor: 'pointer',
            }}
            onMouseEnter={e => { if (activePanel !== item.id) { e.currentTarget.style.borderColor = item.color; e.currentTarget.style.transform = 'translateX(-2px)'; } }}
            onMouseLeave={e => { if (activePanel !== item.id) { e.currentTarget.style.borderColor = 'var(--glass-border)'; e.currentTarget.style.transform = 'none'; } }}
          >
            <item.icon className="w-3 h-3" style={{ color: item.color }} />
            <span style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>{item.label}</span>
            <ChevronRight className="w-2.5 h-2.5 transition-transform" style={{ color: 'var(--text-muted)', transform: activePanel === item.id ? 'rotate(180deg)' : undefined }} />
          </button>
        ))}
      </div>

      {/* Expanded floating card */}
      {activePanel && (
        <div
          className="floating-stat-card float-card-enter mt-3 mr-2"
          style={{ pointerEvents: 'auto', position: 'relative', right: 0, width: '300px' }}
        >
          {/* Card header */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              {(() => {
                const item = PANEL_ITEMS.find(p => p.id === activePanel);
                if (!item) return null;
                return (
                  <>
                    <item.icon className="w-4 h-4" style={{ color: item.color }} />
                    <span className="text-xs font-semibold" style={{ color: item.color }}>{item.label}</span>
                  </>
                );
              })()}
            </div>
            <button
              onClick={() => setActivePanel(null)}
              className="w-6 h-6 rounded-lg flex items-center justify-center transition"
              style={{ color: 'var(--text-muted)' }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Panel content */}
          <div className="max-h-[60vh] overflow-y-auto">
            {activePanel === 'system' && (
              <SystemStatusPanel systemStats={systemStats} serviceHealth={serviceHealth} backendOnline={backendOnline} />
            )}
            {activePanel === 'tokens' && (
              <TokenCostPanel tokenStats={tokenStats} backendOnline={backendOnline} />
            )}
            {activePanel === 'desks' && (
              <AIDeskGrid aiDeskStatuses={aiDeskStatuses} backendOnline={backendOnline} />
            )}
            {activePanel === 'brain' && (
              <OllamaBrainPanel brainStatus={brainStatus} backendOnline={backendOnline} />
            )}
            {activePanel === 'services' && (
              <EmpireBoxPanel serviceHealth={serviceHealth} backendOnline={backendOnline} models={models} brainStatus={brainStatus} />
            )}
            {activePanel === 'forge' && <ForgePanel serviceHealth={serviceHealth} />}
            {activePanel === 'crm' && <CrmPanel />}
          </div>
        </div>
      )}
    </div>
  );
}
