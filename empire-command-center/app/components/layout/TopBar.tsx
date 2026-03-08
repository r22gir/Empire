'use client';
import { useState, useRef, useEffect } from 'react';
import { BusinessTab } from '../../lib/types';
import { MessageSquare, Video, Bell, Command, Eye, Globe } from 'lucide-react';

const TABS: { id: BusinessTab; label: string; dot: string; onClass: string }[] = [
  { id: 'max', label: 'MAX', dot: '#D4AF37', onClass: 'text-[#D4AF37] bg-[#2a2510]' },
  { id: 'workroom', label: 'Workroom', dot: '#22C55E', onClass: 'text-[#22C55E] bg-[#0d2a10]' },
  { id: 'craft', label: 'CraftForge', dot: '#EAB308', onClass: 'text-[#EAB308] bg-[#2a2510]' },
  { id: 'platform', label: 'Platform', dot: '#3B82F6', onClass: 'text-[#3B82F6] bg-[#0d1a2a]' },
];

interface Props {
  activeTab: BusinessTab;
  onTabChange: (tab: BusinessTab) => void;
  onVideoCall: () => void;
  onQuickSwitch: () => void;
  onClientView: () => void;
  services?: any;
}

export default function TopBar({ activeTab, onTabChange, onVideoCall, onQuickSwitch, onClientView, services }: Props) {
  const [showNotifs, setShowNotifs] = useState(false);
  const [lang, setLang] = useState('EN');
  const notifRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setShowNotifs(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <header className="h-12 bg-[#1a1a1a] flex items-center px-3 gap-1 shrink-0 z-50">
      <span className="font-bold text-sm text-[#D4AF37] tracking-[2px] mr-3.5 pr-3.5 border-r border-[#333]">EMPIRE</span>
      {TABS.map(t => (
        <button key={t.id} onClick={() => onTabChange(t.id)}
          className={`px-5 py-2.5 text-[13px] font-semibold border-none cursor-pointer rounded-t-lg min-h-[44px] flex items-center gap-2 transition-all
            ${activeTab === t.id ? `font-bold ${t.onClass} border-b-2` : 'text-[#777] bg-transparent hover:text-white hover:bg-[#333]'}`}
          style={activeTab === t.id ? { borderBottomColor: t.dot } : {}}>
          <span className="w-2 h-2 rounded-full" style={{ background: t.dot }} />
          {t.label}
        </button>
      ))}

      <div className="ml-auto flex items-center gap-1.5">
        <button onClick={onVideoCall} title="Video Call" className="tb-btn"><Video size={17} /></button>

        <div ref={notifRef} className="relative">
          <button onClick={() => setShowNotifs(!showNotifs)} className="tb-btn">
            <Bell size={17} />
            <span className="absolute -top-[3px] -right-[3px] bg-red-600 text-white text-[8px] font-bold min-w-[16px] h-4 rounded-full flex items-center justify-center">6</span>
          </button>
          {showNotifs && (
            <div className="absolute top-[46px] right-0 w-[340px] bg-white border border-[#e5e0d8] rounded-xl shadow-[0_8px_30px_rgba(0,0,0,0.12)] z-[200] overflow-hidden">
              <div className="p-3 border-b border-[#ece8e1] text-[13px] font-semibold text-[#1a1a1a]">Notifications</div>
              <div className="p-2">
                <div className="text-[9px] font-bold text-[#22C55E] tracking-[0.5px] px-2 py-1.5">EMPIRE WORKROOM — 3 NEW</div>
                <NotifItem title="Quote Review" body="Maria new request" time="10m" />
                <NotifItem title="Shipping" body="Emily valance picked up" time="1h" />
                <NotifItem title="Desk: Aria" body="IG post drafted" time="2h" />
                <div className="text-[9px] font-bold text-[#EAB308] tracking-[0.5px] px-2 py-1.5 mt-1">CRAFTFORGE — 1 NEW</div>
                <NotifItem title="Desk: Vanguard" body="Roadmap draft ready" time="3h" />
                <div className="text-[9px] font-bold text-[#7c3aed] tracking-[0.5px] px-2 py-1.5 mt-1">PERSONAL — 2 NEW</div>
                <NotifItem title="System" body="DDG search rate-limited" time="4h" />
                <NotifItem title="Memory" body="Context-pack updated" time="6h" />
              </div>
            </div>
          )}
        </div>

        <button onClick={onQuickSwitch} title="Ctrl+K" className="tb-btn"><Command size={17} /></button>
        <button onClick={() => setLang(l => l === 'EN' ? 'ES' : 'EN')}
          className="text-[11px] font-bold font-mono px-2.5 py-1.5 rounded-md border border-[#444] bg-[#222] text-[#999] cursor-pointer min-h-[38px] hover:text-white">
          {lang}
        </button>
        <button onClick={onClientView} title="Client View" className="tb-btn"><Eye size={17} /></button>

        <div className="flex gap-1.5 pl-2 border-l border-[#333] ml-1">
          <StatusDot label="Grok" ok />
          <StatusDot label="TG" ok />
          <StatusDot label="DDG" warn />
        </div>
      </div>
    </header>
  );
}

function NotifItem({ title, body, time }: { title: string; body: string; time: string }) {
  return (
    <div className="px-2.5 py-2 rounded-[7px] cursor-pointer text-xs mb-0.5 hover:bg-[#f0ede8] transition-colors text-[#1a1a1a]">
      <strong>{title}</strong> — {body}
      <span className="text-[9px] text-[#aaa] float-right font-mono">{time}</span>
    </div>
  );
}

function StatusDot({ label, ok, warn }: { label: string; ok?: boolean; warn?: boolean }) {
  const color = ok ? '#22C55E' : warn ? '#EAB308' : '#dc2626';
  return (
    <span className="flex items-center gap-[3px] text-[9px] font-mono" style={{ color }}>
      <span className="w-[5px] h-[5px] rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}
