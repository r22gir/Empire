'use client';

import { useState, useCallback } from 'react';
import { Link2, Loader2, Check, X, AlertCircle, ExternalLink, RefreshCw, Plus, Trash2 } from 'lucide-react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface ImportedProduct {
  id: number;
  title: string;
  source_platform: string;
  source_url: string;
  price: number;
  shipping_cost: number;
  images: string[];
  brand: string;
  market_estimate: {
    market_price: number;
    fees_estimate: number;
    shipping_estimate: number;
    estimated_profit: number;
    roi_percent: number;
  };
  deal: {
    score: number;
    label: string;
    reason: string;
    market_price: number;
  };
  saved: boolean;
}

interface SelectedProduct {
  id: number;
  title: string;
  source_platform: string;
  source_price: number;
  market_price: number;
  estimated_profit: number;
  roi_percent: number;
  deal_label: string;
  deal_score: number;
}

export default function ImportSection() {
  const [url, setUrl] = useState('');
  const [importing, setImporting] = useState(false);
  const [results, setResults] = useState<ImportedProduct[]>([]);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const importUrl = useCallback(async () => {
    if (!url.trim()) return;
    setImporting(true);
    setError('');
    try {
      const res = await fetch(`${API}/relist/sources/import-full`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Import failed');
      setResults(prev => [data, ...prev]);
      setUrl('');
    } catch (e: any) {
      setError(e.message || 'Failed to import URL');
    } finally {
      setImporting(false);
    }
  }, [url]);

  const deleteResult = (id: number) => {
    setResults(prev => prev.filter(r => r.id !== id));
    setSelected(prev => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const toggleSelect = (id: number) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  };

  const toggleSelectAll = () => {
    if (selected.size === results.length) setSelected(new Set());
    else setSelected(new Set(results.map(r => r.id)));
  };

  const createDrafts = async () => {
    const selectedItems = results.filter(r => selected.has(r.id));
    for (const item of selectedItems) {
      try {
        await fetch(`${API}/relist/listings/from-source`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_id: item.id,
            platform: 'ebay',
            your_price: item.deal.market_price,
            platform_fee_percent: 13.0,
          }),
        });
      } catch (e) {
        console.error('Failed to create draft for', item.id, e);
      }
    }
    setSelected(new Set());
  };

  const LabelBadge = ({ label }: { label: string }) => {
    const colors: Record<string, string> = {
      strong: 'bg-green-100 text-green-700 border-green-200',
      medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      weak: 'bg-red-100 text-red-700 border-red-200',
    };
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-bold border ${colors[label] || 'bg-gray-100 text-gray-700'}`}>
        {label.toUpperCase()}
      </span>
    );
  };

  return (
    <div className="max-w-5xl">
      <div className="mb-6">
        <h2 className="text-xl font-bold mb-1">Import Product URL</h2>
        <p className="text-sm" style={{ color: 'var(--muted)' }}>
          Paste a product URL from Amazon, Walmart, AliExpress, eBay, or any major marketplace to import and analyze it.
        </p>
      </div>

      {/* URL Input */}
      <div className="empire-card mb-6">
        <div className="flex gap-3">
          <input
            type="url"
            placeholder="https://amazon.com/dp/... or any product URL"
            className="form-input flex-1"
            value={url}
            onChange={e => setUrl(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && importUrl()}
          />
          <button
            className="btn-primary"
            onClick={importUrl}
            disabled={importing || !url.trim()}
          >
            {importing ? <Loader2 size={15} className="animate-spin" /> : <Link2 size={15} />}
            {importing ? 'Importing...' : 'Import'}
          </button>
        </div>
        {error && (
          <div className="mt-3 p-3 rounded-lg flex items-center gap-2" style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626' }}>
            <AlertCircle size={16} />
            <span className="text-sm">{error}</span>
          </div>
        )}
        <p className="text-xs mt-2" style={{ color: 'var(--muted)' }}>
          Supported: Amazon, Walmart, AliExpress, eBay, Costco, Target, BestBuy
        </p>
      </div>

      {/* Bulk Actions */}
      {results.length > 0 && (
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <button className="btn-secondary text-sm" onClick={toggleSelectAll}>
              {selected.size === results.length ? 'Deselect All' : 'Select All'}
            </button>
            <span className="text-sm" style={{ color: 'var(--muted)' }}>
              {selected.size} of {results.length} selected
            </span>
          </div>
          {selected.size > 0 && (
            <div className="flex gap-2">
              <button className="btn-primary text-sm" onClick={createDrafts}>
                <Plus size={14} /> Create {selected.size} Draft{selected.size !== 1 ? 's' : ''}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Results */}
      {results.length === 0 ? (
        <div className="empire-card text-center py-16">
          <Link2 size={40} style={{ color: 'var(--muted)', margin: '0 auto 12px' }} />
          <p className="font-semibold mb-1">No products imported yet</p>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>
            Paste a product URL above to get started
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {results.map(product => (
            <div
              key={product.id}
              className="empire-card"
              style={{
                border: selected.has(product.id) ? '2px solid #06b6d4' : '1px solid var(--border)',
                cursor: 'pointer',
              }}
              onClick={() => toggleSelect(product.id)}
            >
              <div className="flex gap-4">
                {/* Image */}
                <div className="shrink-0 w-20 h-20 rounded-lg overflow-hidden bg-gray-100">
                  {product.images && product.images[0] ? (
                    <img src={product.images[0]} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-400">
                      <Link2 size={24} />
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold uppercase px-2 py-0.5 rounded" style={{ background: '#f3f4f6', color: '#6b7280' }}>
                        {product.source_platform}
                      </span>
                      <LabelBadge label={product.deal?.label || 'weak'} />
                    </div>
                    <div className="flex items-center gap-2">
                      {selected.has(product.id) && (
                        <div className="w-5 h-5 rounded bg-cyan-500 flex items-center justify-center">
                          <Check size={12} className="text-white" />
                        </div>
                      )}
                      <button
                        className="p-1 rounded hover:bg-gray-100"
                        onClick={e => { e.stopPropagation(); deleteResult(product.id); }}
                      >
                        <Trash2 size={14} style={{ color: '#dc2626' }} />
                      </button>
                    </div>
                  </div>

                  <h4 className="font-semibold text-sm mb-1 truncate">{product.title}</h4>

                  {product.source_url && (
                    <a
                      href={product.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs flex items-center gap-1 mb-2"
                      style={{ color: '#06b6d4' }}
                      onClick={e => e.stopPropagation()}
                    >
                      <ExternalLink size={11} />
                      View source
                    </a>
                  )}

                  {/* Metrics */}
                  <div className="grid grid-cols-5 gap-2 text-xs">
                    <div>
                      <span className="text-gray-500 block">Source Price</span>
                      <span className="font-semibold">${product.price.toFixed(2)}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Est. Market</span>
                      <span className="font-semibold">${(product.deal?.market_price || 0).toFixed(2)}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Est. Profit</span>
                      <span className="font-semibold" style={{ color: '#16a34a' }}>
                        ${(product.market_estimate?.estimated_profit || 0).toFixed(2)}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">ROI</span>
                      <span className="font-semibold">{(product.market_estimate?.roi_percent || 0).toFixed(0)}%</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Score</span>
                      <span className="font-semibold">{product.deal?.score || 0}/100</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Deal explanation */}
              {product.deal?.reason && (
                <div className="mt-3 pt-3 border-t text-xs" style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}>
                  {product.deal.reason}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
