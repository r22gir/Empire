'use client';
import { ScreenMode } from '../../lib/types';
import { MessageSquare, BarChart3, Bot, Inbox, FolderOpen, Search, Mic, Settings } from 'lucide-react';

const ITEMS: { id: ScreenMode | string; icon: any; label: string; badge?: boolean }[] = [
  { id: 'chat', icon: MessageSquare, label: 'Chat' },
  { id: 'dashboard', icon: BarChart3, label: 'Dash' },
  { id: 'desks', icon: Bot, label: 'Desks', badge: true },
  { id: 'inbox', icon: Inbox, label: 'Inbox' },
  { id: '_divider', icon: null, label: '' },
  { id: 'docs', icon: FolderOpen, label: 'Files' },
  { id: 'research', icon: Search, label: 'Search' },
  { id: '_spacer', icon: null, label: '' },
  { id: 'voice', icon: Mic, label: 'Voice' },
  { id: 'settings', icon: Settings, label: 'Settings' },
];

interface Props {
  activeScreen: ScreenMode;
  onScreenChange: (screen: ScreenMode) => void;
}

export default function GlobalSidebar({ activeScreen, onScreenChange }: Props) {
  return (
    <aside className="w-[68px] bg-white border-r border-[#e5e0d8] flex flex-col items-center py-2 gap-1 shrink-0">
      {ITEMS.map((item, i) => {
        if (item.id === '_divider') return <div key={i} className="w-7 h-px bg-[#e5e0d8] my-[5px]" />;
        if (item.id === '_spacer') return <div key={i} className="flex-1" />;
        const Icon = item.icon;
        const isActive = activeScreen === item.id;
        return (
          <button key={item.id} onClick={() => onScreenChange(item.id as ScreenMode)}
            className={`w-[52px] h-[52px] rounded-[12px] flex flex-col items-center justify-center gap-[2px] cursor-pointer border transition-all relative
              ${isActive ? 'bg-[#fdf8eb] border-[#d4b84a] text-[#96750a] shadow-[0_1px_4px_rgba(184,150,12,0.15)]' : 'bg-white border-[#e5e0d8] text-[#555] hover:bg-[#f0ede8] hover:text-[#1a1a1a] hover:border-[#ccc]'}`}>
            <Icon size={20} strokeWidth={2.2} />
            <span className="text-[8px] font-bold">{item.label}</span>
            {item.badge && <span className="absolute top-[5px] right-[5px] w-[7px] h-[7px] rounded-full bg-red-600" />}
          </button>
        );
      })}
    </aside>
  );
}
