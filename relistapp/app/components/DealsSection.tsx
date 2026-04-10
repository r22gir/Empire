'use client';

import { useState, useEffect, useCallback } from 'react';
import { Search, Loader2, RefreshCw, Plus, Trash2, ExternalLink, Check, Filter, TrendingUp, AlertTriangle } from 'lucide-react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface Deal {
  id: number;
  title: string;
  source_platform: string;
  source_url: string | null;
  source_price: number;
  shipping_cost: number;
  images: string[];
  brand: string;
  availability: string;
  market_estimate: {
    market_price: number;
    fees_estimate: number;
    shipping_estimate: number;
    estimated_profit: number;
    roi_percent: number;
  };
  deal_score: number;
  deal_label: string;
  deal_reason: string;
  estimated_profit: number;
  roi_percent: number;
  created_at: string;
}

interface DealsResponse {
  deals: Deal[];
  total: number;
  strong: number;
  medium: number;
  weak: number;
}

export default function DealsSection() {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [minScore, setMinScore] = useState(0);
  const [platformFilter, setPlatformFilter] = useState<string>('');
  const [sortBy, setSortBy] = useState<'score' | 'profit' | 'roi' | 'price'>('score');
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [summary, setSummary] = useState({ strong: 0, medium: 0, weak: 0 });

  const fetchDeals = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true);
    else setLoading(true);
    try {
      const params = new URLSearchParams({ sort_by: sortBy, limit: '100' });
      if (minScore > 0) params.set('min_score', String(minScore));
      if (platformFilter) params.set('platform', platformFilter);

      const res = await fetch(`${API}/relist/deals?${params}`);
      const data: DealsResponse = await res.json();
      setDeals(data.deals || []);
      setSummary({ strong: data.strong || 0, medium: data.medium || 0, weak: data.weak || 0 });
    } catch (e) {
      console.error('Failed to fetch deals', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [sortBy, minScore, platformFilter]);

  useEffect(() => {
    fetchDeals();
  }, [fetchDeals]);

  const toggleSelect = (id: number) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  };

  const toggleSelectAll = () => {
    if (selected.size === deals.length) setSelected(new Set());
    else setSelected(new Set(deals.map(d => d.id)));
  };

  const analyzeDeal = async (id: number) => {
    try {
      await fetch(`${API}/relist/sources/${id}/analyze`, { method: 'POST' });
      fetchDeals();
    } catch (e) {
      console.error('Analyze failed', e);
    }
  };

  const createDrafts = async () => {
    const selectedItems = deals.filter(d => selected.has(d.id));
    for (const item of selectedItems) {
      try {
        await fetch(`${API}/relist/listings/from-source`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_id: item.id,
            platform: 'ebay',
            your_price: item.market_estimate?.market_price || item.source_price * 2,
            platform_fee_percent: 13.0,
          }),
        });
      } catch (e) {
        console.error('Failed to create draft', e);
      }
    }
    setSelected(new Set());
  };

  const refreshAll = async () => {
    setRefreshing(true);
    try {
      await fetch(`${API}/relist/sources/bulk-refresh`, { method: 'POST' });
      await fetchDeals(true);
    } catch (e) {
      console.error('Bulk refresh failed', e);
    }
  };

  const LabelBadge = ({ label }: { label: string }) => {
    const colors: Record<string, string> = {
      strong: 'bg-green-100 text-green-700',
      medium: 'bg-yellow-100 text-yellow-700',
      weak: 'bg-red-100 text-red-700',
    };
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${colors[label] || 'bg-gray-100 text-gray-700'}`}>
        {label.toUpperCase()}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={32} className="animate-spin" style={{ color: '#06b6d4' }} />
      </div>
    );
  }

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold mb-1">AI Deal Finder</h2>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>
            Ranked opportunities from your imported products
          </p>
        </div>
        <button className="btn-secondary" onClick={refreshAll} disabled={refreshing}>
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          {refreshing ? 'Refreshing...' : 'Check All Prices'}
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="empire-card text-center py-4">
          <div className="text-2xl font-bold" style={{ color: '#16a34a' }}>{summary.strong}</div>
          <div className="text-xs font-semibold" style={{ color: '#16a34a' }}>Strong Deals</div>
        </div>
        <div className="empire-card text-center py-4">
          <div className="text-2xl font-bold" style={{ color: '#ca8a04' }}>{summary.medium}</div>
          <div className="text-xs font-semibold" style={{ color: '#ca8a04' }}>Medium Deals</div>
        </div>
        <div className="empire-card text-center py-4">
          <div className="text-2xl font-bold" style={{ color: '#dc2626' }}>{summary.weak}</div>
          <div className="text-xs font-semibold" style={{ color: '#dc2626' }}>Weak Deals</div>
        </div>
        <div className="empire-card text-center py-4">
          <div className="text-2xl font-bold">{deals.length}</div>
          <div className="text-xs font-semibold" style={{ color: 'var(--muted)' }}>Total</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">Min Score:</label>
          <input
            type="number"
            min="0"
            max="100"
            className="form-input !w-20 text-sm"
            value={minScore}
            onChange={e => setMinScore(Number(e.target.value))}
          />
        </div>
        <select
          className="form-input !w-40 text-sm"
          value={platformFilter}
          onChange={e => setPlatformFilter(e.target.value)}
        >
          <option value="">All Platforms</option>
          <option value="amazon">Amazon</option>
          <option value="walmart">Walmart</option>
          <option value="aliexpress">AliExpress</option>
          <option value="ebay">eBay</option>
        </select>
        <select
          className="form-input !w-40 text-sm"
          value={sortBy}
          onChange={e => setSortBy(e.target.value as any)}
        >
          <option value="score">Sort by Score</option>
          <option value="profit">Sort by Profit</option>
          <option value="roi">Sort by ROI</option>
          <option value="price">Sort by Price</option>
        </select>
      </div>

      {/* Bulk Actions */}
      {deals.length > 0 && (
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <button className="btn-secondary text-sm" onClick={toggleSelectAll}>
              {selected.size === deals.length ? 'Deselect All' : 'Select All'}
            </button>
            <span className="text-sm" style={{ color: 'var(--muted)' }}>
              {selected.size} selected
            </span>
          </div>
          {selected.size > 0 && (
            <button className="btn-primary text-sm" onClick={createDrafts}>
              <Plus size={14} /> Create {selected.size} Draft{selected.size !== 1 ? 's' : ''}
            </button>
          )}
        </div>
      )}

      {/* Deals Table */}
      {deals.length === 0 ? (
        <div className="empire-card text-center py-16">
          <Search size={40} style={{ color: 'var(--muted)', margin: '0 auto 12px' }} />
          <p className="font-semibold mb-1">No deals found</p>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>
            Import products using the Import URL section first
          </p>
        </div>
      ) : (
        <div className="empire-card !p-0 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b" style={{ borderColor: 'var(--border)' }}>
                <th className="!p-3 text-left w-8">
                  <input
                    type="checkbox"
                    checked={selected.size === deals.length}
                    onChange={toggleSelectAll}
                    className="rounded"
                  />
                </th>
                <th className="!p-3 text-left text-xs font-bold uppercase" style={{ color: 'var(--muted)' }}>Product</th>
                <th className="!p-3 text-center text-xs font-bold uppercase" style={{ color: 'var(--muted)' }}>Source</th>
                <th className="!p-3 text-right text-xs font-bold uppercase" style={{ color: 'var(--muted)' }}>Cost</th>
                <th className="!p-3 text-right text-xs font-bold uppercase" style={{ color: 'var(--muted)' }}>Market</th>
                <th className="!p-3 text-right text-xs font-bold uppercase" style={{ color: 'var(--muted)' }}>Profit</th>
                <th className="!p-3 text-right text-xs font-bold uppercase" style={{ color: 'var(--muted)' }}>ROI</th>
                <th className="!p-3 text-center text-xs font-bold uppercase" style={{ color: 'var(--muted)' }}>Score</th>
                <th className="!p-3 text-center text-xs font-bold uppercase" style={{ color: 'var(--muted)' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {deals.map(deal => (
                <tr
                  key={deal.id}
                  className="border-b last:border-0 hover:bg-gray-50 transition-colors"
                  style={{ borderColor: 'var(--border)' }}
                >
                  <td className="!p-3">
                    <input
                      type="checkbox"
                      checked={selected.has(deal.id)}
                      onChange={() => toggleSelect(deal.id)}
                      className="rounded"
                    />
                  </td>
                  <td className="!p-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded bg-gray-100 overflow-hidden shrink-0">
                        {deal.images && deal.images[0] ? (
                          <img src={deal.images[0]} alt="" className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-gray-400">
                            <Search size={16} />
                          </div>
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="font-semibold text-sm truncate max-w-xs">{deal.title}</div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <LabelBadge label={deal.deal_label} />
                          {deal.availability === 'out_of_stock' && (
                            <span className="text-xs px-1.5 py-0.5 rounded bg-red-50 text-red-600">
                              Out of Stock
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="!p-3 text-center">
                    <span className="text-xs font-semibold uppercase px-2 py-0.5 rounded" style={{ background: '#f3f4f6', color: '#6b7280' }}>
                      {deal.source_platform}
                    </span>
                  </td>
                  <td className="!p-3 text-right font-semibold text-sm">
                    ${deal.source_price.toFixed(2)}
                  </td>
                  <td className="!p-3 text-right font-semibold text-sm">
                    ${(deal.market_estimate?.market_price || 0).toFixed(2)}
                  </td>
                  <td className="!p-3 text-right font-semibold text-sm" style={{ color: '#16a34a' }}>
                    ${(deal.market_estimate?.estimated_profit || 0).toFixed(2)}
                  </td>
                  <td className="!p-3 text-right font-semibold text-sm">
                    {(deal.market_estimate?.roi_percent || 0).toFixed(0)}%
                  </td>
                  <td className="!p-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <div className="w-12 h-2 rounded-full bg-gray-200 overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${deal.deal_score}%`,
                            background: deal.deal_score >= 70 ? '#16a34a' : deal.deal_score >= 40 ? '#ca8a04' : '#dc2626',
                          }}
                        />
                      </div>
                      <span className="text-xs font-bold">{deal.deal_score}</span>
                    </div>
                  </td>
                  <td className="!p-3">
                    <div className="flex items-center justify-center gap-1">
                      <button
                        className="p-1.5 rounded hover:bg-gray-100"
                        title="Re-analyze"
                        onClick={() => analyzeDeal(deal.id)}
                      >
                        <RefreshCw size={14} style={{ color: '#6b7280' }} />
                      </button>
                      {deal.source_url && (
                        <a
                          href={deal.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1.5 rounded hover:bg-gray-100"
                          title="View source"
                        >
                          <ExternalLink size={14} style={{ color: '#6b7280' }} />
                        </a>
                      )}
                      <button
                        className="p-1.5 rounded hover:bg-gray-100"
                        title="Create draft"
                        onClick={() => {
                          setSelected(new Set([deal.id]));
                          createDrafts();
                        }}
                      >
                        <Plus size={14} style={{ color: '#6b7280' }} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Deal explanation for selected */}
      {selected.size === 1 && (
        <div className="mt-4 p-4 rounded-lg border" style={{ borderColor: 'var(--border)', background: '#fafafa' }}>
          {(() => {
            const deal = deals.find(d => selected.has(d.id));
            return deal ? (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle size={16} style={{ color: '#ca8a04' }} />
                  <span className="font-semibold text-sm">Why this deal is rated {deal.deal_label}:</span>
                </div>
                <p className="text-sm" style={{ color: 'var(--muted)' }}>{deal.deal_reason}</p>
              </div>
            ) : null;
          })()}
        </div>
      )}
    </div>
  );
}
