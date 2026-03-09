'use client';

import { ArrowLeft, RefreshCw, Wifi } from 'lucide-react';
import { mockConnections } from '../lib/mock-data';

const PLATFORM_COLORS: Record<string, string> = {
  ebay: '#e53238', etsy: '#f1641e', shopify: '#96bf48', facebook: '#1877f2',
  mercari: '#4dc4e0', poshmark: '#7f0353', amazon: '#ff9900', depop: '#ff2300',
};

export default function TopBar() {
  const activeConnections = mockConnections.filter(c => c.status === 'active');

  return (
    <header className="h-14 border-b flex items-center justify-between px-5 bg-white" style={{ borderColor: 'var(--border)' }}>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm"
               style={{ background: 'linear-gradient(135deg, #06b6d4, #b8960c)' }}>
            R
          </div>
          <span className="font-semibold text-base">RelistApp</span>
          <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: 'var(--gold-light)', color: 'var(--gold)', border: '1px solid var(--gold-border)' }}>
            v1.0
          </span>
        </div>

        <div className="h-5 w-px bg-gray-200 mx-1" />

        <div className="flex items-center gap-1.5">
          {activeConnections.map(c => (
            <div
              key={c.platform}
              className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-white"
              style={{ background: PLATFORM_COLORS[c.platform] || '#666' }}
              title={`${c.platform}: ${c.account_name}`}
            >
              <Wifi size={10} />
              {c.platform.charAt(0).toUpperCase() + c.platform.slice(1)}
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button className="btn-secondary text-xs py-1.5 px-3">
          <RefreshCw size={13} />
          Sync All
        </button>
        <a
          href="http://localhost:3005"
          className="flex items-center gap-1.5 text-sm hover:opacity-70 transition-opacity"
          style={{ color: 'var(--gold)' }}
        >
          <ArrowLeft size={14} />
          Command Center
        </a>
      </div>
    </header>
  );
}
