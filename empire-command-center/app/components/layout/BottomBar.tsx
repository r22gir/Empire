'use client';
import { useState, useEffect, useCallback } from 'react';
import { ExternalLink, ChevronUp, ChevronDown, Newspaper, Power } from 'lucide-react';
import { API } from '../../lib/api';

interface Props {
  services?: any;
}

const SERVICES = ['backend', 'db', 'grok', 'claude', 'ollama', 'tg'];

interface NewsItem {
  title: string;
  source: string;
  url: string;
  category: string;
}

export default function BottomBar({ services }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [ollamaStatus, setOllamaStatus] = useState<{ ollama: string; percentage: number } | null>(null);
  const [toggling, setToggling] = useState(false);

  // Poll Ollama status
  useEffect(() => {
    const check = () => {
      fetch(API + '/system/ollama/status')
        .then(r => r.ok ? r.json() : null)
        .then(data => { if (data) setOllamaStatus(data); })
        .catch(() => {});
    };
    check();
    const iv = setInterval(check, 30000);
    return () => clearInterval(iv);
  }, []);

  const toggleOllama = async () => {
    if (toggling) return;
    const isOn = ollamaStatus?.ollama === 'running';
    if (isOn && !confirm('Turning off Ollama will stop RecoveryForge classification. Continue?')) return;
    if (!isOn && !confirm('Turning on Ollama may slow down MAX responses. Continue?')) return;
    setToggling(true);
    try {
      const r = await fetch(API + '/system/ollama/toggle', { method: 'POST' });
      if (r.ok) {
        const data = await r.json();
        setOllamaStatus(prev => prev ? { ...prev, ollama: data.ollama } : null);
      }
    } catch (e) { console.error(e); }
    setToggling(false);
  };

  // Fetch notifications/news from backend or use defaults
  useEffect(() => {
    fetch(API + '/notifications/')
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.notifications?.length) {
          setNews(data.notifications.slice(0, 6).map((n: any) => ({
            title: n.title || n.message || 'Update',
            source: n.source || 'Empire',
            url: n.url || '#',
            category: n.category || 'system',
          })));
        }
      })
      .catch(() => {});
  }, []);

  const defaultNews: NewsItem[] = [
    { title: 'AI photo analysis now live in Workroom', source: 'Empire', url: '#', category: 'update' },
    { title: 'Telegram bot integration complete', source: 'Empire', url: '#', category: 'feature' },
    { title: 'New quote builder with vision AI', source: 'WorkroomForge', url: '#', category: 'feature' },
    { title: 'Token cost tracking dashboard available', source: 'Empire', url: '#', category: 'system' },
    { title: 'WoodCraft design pipeline active', source: 'WoodCraft', url: '#', category: 'update' },
    { title: 'Customer intake portal deployed', source: 'Empire', url: '#', category: 'feature' },
  ];

  const displayNews = news.length > 0 ? news : defaultNews;

  return (
    <div className="shrink-0">
      {/* Expanded news panel */}
      {expanded && (
        <div className="bg-[#1a1a1a] border-t border-[#333] px-5 py-3 max-h-[200px] overflow-y-auto">
          <div className="flex items-center gap-2 mb-2">
            <Newspaper size={14} className="text-[#22c55e]" />
            <span className="text-xs font-bold text-[#22c55e]">NEWS & UPDATES</span>
            <span className="text-[9px] text-[#555]">· Click headlines for details</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {displayNews.map((item, i) => (
              <a key={i} href={item.url !== '#' ? item.url : undefined} target={item.url !== '#' ? '_blank' : undefined}
                rel="noopener noreferrer"
                className="block p-2 rounded-lg bg-[#222] border border-[#333] hover:border-[#555] hover:bg-[#2a2a2a] transition-all cursor-pointer">
                <div className="text-[11px] text-[#ccc] font-medium leading-tight line-clamp-2">{item.title}</div>
                <div className="text-[9px] text-[#666] mt-1 flex items-center gap-1">
                  {item.source}
                  {item.url !== '#' && <ExternalLink size={8} />}
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Main bottom bar with ticker */}
      <footer className="h-[34px] bg-[#1a1a1a] border-t border-[#333] flex items-center px-5 gap-4 shrink-0">
        {/* Service status */}
        <div className="flex items-center gap-4">
          {SERVICES.map(s => {
            const isOk = services?.[s]?.status === 'online' || services?.[s] === true;
            return (
              <div key={s} className="flex items-center gap-[5px] text-[10px] text-[#888] font-mono whitespace-nowrap">
                <span className={`w-[5px] h-[5px] rounded-full ${isOk ? 'bg-[#22c55e]' : 'bg-[#f59e0b]'}`} />
                {s}
              </div>
            );
          })}
        </div>

        <div className="w-px h-4 bg-[#444] shrink-0" />

        {/* Scrolling ticker */}
        <div className="flex-1 overflow-hidden relative">
          <div className="ticker-scroll flex items-center gap-6 whitespace-nowrap">
            {displayNews.map((item, i) => (
              <a key={i}
                href={item.url !== '#' ? item.url : undefined}
                target={item.url !== '#' ? '_blank' : undefined}
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-[10px] text-[#aaa] hover:text-[#ddd] font-mono cursor-pointer transition-colors"
                onClick={item.url === '#' ? (e) => { e.preventDefault(); setExpanded(!expanded); } : undefined}
              >
                <span className="text-[#b8960c] font-bold">●</span>
                {item.title}
                <span className="text-[#555]">({item.source})</span>
              </a>
            ))}
            {/* Duplicate for seamless loop */}
            {displayNews.map((item, i) => (
              <a key={`dup-${i}`}
                href={item.url !== '#' ? item.url : undefined}
                target={item.url !== '#' ? '_blank' : undefined}
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-[10px] text-[#aaa] hover:text-[#ddd] font-mono cursor-pointer transition-colors"
                onClick={item.url === '#' ? (e) => { e.preventDefault(); setExpanded(!expanded); } : undefined}
              >
                <span className="text-[#b8960c] font-bold">●</span>
                {item.title}
                <span className="text-[#555]">({item.source})</span>
              </a>
            ))}
          </div>
        </div>

        <div className="w-px h-4 bg-[#444] shrink-0" />

        {/* Ollama toggle */}
        {ollamaStatus && (
          <button
            onClick={toggleOllama}
            disabled={toggling}
            className={`flex items-center gap-1 text-[10px] font-mono cursor-pointer whitespace-nowrap transition-colors px-1.5 py-0.5 rounded ${
              ollamaStatus.ollama === 'running'
                ? 'text-[#22c55e] hover:text-[#16a34a] bg-[#22c55e10]'
                : 'text-[#f59e0b] hover:text-[#d97706] bg-[#f59e0b10]'
            }`}
            title={ollamaStatus.ollama === 'running'
              ? `Ollama ON — RecoveryForge: ${ollamaStatus.percentage}%`
              : 'Ollama OFF — MAX faster'}
          >
            <Power size={10} />
            {ollamaStatus.ollama === 'running' ? 'Ollama ON' : 'Ollama OFF'}
          </button>
        )}

        <div className="w-px h-4 bg-[#444] shrink-0" />

        {/* News expand toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-[10px] text-[#666] hover:text-[#aaa] font-mono cursor-pointer whitespace-nowrap transition-colors"
        >
          <Newspaper size={10} />
          {expanded ? <ChevronDown size={10} /> : <ChevronUp size={10} />}
        </button>

        {/* Time */}
        <div className="text-[10px] text-[#666] font-mono whitespace-nowrap" suppressHydrationWarning>
          {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </footer>
    </div>
  );
}
