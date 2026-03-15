'use client';
import React, { useState, useEffect } from 'react';
import { API } from '../../../lib/api';
import {
  Users, Loader2, ChevronDown, ChevronUp, Mail, Phone, PenTool
} from 'lucide-react';
import SearchBar from '../shared/SearchBar';
import EmptyState from '../shared/EmptyState';

export default function CRMModule() {
  const [customers, setCustomers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expandedCustomer, setExpandedCustomer] = useState<string | null>(null);
  const [customerDesigns, setCustomerDesigns] = useState<any[]>([]);
  const [designsLoading, setDesignsLoading] = useState(false);

  useEffect(() => {
    fetch(`${API}/craftforge/customers`)
      .then(r => r.json())
      .then(data => {
        setCustomers(Array.isArray(data) ? data : data.customers || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const loadDesigns = (customerName: string) => {
    if (expandedCustomer === customerName) {
      setExpandedCustomer(null);
      setCustomerDesigns([]);
      return;
    }
    setExpandedCustomer(customerName);
    setDesignsLoading(true);
    fetch(`${API}/craftforge/designs?customer=${encodeURIComponent(customerName)}`)
      .then(r => r.json())
      .then(data => {
        setCustomerDesigns(Array.isArray(data) ? data : data.designs || []);
        setDesignsLoading(false);
      })
      .catch(() => setDesignsLoading(false));
  };

  const filtered = customers.filter(c => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (c.name || '').toLowerCase().includes(q) ||
           (c.email || '').toLowerCase().includes(q) ||
           (c.phone || '').toLowerCase().includes(q);
  });

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-5">
        <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }} className="flex items-center gap-2">
          <Users size={20} className="text-[#b8960c]" /> Customers
        </h2>
        <div className="w-64">
          <SearchBar value={search} onChange={setSearch} placeholder="Search customers..." />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={24} className="text-[#b8960c] animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Users size={32} />}
          title="No customers found"
          description={search ? 'Try adjusting your search terms.' : 'Customers will appear here when designs are created.'}
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((c, i) => {
            const isExpanded = expandedCustomer === c.name;
            return (
              <div key={c.name || i} className="empire-card flat" style={{ padding: 0, overflow: 'hidden' }}>
                {/* Customer row */}
                <button
                  onClick={() => loadDesigns(c.name)}
                  className="w-full flex items-center justify-between cursor-pointer hover:bg-[#f5f3ef] transition-colors"
                  style={{ padding: '14px 16px', background: isExpanded ? '#fdf8eb' : 'transparent', border: 'none', textAlign: 'left' }}
                >
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0" style={{ background: '#fdf8eb', color: '#b8960c' }}>
                      <span style={{ fontSize: 14, fontWeight: 700 }}>{(c.name || '?')[0].toUpperCase()}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a' }} className="truncate">{c.name || '--'}</div>
                      <div className="flex items-center gap-4 mt-0.5">
                        {c.email && (
                          <span className="flex items-center gap-1 text-[11px] text-[#777]">
                            <Mail size={10} /> {c.email}
                          </span>
                        )}
                        {c.phone && (
                          <span className="flex items-center gap-1 text-[11px] text-[#777]">
                            <Phone size={10} /> {c.phone}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6 shrink-0">
                    <div className="text-right">
                      <div style={{ fontSize: 14, fontWeight: 700, color: '#b8960c' }}>${Number(c.total_revenue || 0).toLocaleString()}</div>
                      <div style={{ fontSize: 10, color: '#999' }}>total spent</div>
                    </div>
                    <div className="text-right">
                      <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>{c.total_designs || 0}</div>
                      <div style={{ fontSize: 10, color: '#999' }}>projects</div>
                    </div>
                    <div className="text-right" style={{ minWidth: 60 }}>
                      <div style={{ fontSize: 10, color: '#999' }} suppressHydrationWarning>
                        {c.last_order ? new Date(c.last_order).toLocaleDateString() : '--'}
                      </div>
                      <div style={{ fontSize: 9, color: '#bbb' }}>last order</div>
                    </div>
                    {isExpanded ? <ChevronUp size={16} className="text-[#b8960c]" /> : <ChevronDown size={16} className="text-[#999]" />}
                  </div>
                </button>

                {/* Expanded design history */}
                {isExpanded && (
                  <div style={{ borderTop: '1px solid #ece8e0', padding: '12px 16px', background: '#faf9f7' }}>
                    {designsLoading ? (
                      <div className="flex items-center justify-center py-4">
                        <Loader2 size={16} className="text-[#b8960c] animate-spin" />
                      </div>
                    ) : customerDesigns.length === 0 ? (
                      <div className="text-center py-4">
                        <span style={{ fontSize: 12, color: '#999' }}>No design history found.</span>
                      </div>
                    ) : (
                      <div>
                        <div className="section-label mb-2">Design History</div>
                        <div className="space-y-2">
                          {customerDesigns.map((d, j) => (
                            <div key={d.id || j} className="flex items-center justify-between" style={{ padding: '8px 12px', background: '#fff', borderRadius: 8, border: '1px solid #ece8e0' }}>
                              <div className="flex items-center gap-3">
                                <PenTool size={14} className="text-[#b8960c]" />
                                <div>
                                  <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{d.name || 'Untitled'}</div>
                                  <div style={{ fontSize: 10, color: '#777' }}>
                                    {d.design_number || '--'} | {d.category || '--'} | <span suppressHydrationWarning>{d.created_at ? new Date(d.created_at).toLocaleDateString() : '--'}</span>
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center gap-3">
                                <span style={{ fontSize: 12, fontWeight: 700, color: '#b8960c' }}>{d.total != null ? `$${Number(d.total).toFixed(2)}` : '--'}</span>
                                <span className="status-pill" style={{
                                  fontSize: 10,
                                  background: d.status === 'complete' ? '#f0fdf4' : d.status === 'concept' ? '#f5f3ef' : '#eff6ff',
                                  color: d.status === 'complete' ? '#16a34a' : d.status === 'concept' ? '#888' : '#2563eb',
                                }}>
                                  {(d.status || 'concept').replace(/_/g, ' ')}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
