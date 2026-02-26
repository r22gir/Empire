'use client';
import { useState } from 'react';
import { Globe, Search, BarChart3, ExternalLink } from 'lucide-react';
import { StatsBar, TaskList } from './shared';

interface SeoItem { label: string; status: 'good' | 'warning' | 'missing'; detail: string }
interface PageMetric { page: string; views: number; bounce: string; avgTime: string }

const SEO_CHECKLIST: SeoItem[] = [
  { label: 'Google Business Profile', status: 'good', detail: 'Claimed and verified' },
  { label: 'Meta descriptions', status: 'good', detail: 'All pages have unique descriptions' },
  { label: 'Mobile responsive', status: 'good', detail: 'All pages pass mobile test' },
  { label: 'SSL certificate', status: 'good', detail: 'Valid through 2027' },
  { label: 'Schema markup', status: 'warning', detail: 'LocalBusiness schema added, missing FAQ' },
  { label: 'Image alt tags', status: 'warning', detail: '14/22 portfolio images tagged' },
  { label: 'Blog content', status: 'missing', detail: 'No posts in last 30 days' },
  { label: 'Page speed', status: 'good', detail: 'Score: 92/100' },
];

const PAGE_METRICS: PageMetric[] = [
  { page: 'Homepage', views: 1240, bounce: '32%', avgTime: '2:14' },
  { page: 'Portfolio', views: 890, bounce: '18%', avgTime: '3:45' },
  { page: 'Services', views: 645, bounce: '41%', avgTime: '1:32' },
  { page: 'Contact', views: 420, bounce: '25%', avgTime: '1:55' },
  { page: 'About', views: 310, bounce: '52%', avgTime: '0:58' },
  { page: 'Blog', views: 285, bounce: '45%', avgTime: '2:20' },
];

const STATUS_MAP: Record<string, { color: string; icon: string }> = {
  good: { color: '#22c55e', icon: '✓' },
  warning: { color: '#f59e0b', icon: '!' },
  missing: { color: '#ef4444', icon: '✗' },
};

export default function WebsiteDesk() {
  const [tab, setTab] = useState<'seo' | 'analytics'>('analytics');

  const seoGood = SEO_CHECKLIST.filter(s => s.status === 'good').length;
  const totalViews = PAGE_METRICS.reduce((s, p) => s + p.views, 0);

  return (
    <div className="flex flex-col h-full">
      <StatsBar
        items={[
          { label: 'Monthly Views', value: totalViews.toLocaleString(), icon: BarChart3, color: '#14B8A6' },
          { label: 'SEO Score', value: `${seoGood}/${SEO_CHECKLIST.length}`, icon: Search, color: 'var(--gold)' },
          { label: 'Pages', value: String(PAGE_METRICS.length), icon: Globe, color: 'var(--purple)' },
        ]}
        rightSlot={
          <div className="flex items-center gap-1 shrink-0">
            {(['analytics', 'seo'] as const).map(v => (
              <button
                key={v}
                onClick={() => setTab(v)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium transition capitalize"
                style={{
                  background: tab === v ? 'var(--gold-pale)' : 'transparent',
                  color: tab === v ? 'var(--gold)' : 'var(--text-muted)',
                  border: tab === v ? '1px solid var(--gold-border)' : '1px solid transparent',
                }}
              >
                {v}
              </button>
            ))}
          </div>
        }
      />

      <div className="flex-1 overflow-auto p-4 flex gap-4">
        <div className="flex-1 flex flex-col gap-4">
          {tab === 'analytics' ? (
            <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
              <table className="w-full text-xs">
                <thead>
                  <tr style={{ background: 'var(--elevated)' }}>
                    {['Page', 'Views', 'Bounce Rate', 'Avg Time'].map(h => (
                      <th key={h} className="text-left px-4 py-2.5 font-semibold" style={{ color: 'var(--gold)', borderBottom: '1px solid var(--border)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {PAGE_METRICS.map(p => (
                    <tr
                      key={p.page}
                      className="transition"
                      style={{ borderBottom: '1px solid var(--border)' }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'var(--hover)')}
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                    >
                      <td className="px-4 py-2.5 font-medium flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                        {p.page}
                        <ExternalLink className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
                      </td>
                      <td className="px-4 py-2.5 font-mono font-semibold" style={{ color: '#14B8A6' }}>{p.views.toLocaleString()}</td>
                      <td className="px-4 py-2.5 font-mono" style={{ color: parseInt(p.bounce) > 40 ? '#ef4444' : 'var(--text-secondary)' }}>{p.bounce}</td>
                      <td className="px-4 py-2.5 font-mono" style={{ color: 'var(--text-secondary)' }}>{p.avgTime}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="space-y-2">
              {SEO_CHECKLIST.map(item => {
                const s = STATUS_MAP[item.status];
                return (
                  <div
                    key={item.label}
                    className="rounded-xl p-3 flex items-center gap-3"
                    style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
                  >
                    <span
                      className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                      style={{ background: s.color + '18', color: s.color }}
                    >
                      {s.icon}
                    </span>
                    <div className="flex-1">
                      <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{item.label}</p>
                      <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>{item.detail}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          <TaskList desk="website" compact />
        </div>
      </div>
    </div>
  );
}
