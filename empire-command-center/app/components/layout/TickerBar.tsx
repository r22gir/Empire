'use client';
import { useState } from 'react';

export default function TickerBar() {
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
    <div onClick={() => setCollapsed(true)}
      className="h-[34px] bg-[#1a1a1a] flex items-center px-4 gap-5 overflow-x-auto shrink-0 cursor-pointer select-none border-t border-[#333]">
      <TickerGroup color="#f59e0b" label="₿">
        <span className="text-[#ddd] font-semibold">BTC $68.1K</span>
        <span className="text-[#22C55E] font-bold">↑3.1%</span>
        <span className="text-[#ccc]">ETH $2.0K</span>
        <span className="text-[#ccc]">SOL $84</span>
        <span className="text-[#22C55E] font-bold">↑5.4%</span>
      </TickerGroup>
      <Divider />
      <TickerGroup color="#06b6d4" label="☁">
        <span className="text-[#ddd]">DC --°F</span>
      </TickerGroup>
      <Divider />
      <TickerGroup color="#22c55e" label="📰">
        <span className="text-[#ccc]">Tech shifts accelerate...</span>
      </TickerGroup>
      <Divider />
      <TickerGroup color="#ef4444" label="⚽">
        <span className="text-[#ccc]">DAL 0 — BOS 0</span>
      </TickerGroup>
      <Divider />
      <TickerGroup color="#8b5cf6" label="⚡">
        <span className="text-[#ddd] font-semibold">5 services ✓</span>
        <span className="text-[#aaa]">· 97 memories</span>
      </TickerGroup>
    </div>
  );
}

function TickerGroup({ color, label, children }: { color: string; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 text-[11px] font-mono whitespace-nowrap">
      <span className="font-bold text-[10px]" style={{ color }}>{label}</span>
      {children}
    </div>
  );
}

function Divider() {
  return <div className="w-px h-4 bg-[#444]" />;
}
