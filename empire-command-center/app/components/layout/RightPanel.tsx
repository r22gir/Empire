'use client';
import { useState } from 'react';
import { RightTab, Desk } from '../../lib/types';
import { Cpu, HardDrive, Database, Clock, PanelRightClose, PanelRight } from 'lucide-react';

const TABS: { id: RightTab; label: string; badge?: string }[] = [
  { id: 'desks', label: 'Desks' },
  { id: 'inbox', label: 'Inbox', badge: '5' },
  { id: 'system', label: 'System' },
  { id: 'memory', label: 'Memory' },
];

interface Props {
  desks: Desk[];
  briefing: string;
  systemStats?: any;
  collapsed?: boolean;
  onToggle?: () => void;
}

export default function RightPanel({ desks, briefing, systemStats, collapsed, onToggle }: Props) {
  const [activeTab, setActiveTab] = useState<RightTab>('desks');
  const [showAll, setShowAll] = useState(false);

  const displayDesks = showAll ? desks : desks.slice(0, 6);

  if (collapsed) {
    return (
      <aside className="w-[24px] bg-white border-l border-[#e5e0d8] flex items-start justify-center pt-2 shrink-0 cursor-pointer hover:bg-[#f5f3ef] transition-colors"
        onClick={onToggle}>
        <PanelRight size={14} className="text-[#aaa]" />
      </aside>
    );
  }

  return (
    <aside className="w-[300px] bg-white border-l border-[#e5e0d8] flex flex-col shrink-0">
      <div className="flex border-b border-[#ece8e1] px-1">
        <button onClick={onToggle} className="px-1.5 py-2.5 text-[#ccc] hover:text-[#888] cursor-pointer" title="Collapse">
          <PanelRightClose size={14} />
        </button>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className={`px-3 py-2.5 text-[12px] font-semibold cursor-pointer border-b-2 bg-transparent min-h-[42px] flex items-center gap-1 transition-colors
              ${activeTab === t.id ? 'text-[#b8960c] border-[#b8960c]' : 'text-[#888] border-transparent hover:text-[#1a1a1a]'}`}>
            {t.label}
            {t.badge && <span className="text-[9px] font-bold text-white bg-red-500 rounded-full w-4 h-4 flex items-center justify-center">{t.badge}</span>}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {activeTab === 'desks' && (
          <>
            {briefing && (
              <div className="bg-[#fdf8eb] border border-[#e8d89c] rounded-xl p-3.5 mb-3">
                <h4 className="text-xs font-bold text-[#b8960c] mb-1.5">Morning Briefing</h4>
                <p className="text-[11px] text-[#555] leading-relaxed">{briefing}</p>
              </div>
            )}
            <div className="grid grid-cols-2 gap-2">
              {displayDesks.map(d => (
                <div key={d.id} className="p-3 rounded-xl border border-[#ece8e1] cursor-pointer bg-white min-h-[72px] transition-all hover:border-[#7c3aed] hover:shadow-[0_2px_8px_rgba(124,58,237,0.1)]">
                  <div className="flex items-center gap-1.5">
                    <span className="text-lg">{d.icon || '🤖'}</span>
                    <span className="text-[11px] font-bold text-[#1a1a1a]">{d.name}</span>
                  </div>
                  <div className="text-[9px] text-[#7c3aed] font-medium italic mt-0.5">{d.persona}</div>
                  <div className="text-[9px] text-[#999] mt-1 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#16a34a]" />
                    {d.status || 'Ready'}
                  </div>
                </div>
              ))}
            </div>
            {desks.length > 6 && (
              <button onClick={() => setShowAll(!showAll)}
                className="w-full text-center py-2.5 text-[11px] text-[#7c3aed] font-bold cursor-pointer rounded-lg min-h-[38px] hover:bg-[#ede9fe] mt-2 border border-transparent hover:border-[#c4b5fd] transition-all">
                {showAll ? '▲ Show less' : `▼ Show ${desks.length - 6} more desks`}
              </button>
            )}
            {desks.length === 0 && (
              <div className="text-center text-xs text-[#aaa] py-8">No AI desks loaded</div>
            )}
          </>
        )}

        {activeTab === 'inbox' && (
          <div className="space-y-2">
            <InboxItem type="quote" title="Maria — New Quote Request" time="10m ago" color="#b8960c" />
            <InboxItem type="shipping" title="Emily valance — Picked up" time="1h ago" color="#16a34a" />
            <InboxItem type="desk" title="Aria — IG post drafted" time="2h ago" color="#7c3aed" />
            <InboxItem type="system" title="DDG search rate-limited" time="4h ago" color="#d97706" />
            <InboxItem type="memory" title="Context-pack updated" time="6h ago" color="#2563eb" />
            <div className="text-center text-[10px] text-[#aaa] mt-4">Loads from /api/v1/inbox when available</div>
          </div>
        )}

        {activeTab === 'system' && (
          <div className="space-y-2.5">
            <SystemGauge icon={<Cpu size={16} />} label="CPU" value={systemStats?.cpu_percent || 0} unit="%" color="#2563eb" />
            <SystemGauge icon={<HardDrive size={16} />} label="RAM" value={systemStats?.memory?.percent || 0} unit="%" color="#7c3aed" />
            <SystemGauge icon={<Database size={16} />} label="Disk" value={systemStats?.disk?.percent || 0} unit="%" color="#b8960c" />
            <div className="flex items-center justify-between p-3 rounded-xl border border-[#ece8e1] bg-[#faf9f7]">
              <div className="flex items-center gap-2">
                <Clock size={16} className="text-[#16a34a]" />
                <span className="text-xs font-semibold text-[#555]">Uptime</span>
              </div>
              <span className="text-xs font-mono font-bold text-[#1a1a1a]">{systemStats?.uptime || '--'}</span>
            </div>
            <div className="p-3 rounded-xl bg-[#f0fdf4] border border-[#bbf7d0] mt-2">
              <div className="text-[10px] font-bold text-[#16a34a] mb-0.5">SERVER</div>
              <div className="text-[10px] text-[#555]">EmpireDell · Xeon E5-2650 v3 · 32GB RAM</div>
            </div>
          </div>
        )}

        {activeTab === 'memory' && (
          <div className="space-y-2.5">
            <MemoryCard label="Persistent Memory" value="~/Empire/max/memory.md" icon="🧠" />
            <MemoryCard label="Context Pack" value="Loaded at session start" icon="📦" />
            <MemoryCard label="Session Log" value="Today's interactions" icon="📝" />
            <div className="p-3 rounded-xl bg-[#ede9fe] border border-[#c4b5fd] mt-2">
              <div className="text-[10px] font-bold text-[#7c3aed] mb-0.5">MEMORY SYSTEM</div>
              <div className="text-[10px] text-[#555]">MAX retains context across sessions via persistent memory files and context packs.</div>
            </div>
            <div className="text-center text-[10px] text-[#aaa] mt-2">Full stats from /api/v1/memory/stats</div>
          </div>
        )}
      </div>
    </aside>
  );
}

function SystemGauge({ icon, label, value, unit, color }: { icon: React.ReactNode; label: string; value: number; unit: string; color: string }) {
  const barColor = value > 85 ? '#dc2626' : value > 60 ? '#d97706' : color;
  return (
    <div className="p-3 rounded-xl border border-[#ece8e1] bg-[#faf9f7]">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span style={{ color: barColor }}>{icon}</span>
          <span className="text-xs font-semibold text-[#555]">{label}</span>
        </div>
        <span className="text-sm font-mono font-bold" style={{ color: barColor }}>{value}{unit}</span>
      </div>
      <div className="w-full h-2 rounded-full bg-[#e5e0d8] overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${value}%`, background: barColor }} />
      </div>
    </div>
  );
}

function InboxItem({ type, title, time, color }: { type: string; title: string; time: string; color: string }) {
  const icons: Record<string, string> = { quote: '💰', shipping: '🚚', desk: '🤖', system: '⚙️', memory: '🧠' };
  return (
    <div className="p-3 rounded-xl border border-[#ece8e1] bg-white cursor-pointer hover:border-[#b8960c] hover:bg-[#fdf8eb] transition-all">
      <div className="flex items-start gap-2">
        <span className="text-sm mt-0.5">{icons[type] || '📌'}</span>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold text-[#1a1a1a] truncate">{title}</div>
          <div className="text-[9px] font-mono mt-0.5" style={{ color }}>{time}</div>
        </div>
      </div>
    </div>
  );
}

function MemoryCard({ label, value, icon }: { label: string; value: string; icon: string }) {
  return (
    <div className="p-3 rounded-xl border border-[#ece8e1] bg-[#faf9f7]">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-sm">{icon}</span>
        <span className="text-xs font-bold text-[#1a1a1a]">{label}</span>
      </div>
      <div className="text-[10px] text-[#777] font-mono">{value}</div>
    </div>
  );
}
