'use client';

import { useState } from 'react';
import { Search, TrendingUp, DollarSign, Calculator, Sparkles, ExternalLink } from 'lucide-react';
import { mockComps, PLATFORM_COLORS, PLATFORM_FEES } from '../lib/mock-data';

export default function PricingSection() {
  const [searchQuery, setSearchQuery] = useState('Vintage Levi\'s 501 Jeans');
  const [hasSearched, setHasSearched] = useState(true);
  const [purchasePrice, setPurchasePrice] = useState(12);
  const [salePrice, setSalePrice] = useState(68);
  const [selectedPlatform, setSelectedPlatform] = useState('ebay');
  const [shippingCost, setShippingCost] = useState(8.50);

  const fee = PLATFORM_FEES[selectedPlatform];
  const platformFee = fee ? salePrice * fee.rate + fee.fixed : 0;
  const profit = salePrice - purchasePrice - platformFee - shippingCost;
  const margin = salePrice > 0 ? (profit / salePrice) * 100 : 0;

  const avgSoldPrice = mockComps.reduce((s, c) => s + c.sold_price, 0) / mockComps.length;
  const lowPrice = Math.min(...mockComps.map(c => c.sold_price));
  const highPrice = Math.max(...mockComps.map(c => c.sold_price));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Pricing Intelligence</h1>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>AI-powered pricing analysis and margin calculator</p>
      </div>

      {/* Search */}
      <div className="empire-card">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--muted)' }} />
            <input
              type="text"
              className="form-input pl-9"
              placeholder="Search product name or paste a URL..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>
          <button className="btn-primary" onClick={() => setHasSearched(true)}>
            <Sparkles size={15} /> AI Price Check
          </button>
        </div>
      </div>

      {hasSearched && (
        <>
          {/* Price Recommendation */}
          <div className="grid grid-cols-3 gap-4">
            <div className="empire-card text-center" style={{ borderTop: '3px solid var(--green)' }}>
              <div className="section-label">Suggested Price</div>
              <div className="text-3xl font-bold mt-2" style={{ color: 'var(--green)' }}>
                ${avgSoldPrice.toFixed(2)}
              </div>
              <div className="text-xs mt-1" style={{ color: 'var(--muted)' }}>Based on {mockComps.length} recent sales</div>
            </div>
            <div className="empire-card text-center" style={{ borderTop: '3px solid var(--blue)' }}>
              <div className="section-label">Price Range</div>
              <div className="text-xl font-bold mt-2" style={{ color: 'var(--blue)' }}>
                ${lowPrice.toFixed(2)} — ${highPrice.toFixed(2)}
              </div>
              <div className="mt-2 h-2 rounded-full bg-gray-100 relative">
                <div
                  className="absolute h-full rounded-full"
                  style={{
                    background: 'var(--blue)',
                    left: '10%',
                    right: '10%',
                    opacity: 0.3,
                  }}
                />
                <div
                  className="absolute w-2 h-4 rounded-sm -top-1"
                  style={{
                    background: 'var(--green)',
                    left: `${((avgSoldPrice - lowPrice) / (highPrice - lowPrice)) * 80 + 10}%`,
                  }}
                />
              </div>
            </div>
            <div className="empire-card text-center" style={{ borderTop: '3px solid var(--gold)' }}>
              <div className="section-label">Confidence</div>
              <div className="text-3xl font-bold mt-2" style={{ color: 'var(--gold)' }}>87%</div>
              <div className="text-xs mt-1" style={{ color: 'var(--muted)' }}>High confidence — good data</div>
            </div>
          </div>

          {/* Comparable Sales */}
          <div className="empire-card">
            <div className="section-label mb-3">Comparable Sold Items</div>
            <div className="grid grid-cols-2 gap-3">
              {mockComps.map((comp, i) => (
                <div key={i} className="p-3 rounded-lg border flex items-start justify-between" style={{ borderColor: 'var(--border)' }}>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{comp.title}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs capitalize" style={{ color: PLATFORM_COLORS[comp.platform] }}>{comp.platform}</span>
                      <span className="text-xs" style={{ color: 'var(--muted)' }}>{comp.condition}</span>
                      <span className="text-xs" style={{ color: 'var(--muted)' }}>{comp.sold_date}</span>
                    </div>
                  </div>
                  <div className="text-base font-bold" style={{ color: 'var(--green)' }}>${comp.sold_price.toFixed(2)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Margin Calculator */}
          <div className="empire-card">
            <div className="flex items-center gap-2 mb-4">
              <Calculator size={18} style={{ color: 'var(--teal)' }} />
              <h3 className="font-semibold">Margin Calculator</h3>
            </div>

            <div className="grid grid-cols-4 gap-4 mb-4">
              <div>
                <label className="section-label">Purchase Price</label>
                <input
                  type="number"
                  className="form-input"
                  value={purchasePrice}
                  onChange={e => setPurchasePrice(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="section-label">Sale Price</label>
                <input
                  type="number"
                  className="form-input"
                  value={salePrice}
                  onChange={e => setSalePrice(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="section-label">Platform</label>
                <select className="form-input" value={selectedPlatform} onChange={e => setSelectedPlatform(e.target.value)}>
                  {Object.entries(PLATFORM_FEES).map(([k, v]) => (
                    <option key={k} value={k}>{k.charAt(0).toUpperCase() + k.slice(1)} ({v.label})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="section-label">Shipping Cost</label>
                <input
                  type="number"
                  className="form-input"
                  value={shippingCost}
                  onChange={e => setShippingCost(Number(e.target.value))}
                  step={0.5}
                />
              </div>
            </div>

            {/* Fee Breakdown */}
            <div className="rounded-lg p-4" style={{ background: '#f9fafb' }}>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>Sale Price</span>
                  <span className="font-medium">${salePrice.toFixed(2)}</span>
                </div>
                <div className="flex justify-between" style={{ color: 'var(--red)' }}>
                  <span>- Purchase Price</span>
                  <span>-${purchasePrice.toFixed(2)}</span>
                </div>
                <div className="flex justify-between" style={{ color: 'var(--red)' }}>
                  <span>- Platform Fee ({fee?.label})</span>
                  <span>-${platformFee.toFixed(2)}</span>
                </div>
                <div className="flex justify-between" style={{ color: 'var(--red)' }}>
                  <span>- Shipping</span>
                  <span>-${shippingCost.toFixed(2)}</span>
                </div>
                <div className="border-t pt-2 flex justify-between font-bold" style={{ borderColor: 'var(--border)' }}>
                  <span>Net Profit</span>
                  <span style={{ color: profit >= 0 ? 'var(--green)' : 'var(--red)' }}>${profit.toFixed(2)}</span>
                </div>
                <div className="flex justify-between font-medium">
                  <span>Margin</span>
                  <span style={{ color: margin >= 20 ? 'var(--green)' : margin >= 0 ? 'var(--orange)' : 'var(--red)' }}>
                    {margin.toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>

            {/* All Platform Fee Comparison */}
            <div className="mt-4">
              <div className="section-label mb-2">Fee Comparison Across Platforms</div>
              <div className="grid grid-cols-4 gap-2">
                {Object.entries(PLATFORM_FEES).map(([platform, feeInfo]) => {
                  const pFee = salePrice * feeInfo.rate + feeInfo.fixed;
                  const pProfit = salePrice - purchasePrice - pFee - shippingCost;
                  return (
                    <div key={platform} className="p-2 rounded-lg border text-center text-sm" style={{ borderColor: 'var(--border)' }}>
                      <div className="font-medium capitalize" style={{ color: PLATFORM_COLORS[platform] }}>{platform}</div>
                      <div className="text-xs" style={{ color: 'var(--muted)' }}>Fee: ${pFee.toFixed(2)}</div>
                      <div className="font-bold" style={{ color: pProfit >= 0 ? 'var(--green)' : 'var(--red)' }}>
                        ${pProfit.toFixed(2)}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
