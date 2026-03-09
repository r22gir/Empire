'use client';

import { useState } from 'react';
import { Wifi, WifiOff, RefreshCw, Link, Unlink, Clock, AlertTriangle } from 'lucide-react';
import { mockConnections, PLATFORM_COLORS } from '../lib/mock-data';
import { Platform } from '../lib/types';

const PLATFORM_INFO: Record<string, { label: string; coming_soon?: boolean; premium?: boolean }> = {
  ebay: { label: 'eBay' },
  etsy: { label: 'Etsy' },
  shopify: { label: 'Shopify' },
  facebook: { label: 'Facebook Marketplace' },
  mercari: { label: 'Mercari' },
  poshmark: { label: 'Poshmark', coming_soon: true },
  amazon: { label: 'Amazon', premium: true },
  depop: { label: 'Depop', coming_soon: true },
};

const syncLog = [
  { time: '2026-03-09 08:30', platform: 'ebay', action: 'Full sync completed', items: 67, status: 'success' },
  { time: '2026-03-09 07:45', platform: 'etsy', action: 'Full sync completed', items: 24, status: 'success' },
  { time: '2026-03-09 06:00', platform: 'shopify', action: 'Full sync completed', items: 18, status: 'success' },
  { time: '2026-03-08 22:00', platform: 'facebook', action: 'Partial sync - 2 errors', items: 13, status: 'warning' },
  { time: '2026-03-08 20:00', platform: 'ebay', action: 'Price update sync', items: 5, status: 'success' },
  { time: '2026-03-08 18:00', platform: 'mercari', action: 'Sync failed - token expired', items: 0, status: 'error' },
];

export default function PlatformsSection() {
  const [autoSync, setAutoSync] = useState<Record<string, boolean>>({
    ebay: true, etsy: true, shopify: true, facebook: false, mercari: false,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Platforms</h1>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Connected marketplace management</p>
      </div>

      {/* Platform Cards */}
      <div className="grid grid-cols-2 gap-4">
        {mockConnections.map(conn => {
          const info = PLATFORM_INFO[conn.platform];
          const color = PLATFORM_COLORS[conn.platform];
          const isActive = conn.status === 'active';

          return (
            <div key={conn.platform} className="empire-card" style={{ borderLeft: `4px solid ${color}` }}>
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold" style={{ background: color }}>
                    {(info?.label || conn.platform)[0].toUpperCase()}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold">{info?.label || conn.platform}</h3>
                      {info?.coming_soon && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100" style={{ color: 'var(--muted)' }}>Coming Soon</span>
                      )}
                      {info?.premium && (
                        <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: 'var(--gold-light)', color: 'var(--gold)' }}>Premium</span>
                      )}
                    </div>
                    {conn.account_name && (
                      <p className="text-xs" style={{ color: 'var(--muted)' }}>{conn.account_name}</p>
                    )}
                  </div>
                </div>
                <div className={`status-pill ${isActive ? 'active' : conn.status === 'error' ? 'error' : 'draft'}`}>
                  {isActive ? <Wifi size={11} /> : <WifiOff size={11} />}
                  {conn.status}
                </div>
              </div>

              {isActive && (
                <div className="grid grid-cols-3 gap-3 mb-3 text-center">
                  <div className="p-2 rounded-lg" style={{ background: '#f9fafb' }}>
                    <div className="text-lg font-bold">{conn.listings_count}</div>
                    <div className="text-xs" style={{ color: 'var(--muted)' }}>Listings</div>
                  </div>
                  <div className="p-2 rounded-lg" style={{ background: '#f9fafb' }}>
                    <div className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                      {conn.last_sync ? new Date(conn.last_sync).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                    </div>
                    <div className="text-xs" style={{ color: 'var(--muted)' }}>Last Sync</div>
                  </div>
                  <div className="p-2 rounded-lg" style={{ background: '#f9fafb' }}>
                    <div className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>{conn.connected_at}</div>
                    <div className="text-xs" style={{ color: 'var(--muted)' }}>Connected</div>
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2">
                {isActive ? (
                  <>
                    <button className="btn-secondary text-xs flex-1 justify-center">
                      <RefreshCw size={13} /> Force Sync
                    </button>
                    <label className="flex items-center gap-1.5 text-xs cursor-pointer">
                      <input
                        type="checkbox"
                        className="accent-cyan-500"
                        checked={autoSync[conn.platform] || false}
                        onChange={e => setAutoSync({ ...autoSync, [conn.platform]: e.target.checked })}
                      />
                      Auto-Sync
                    </label>
                    <button className="btn-danger text-xs">
                      <Unlink size={13} /> Disconnect
                    </button>
                  </>
                ) : (
                  <button
                    className="btn-primary text-xs flex-1 justify-center"
                    disabled={info?.coming_soon}
                    style={info?.coming_soon ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
                  >
                    <Link size={13} /> {info?.coming_soon ? 'Coming Soon' : info?.premium ? 'Upgrade to Connect' : 'Connect'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Sync History */}
      <div className="empire-card">
        <div className="section-label mb-3">Sync History</div>
        <table className="empire-table text-sm">
          <thead><tr><th>Time</th><th>Platform</th><th>Action</th><th>Items</th><th>Status</th></tr></thead>
          <tbody>
            {syncLog.map((log, i) => (
              <tr key={i}>
                <td style={{ color: 'var(--muted)' }}>{log.time}</td>
                <td>
                  <span className="capitalize font-medium" style={{ color: PLATFORM_COLORS[log.platform] }}>{log.platform}</span>
                </td>
                <td>{log.action}</td>
                <td>{log.items}</td>
                <td>
                  {log.status === 'success' && <span className="status-pill active">Success</span>}
                  {log.status === 'warning' && <span className="status-pill pending">Warning</span>}
                  {log.status === 'error' && <span className="status-pill error">Error</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
