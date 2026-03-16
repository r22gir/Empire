'use client';
import { useState, useEffect, useRef } from 'react';
import { Search, MessageSquare, BarChart3, ClipboardList, FolderOpen, Globe, Video, Scissors, Hammer, Server, MessageCircle, ListTodo, Monitor } from 'lucide-react';

const SECTIONS = [
  { label: 'Chat', shortcut: 'C', screen: 'chat', icon: MessageSquare, color: '#b8960c' },
  { label: 'MAX Avatar', shortcut: 'M', screen: 'presentation', icon: Monitor, color: '#b8960c' },
  { label: 'Dashboard', shortcut: 'D', screen: 'dashboard', icon: BarChart3, color: '#b8960c' },
  { label: 'Tasks', shortcut: 'K', screen: 'tasks', icon: ListTodo, color: '#d97706' },
  { label: 'Quote Review', shortcut: 'Q', screen: 'quote', icon: ClipboardList, color: '#d97706' },
  { label: 'Documents', shortcut: 'F', screen: 'docs', icon: FolderOpen, color: '#7c3aed' },
  { label: 'Research', shortcut: 'R', screen: 'research', icon: Globe, color: '#2563eb' },
  { label: 'Video Call', shortcut: 'V', screen: 'video', icon: Video, color: '#16a34a' },
  { label: 'Workroom', shortcut: 'W', screen: 'workroom-page', icon: Scissors, color: '#16a34a' },
  { label: 'WoodCraft', shortcut: 'G', screen: 'craft-page', icon: Hammer, color: '#ca8a04' },
  { label: 'Platform', shortcut: 'P', screen: 'platform-page', icon: Server, color: '#2563eb' },
  { label: 'Telegram', shortcut: 'T', screen: 'telegram', icon: MessageCircle, color: '#2563eb' },
];

interface Props {
  open: boolean;
  onClose: () => void;
  onSelect: (screen: string) => void;
}

export default function QuickSwitch({ open, onClose, onSelect }: Props) {
  const [query, setQuery] = useState('');
  const [focusIdx, setFocusIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) { setQuery(''); setFocusIdx(0); setTimeout(() => inputRef.current?.focus(), 50); }
  }, [open]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); onClose(); }
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  if (!open) return null;

  const filtered = SECTIONS.filter(s => s.label.toLowerCase().includes(query.toLowerCase()));

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setFocusIdx(i => Math.min(i + 1, filtered.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setFocusIdx(i => Math.max(i - 1, 0)); }
    else if (e.key === 'Enter' && filtered[focusIdx]) { onSelect(filtered[focusIdx].screen); onClose(); }
  };

  return (
    <div className="fixed inset-0 z-[300] flex items-start justify-center pt-[15vh]" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" />
      <div onClick={e => e.stopPropagation()}
        className="relative w-[520px] bg-white rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.25)] border border-[#e5e0d8] overflow-hidden">
        <div className="flex items-center gap-3 px-5 border-b border-[#ece8e1]">
          <Search size={18} className="text-[#b8960c]" />
          <input ref={inputRef} value={query} onChange={e => { setQuery(e.target.value); setFocusIdx(0); }}
            onKeyDown={handleKeyDown}
            className="flex-1 py-4 text-[15px] bg-transparent outline-none placeholder:text-[#bbb] text-[#1a1a1a] font-medium"
            placeholder="Jump to section..." />
          <span className="text-[10px] font-mono text-[#999] bg-[#f0ede8] px-2.5 py-1 rounded-md border border-[#e5e0d8]">ESC</span>
        </div>
        <div className="max-h-[360px] overflow-y-auto py-2">
          {filtered.map((s, i) => {
            const Icon = s.icon;
            return (
              <button key={s.screen} onClick={() => { onSelect(s.screen); onClose(); }}
                className={`w-full text-left px-5 py-3 flex items-center gap-3 transition-colors
                  ${i === focusIdx ? 'bg-[#fdf8eb]' : 'hover:bg-[#f5f3ef]'}`}>
                <Icon size={18} style={{ color: s.color }} />
                <span className="text-[14px] font-semibold text-[#1a1a1a] flex-1">{s.label}</span>
                <span className="text-[11px] font-mono text-[#aaa] bg-[#f5f3ef] px-2.5 py-1 rounded-md border border-[#ece8e1] min-w-[28px] text-center">{s.shortcut}</span>
              </button>
            );
          })}
          {filtered.length === 0 && (
            <div className="text-center text-sm text-[#aaa] py-8">No results for &quot;{query}&quot;</div>
          )}
        </div>
        <div className="border-t border-[#ece8e1] px-5 py-2 flex items-center gap-4 text-[10px] text-[#bbb]">
          <span>↑↓ Navigate</span>
          <span>↵ Select</span>
          <span>ESC Close</span>
        </div>
      </div>
    </div>
  );
}
