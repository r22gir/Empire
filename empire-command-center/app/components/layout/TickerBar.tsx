'use client';
import { useState } from 'react';
import { ExternalLink, ChevronUp, ChevronDown, Newspaper } from 'lucide-react';

export default function TickerBar() {
  const [expanded, setExpanded] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  if (collapsed) {
    return (
      <div onClick={() => setCollapsed(false)}
        className="h-[16px] bg-[#1a1a1a] flex items-center justify-center cursor-pointer shrink-0 hover:bg-[#222] transition-colors">
        <span className="text-[9px] text-[#555] font-mono tracking-wider">▲ TICKER</span>
      </div>
    );
  }

  return (
    <div className="bg-[#1a1a1a] shrink-0 border-t border-[#333]">
      {/* Ticker strip */}
      <div className="h-[34px] flex items-center px-4 gap-5 overflow-x-auto select-none">
        <TickerItem label="₿" color="#f59e0b" onClick={() => window.open('https://www.coingecko.com', '_blank')}>
          <span className="text-[#ddd] font-semibold">BTC $68.1K</span>
          <span className="text-[#22C55E] font-bold">↑3.1%</span>
          <span className="text-[#ccc]">ETH $2.0K</span>
          <span className="text-[#ccc]">SOL $84</span>
        </TickerItem>
        <Div />
        <TickerItem label="☁" color="#06b6d4" onClick={() => window.open('https://weather.gov', '_blank')}>
          <span className="text-[#ddd]">DC --°F</span>
        </TickerItem>
        <Div />
        <TickerItem label="📰" color="#22c55e" onClick={() => setExpanded(!expanded)}>
          <span className="text-[#ddd] font-semibold">World News</span>
          <span className="text-[#888]">· Click for details</span>
          {expanded ? <ChevronDown size={10} className="text-[#666]" /> : <ChevronUp size={10} className="text-[#666]" />}
        </TickerItem>
        <Div />
        <TickerItem label="⚽" color="#ef4444" onClick={() => window.open('https://www.espn.com', '_blank')}>
          <span className="text-[#ccc]">Sports · Live scores</span>
        </TickerItem>
        <Div />
        <TickerItem label="⚡" color="#8b5cf6">
          <span className="text-[#ddd] font-semibold">5 services ✓</span>
          <span className="text-[#aaa]">· 97 memories</span>
        </TickerItem>
        <div className="ml-auto flex items-center gap-2">
          <button onClick={() => setCollapsed(true)} className="text-[9px] text-[#555] hover:text-[#888] font-mono cursor-pointer">▼ hide</button>
        </div>
      </div>

      {/* Expanded news section */}
      {expanded && (
        <div className="border-t border-[#333] px-4 py-3 max-h-[200px] overflow-y-auto">
          <div className="flex items-center gap-2 mb-2">
            <Newspaper size={14} className="text-[#22c55e]" />
            <span className="text-xs font-bold text-[#22c55e]">WORLD NEWS</span>
            <span className="text-[9px] text-[#555]">· Click headlines to read</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <NewsCard title="Tech industry shifts accelerate amid AI boom" source="Reuters" url="https://reuters.com" />
            <NewsCard title="Markets rally on economic optimism" source="Bloomberg" url="https://bloomberg.com" />
            <NewsCard title="New climate accord reached at summit" source="AP News" url="https://apnews.com" />
            <NewsCard title="Housing market shows recovery signs" source="CNBC" url="https://cnbc.com" />
            <NewsCard title="Space launch program advances to next phase" source="NASA" url="https://nasa.gov" />
            <NewsCard title="Global supply chain improvements continue" source="WSJ" url="https://wsj.com" />
          </div>
        </div>
      )}
    </div>
  );
}

function TickerItem({ label, color, children, onClick }: { label: string; color: string; children: React.ReactNode; onClick?: () => void }) {
  return (
    <div className={`flex items-center gap-2 text-[11px] font-mono whitespace-nowrap ${onClick ? 'cursor-pointer hover:opacity-80' : ''}`}
      onClick={onClick}>
      <span className="font-bold text-[10px]" style={{ color }}>{label}</span>
      {children}
      {onClick && <ExternalLink size={9} className="text-[#555]" />}
    </div>
  );
}

function Div() {
  return <div className="w-px h-4 bg-[#444] shrink-0" />;
}

function NewsCard({ title, source, url }: { title: string; source: string; url: string }) {
  return (
    <a href={url} target="_blank" rel="noopener noreferrer"
      className="block p-2 rounded-lg bg-[#222] border border-[#333] hover:border-[#555] hover:bg-[#2a2a2a] transition-all cursor-pointer">
      <div className="text-[11px] text-[#ccc] font-medium leading-tight line-clamp-2">{title}</div>
      <div className="text-[9px] text-[#666] mt-1 flex items-center gap-1">
        {source} <ExternalLink size={8} />
      </div>
    </a>
  );
}
