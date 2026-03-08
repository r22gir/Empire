'use client';
import { useState } from 'react';
import { BusinessTab, Conversation } from '../../lib/types';
import { Plus } from 'lucide-react';

const TAB_CONFIG: Record<BusinessTab, { label: string; color: string }> = {
  max: { label: 'ALL (God View)', color: '#D4AF37' },
  workroom: { label: 'WORKROOM ONLY', color: '#22C55E' },
  craft: { label: 'CRAFTFORGE ONLY', color: '#EAB308' },
  platform: { label: 'PLATFORM ONLY', color: '#3B82F6' },
};

const GROUP_CONFIG: Record<string, { label: string; icon: string; color: string }> = {
  personal: { label: 'PERSONAL', icon: '🤖', color: '#7c3aed' },
  workroom: { label: 'EMPIRE WORKROOM', icon: '🏗️', color: '#22C55E' },
  craft: { label: 'CRAFTFORGE', icon: '🪵', color: '#EAB308' },
  platform: { label: 'PLATFORM', icon: '🌐', color: '#3B82F6' },
};

interface Props {
  activeTab: BusinessTab;
  conversations: Conversation[];
  activeConvId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}

export default function ConversationSidebar({ activeTab, conversations, activeConvId, onSelect, onNew }: Props) {
  const [search, setSearch] = useState('');
  const config = TAB_CONFIG[activeTab];

  // Group conversations
  const filtered = conversations.filter(c =>
    !search || c.title.toLowerCase().includes(search.toLowerCase())
  );

  // For MAX tab, group by business; for others, show flat list
  const groups: { key: string; items: Conversation[] }[] = [];
  if (activeTab === 'max') {
    const buckets: Record<string, Conversation[]> = { personal: [], workroom: [], craft: [], platform: [] };
    for (const c of filtered) {
      const biz = c.business || 'personal';
      (buckets[biz] || buckets.personal).push(c);
    }
    for (const key of ['personal', 'workroom', 'craft', 'platform']) {
      if (buckets[key].length) groups.push({ key, items: buckets[key] });
    }
  } else {
    groups.push({ key: activeTab, items: filtered });
  }

  return (
    <aside className="w-60 bg-white border-r border-[#e5e0d8] flex flex-col shrink-0">
      <div className="px-3 py-2.5 border-b border-[#ece8e1] flex items-center justify-between">
        <h3 className="text-xs font-semibold text-[#1a1a1a]">
          History · <span className="text-[10px]" style={{ color: config.color }}>{config.label}</span>
        </h3>
        <button onClick={onNew} className="bg-[#b8960c] text-white border-none px-3.5 py-2 rounded-lg text-[12px] font-bold cursor-pointer min-h-[38px] hover:bg-[#a08509] flex items-center gap-1.5 shadow-[0_2px_6px_rgba(184,150,12,0.25)] transition-all active:scale-95">
          <Plus size={14} strokeWidth={2.5} /> New
        </button>
      </div>
      <input value={search} onChange={e => setSearch(e.target.value)}
        className="mx-2.5 my-2 px-3 py-2.5 border border-[#d8d3cb] rounded-lg text-xs bg-white outline-none min-h-[40px] focus:border-[#b8960c] focus:shadow-[0_0_0_3px_#f5ecd0] placeholder:text-[#bbb]"
        placeholder="Search conversations..." />
      <div className="flex-1 overflow-y-auto px-1.5 py-[3px]">
        {groups.map(g => {
          const gc = GROUP_CONFIG[g.key];
          return (
            <div key={g.key}>
              {activeTab === 'max' && gc && (
                <div className="text-[9px] font-bold tracking-[0.5px] px-2.5 py-1.5 mt-2" style={{ color: gc.color }}>
                  {gc.icon} {gc.label}
                </div>
              )}
              {g.items.map(c => (
                <div key={c.id} onClick={() => onSelect(c.id)}
                  className={`px-3 py-3 rounded-lg cursor-pointer mb-0.5 min-h-[56px] transition-all border
                    ${activeConvId === c.id ? 'bg-[#fdf8eb] border-[#e8d89c]' : 'border-transparent hover:bg-[#f0ede8] hover:border-[#e5e0d8]'}`}>
                  <div className="text-[12px] font-semibold text-[#1a1a1a] truncate">{c.title}</div>
                  <div className="text-[10px] text-[#888] mt-0.5 truncate">{c.preview}</div>
                  <div className="text-[9px] text-[#bbb] mt-0.5 font-mono">{formatTime(c.timestamp)}</div>
                </div>
              ))}
            </div>
          );
        })}
        {groups.length === 0 && (
          <div className="text-center text-xs text-[#aaa] py-8">No conversations yet</div>
        )}
      </div>
    </aside>
  );
}

function formatTime(ts: string): string {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    const now = new Date();
    if (d.toDateString() === now.toDateString()) {
      return 'Today ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  } catch { return ts; }
}
