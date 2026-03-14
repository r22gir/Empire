'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  Upload, Package, Users, Truck, Check, X, ChevronDown, ChevronRight,
  AlertCircle, Loader2, CheckCircle2, Search, ToggleLeft, ToggleRight
} from 'lucide-react';
import { API } from '../../../lib/api';

interface QBItem {
  name: string;
  sku: string;
  category: string;
  description: string;
  sell_price: number;
  cost_per_unit: number;
  vendor: string;
  unit: string;
  item_type: string;
  exists: boolean;
}

interface QBVendor {
  name: string;
  email: string;
  phone: string;
  address: string;
  contact: string;
  account_number: string;
  exists: boolean;
}

interface QBCustomer {
  name: string;
  email: string;
  phone: string;
  address: string;
  company: string;
  type: string;
  source: string;
  notes: string;
  balance: number;
  exists: boolean;
}

type Tab = 'items' | 'vendors' | 'customers';

function fmt(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(n);
}

export default function QBImportPreview() {
  const [items, setItems] = useState<QBItem[]>([]);
  const [vendors, setVendors] = useState<QBVendor[]>([]);
  const [customers, setCustomers] = useState<QBCustomer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selection state — names
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [selectedVendors, setSelectedVendors] = useState<Set<string>>(new Set());
  const [selectedCustomers, setSelectedCustomers] = useState<Set<string>>(new Set());

  // UI state
  const [tab, setTab] = useState<Tab>('items');
  const [search, setSearch] = useState('');
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set());
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);

  useEffect(() => {
    fetchPreview();
  }, []);

  const fetchPreview = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/inventory/qb-import/preview`);
      if (!res.ok) throw new Error(`Failed to load preview (${res.status})`);
      const data = await res.json();

      setItems(data.items || []);
      setVendors(data.vendors || []);
      setCustomers(data.customers || []);

      // Pre-select all non-existing entries
      setSelectedItems(new Set((data.items || []).filter((i: QBItem) => !i.exists).map((i: QBItem) => i.name)));
      setSelectedVendors(new Set((data.vendors || []).filter((v: QBVendor) => !v.exists).map((v: QBVendor) => v.name)));
      setSelectedCustomers(new Set((data.customers || []).filter((c: QBCustomer) => !c.exists).map((c: QBCustomer) => c.name)));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Group items by category
  const itemsByCategory = useMemo(() => {
    const map: Record<string, QBItem[]> = {};
    for (const item of items) {
      if (!map[item.category]) map[item.category] = [];
      map[item.category].push(item);
    }
    return map;
  }, [items]);

  const sortedCategories = useMemo(() =>
    Object.keys(itemsByCategory).sort((a, b) => itemsByCategory[b].length - itemsByCategory[a].length),
    [itemsByCategory]
  );

  // Filter
  const q = search.toLowerCase();
  const filteredCategories = sortedCategories.filter(cat => {
    if (!q) return true;
    if (cat.toLowerCase().includes(q)) return true;
    return itemsByCategory[cat].some(i => i.name.toLowerCase().includes(q) || i.description?.toLowerCase().includes(q));
  });
  const filteredVendors = vendors.filter(v => !q || v.name.toLowerCase().includes(q) || v.phone?.includes(q));
  const filteredCustomers = customers.filter(c => !q || c.name.toLowerCase().includes(q) || c.phone?.includes(q) || c.type?.includes(q));

  // Toggle helpers
  const toggle = (set: Set<string>, setFn: (s: Set<string>) => void, name: string) => {
    const next = new Set(set);
    if (next.has(name)) next.delete(name); else next.add(name);
    setFn(next);
  };

  const toggleCategory = (cat: string) => {
    const catItems = itemsByCategory[cat] || [];
    const allSelected = catItems.every(i => selectedItems.has(i.name) || i.exists);
    const next = new Set(selectedItems);
    catItems.forEach(i => {
      if (i.exists) return;
      if (allSelected) next.delete(i.name); else next.add(i.name);
    });
    setSelectedItems(next);
  };

  const selectAllTab = () => {
    if (tab === 'items') setSelectedItems(new Set(items.filter(i => !i.exists).map(i => i.name)));
    if (tab === 'vendors') setSelectedVendors(new Set(vendors.filter(v => !v.exists).map(v => v.name)));
    if (tab === 'customers') setSelectedCustomers(new Set(customers.filter(c => !c.exists).map(c => c.name)));
  };

  const deselectAllTab = () => {
    if (tab === 'items') setSelectedItems(new Set());
    if (tab === 'vendors') setSelectedVendors(new Set());
    if (tab === 'customers') setSelectedCustomers(new Set());
  };

  const expandToggle = (cat: string) => {
    const next = new Set(expandedCats);
    if (next.has(cat)) next.delete(cat); else next.add(cat);
    setExpandedCats(next);
  };

  const handleImport = async () => {
    setImporting(true);
    setError(null);
    try {
      const res = await fetch(`${API}/inventory/qb-import/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: Array.from(selectedItems),
          vendors: Array.from(selectedVendors),
          customers: Array.from(selectedCustomers),
        }),
      });
      if (!res.ok) throw new Error(`Import failed (${res.status})`);
      const result = await res.json();
      setImportResult(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center py-20">
        <Loader2 size={28} className="text-[#16a34a] animate-spin" />
        <span className="ml-3 text-[#555] text-base">Parsing QuickBooks data...</span>
      </div>
    );
  }

  if (importResult) {
    return (
      <div className="max-w-3xl mx-auto" style={{ padding: '32px 36px' }}>
        <div className="empire-card flat" style={{ padding: 32, textAlign: 'center' }}>
          <CheckCircle2 size={48} className="text-[#16a34a] mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-[#1a1a1a] mb-4">Import Complete</h2>
          <div className="grid grid-cols-3 gap-6 mb-6">
            <div className="empire-card flat" style={{ padding: 16 }}>
              <div className="text-3xl font-bold text-[#16a34a]">{importResult.items_imported}</div>
              <div className="text-sm text-[#999]">Items</div>
            </div>
            <div className="empire-card flat" style={{ padding: 16 }}>
              <div className="text-3xl font-bold text-[#16a34a]">{importResult.vendors_imported}</div>
              <div className="text-sm text-[#999]">Vendors</div>
            </div>
            <div className="empire-card flat" style={{ padding: 16 }}>
              <div className="text-3xl font-bold text-[#16a34a]">{importResult.customers_imported}</div>
              <div className="text-sm text-[#999]">Customers</div>
            </div>
          </div>
          {importResult.errors?.length > 0 && (
            <div className="text-left mt-4 p-4 bg-red-50 border border-red-200 rounded-xl">
              <p className="text-sm font-bold text-red-700 mb-2">Errors ({importResult.errors.length}):</p>
              {importResult.errors.map((e: string, i: number) => (
                <p key={i} className="text-sm text-red-600">{e}</p>
              ))}
            </div>
          )}
          <button
            onClick={() => { setImportResult(null); fetchPreview(); }}
            className="mt-6 px-6 py-3 text-sm font-bold text-white bg-[#16a34a] hover:bg-[#15803d] rounded-xl transition-colors cursor-pointer"
          >
            Back to Preview
          </button>
        </div>
      </div>
    );
  }

  const totalSelected = selectedItems.size + selectedVendors.size + selectedCustomers.size;

  return (
    <div className="max-w-5xl mx-auto" style={{ padding: '24px 36px' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
            <Upload size={20} className="text-[#b8960c]" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#1a1a1a]">QuickBooks Import</h1>
            <p className="text-sm text-[#999]">Review and select what to import into Workroom</p>
          </div>
        </div>
        <button
          onClick={handleImport}
          disabled={importing || totalSelected === 0}
          className="flex items-center gap-2 px-6 py-3 text-sm font-bold text-white bg-[#16a34a] hover:bg-[#15803d] rounded-xl transition-colors disabled:opacity-50 cursor-pointer"
        >
          {importing ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
          {importing ? 'Importing...' : `Import ${totalSelected} Selected`}
        </button>
      </div>

      {error && (
        <div className="mb-4 empire-card flat" style={{ padding: 12, borderColor: '#fca5a5', background: '#fef2f2' }}>
          <div className="flex items-center gap-2 text-sm text-red-700">
            <AlertCircle size={16} /> {error}
          </div>
        </div>
      )}

      {/* Stats bar */}
      <div className="grid grid-cols-3 gap-4 mb-5">
        <div
          onClick={() => setTab('items')}
          className={`empire-card flat cursor-pointer transition-all ${tab === 'items' ? 'ring-2 ring-[#16a34a]' : ''}`}
          style={{ padding: '14px 16px' }}
        >
          <div className="flex items-center gap-2 mb-1">
            <Package size={16} className="text-[#16a34a]" />
            <span className="text-sm font-bold text-[#1a1a1a]">Items & Services</span>
          </div>
          <div className="text-2xl font-bold text-[#16a34a]">{selectedItems.size}<span className="text-sm font-normal text-[#999]"> / {items.filter(i => !i.exists).length} new</span></div>
          <div className="text-xs text-[#999]">{items.filter(i => i.exists).length} already exist</div>
        </div>
        <div
          onClick={() => setTab('vendors')}
          className={`empire-card flat cursor-pointer transition-all ${tab === 'vendors' ? 'ring-2 ring-[#b8960c]' : ''}`}
          style={{ padding: '14px 16px' }}
        >
          <div className="flex items-center gap-2 mb-1">
            <Truck size={16} className="text-[#b8960c]" />
            <span className="text-sm font-bold text-[#1a1a1a]">Vendors</span>
          </div>
          <div className="text-2xl font-bold text-[#b8960c]">{selectedVendors.size}<span className="text-sm font-normal text-[#999]"> / {vendors.filter(v => !v.exists).length} new</span></div>
          <div className="text-xs text-[#999]">{vendors.filter(v => v.exists).length} already exist</div>
        </div>
        <div
          onClick={() => setTab('customers')}
          className={`empire-card flat cursor-pointer transition-all ${tab === 'customers' ? 'ring-2 ring-[#7c3aed]' : ''}`}
          style={{ padding: '14px 16px' }}
        >
          <div className="flex items-center gap-2 mb-1">
            <Users size={16} className="text-[#7c3aed]" />
            <span className="text-sm font-bold text-[#1a1a1a]">Customers</span>
          </div>
          <div className="text-2xl font-bold text-[#7c3aed]">{selectedCustomers.size}<span className="text-sm font-normal text-[#999]"> / {customers.filter(c => !c.exists).length} new</span></div>
          <div className="text-xs text-[#999]">{customers.filter(c => c.exists).length} already exist</div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1 relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#999]" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder={`Search ${tab}...`}
            className="w-full pl-9 pr-3 py-2.5 text-sm border border-[#ece8e0] rounded-xl bg-[#faf9f7] outline-none focus:border-[#b8960c] transition-colors"
          />
        </div>
        <button onClick={selectAllTab} className="px-3 py-2.5 text-xs font-bold text-[#16a34a] bg-[#dcfce7] hover:bg-[#bbf7d0] rounded-xl transition-colors cursor-pointer">
          Select All
        </button>
        <button onClick={deselectAllTab} className="px-3 py-2.5 text-xs font-bold text-[#dc2626] bg-[#fef2f2] hover:bg-[#fee2e2] rounded-xl transition-colors cursor-pointer">
          Deselect All
        </button>
      </div>

      {/* Content */}
      <div className="empire-card flat" style={{ padding: 0, overflow: 'hidden' }}>
        {tab === 'items' && (
          <div>
            {filteredCategories.map(cat => {
              const catItems = itemsByCategory[cat].filter(i => !q || i.name.toLowerCase().includes(q) || i.description?.toLowerCase().includes(q) || cat.toLowerCase().includes(q));
              const expanded = expandedCats.has(cat);
              const newCount = catItems.filter(i => !i.exists).length;
              const selectedCount = catItems.filter(i => selectedItems.has(i.name)).length;
              const allSelected = catItems.filter(i => !i.exists).every(i => selectedItems.has(i.name));

              return (
                <div key={cat} className="border-b border-[#ece8e0] last:border-b-0">
                  {/* Category header */}
                  <div
                    className="flex items-center gap-3 px-5 py-3.5 hover:bg-[#faf9f7] cursor-pointer transition-colors"
                    onClick={() => expandToggle(cat)}
                  >
                    {expanded ? <ChevronDown size={16} className="text-[#999]" /> : <ChevronRight size={16} className="text-[#999]" />}
                    <div className="flex-1">
                      <span className="font-bold text-[#1a1a1a] text-sm">{cat}</span>
                      <span className="ml-2 text-xs text-[#999]">{catItems.length} items ({newCount} new)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {selectedCount > 0 && (
                        <span className="text-xs font-bold text-[#16a34a] bg-[#dcfce7] px-2 py-0.5 rounded-full">{selectedCount} selected</span>
                      )}
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleCategory(cat); }}
                        className={`p-1.5 rounded-lg transition-colors cursor-pointer ${allSelected && newCount > 0 ? 'bg-[#16a34a] text-white' : 'bg-[#f5f3ef] text-[#999] hover:text-[#555]'}`}
                        title={allSelected ? 'Deselect all in category' : 'Select all in category'}
                      >
                        <Check size={14} />
                      </button>
                    </div>
                  </div>
                  {/* Items */}
                  {expanded && (
                    <div className="bg-[#faf9f7]">
                      {catItems.map(item => (
                        <div
                          key={item.name}
                          className={`flex items-center gap-3 px-5 py-2.5 pl-12 border-t border-[#f0ece4] transition-colors ${
                            item.exists ? 'opacity-40' : 'hover:bg-[#f5f3ef] cursor-pointer'
                          }`}
                          onClick={() => !item.exists && toggle(selectedItems, setSelectedItems, item.name)}
                        >
                          {/* Checkbox */}
                          <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                            item.exists ? 'border-[#ddd] bg-[#eee]' :
                            selectedItems.has(item.name) ? 'border-[#16a34a] bg-[#16a34a]' : 'border-[#ccc] bg-white'
                          }`}>
                            {(selectedItems.has(item.name) || item.exists) && <Check size={12} className="text-white" />}
                          </div>
                          {/* Info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-[#1a1a1a] truncate">{item.name}</span>
                              <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                                item.item_type === 'service' ? 'bg-blue-50 text-blue-600' : 'bg-amber-50 text-amber-700'
                              }`}>
                                {item.item_type === 'service' ? 'SVC' : 'PRD'}
                              </span>
                              {item.exists && <span className="text-[10px] font-bold text-[#999] bg-[#f0ece4] px-1.5 py-0.5 rounded">EXISTS</span>}
                            </div>
                            {item.description && <div className="text-xs text-[#999] truncate">{item.description}</div>}
                          </div>
                          {/* Price */}
                          <div className="text-right flex-shrink-0" style={{ minWidth: 80 }}>
                            {item.sell_price > 0 ? (
                              <span className="text-sm font-bold text-[#16a34a]">{fmt(item.sell_price)}</span>
                            ) : (
                              <span className="text-xs text-[#ccc]">no price</span>
                            )}
                            {item.cost_per_unit > 0 && (
                              <div className="text-[10px] text-[#999]">cost {fmt(item.cost_per_unit)}</div>
                            )}
                          </div>
                          {/* Vendor */}
                          {item.vendor && (
                            <span className="text-xs text-[#999] flex-shrink-0" style={{ maxWidth: 100 }} title={item.vendor}>
                              {item.vendor.length > 15 ? item.vendor.slice(0, 15) + '...' : item.vendor}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {tab === 'vendors' && (
          <div>
            {filteredVendors.map(v => (
              <div
                key={v.name}
                className={`flex items-center gap-3 px-5 py-3.5 border-b border-[#ece8e0] last:border-b-0 transition-colors ${
                  v.exists ? 'opacity-40' : 'hover:bg-[#faf9f7] cursor-pointer'
                }`}
                onClick={() => !v.exists && toggle(selectedVendors, setSelectedVendors, v.name)}
              >
                <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                  v.exists ? 'border-[#ddd] bg-[#eee]' :
                  selectedVendors.has(v.name) ? 'border-[#b8960c] bg-[#b8960c]' : 'border-[#ccc] bg-white'
                }`}>
                  {(selectedVendors.has(v.name) || v.exists) && <Check size={12} className="text-white" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-[#1a1a1a]">{v.name}</span>
                    {v.exists && <span className="text-[10px] font-bold text-[#999] bg-[#f0ece4] px-1.5 py-0.5 rounded">EXISTS</span>}
                  </div>
                  <div className="text-xs text-[#999]">
                    {[v.phone, v.email, v.address].filter(Boolean).join(' · ') || 'No contact info'}
                  </div>
                </div>
                {v.account_number && <span className="text-xs text-[#999]">Acct: {v.account_number}</span>}
              </div>
            ))}
          </div>
        )}

        {tab === 'customers' && (
          <div>
            {filteredCustomers.map(c => (
              <div
                key={c.name}
                className={`flex items-center gap-3 px-5 py-3.5 border-b border-[#ece8e0] last:border-b-0 transition-colors ${
                  c.exists ? 'opacity-40' : 'hover:bg-[#faf9f7] cursor-pointer'
                }`}
                onClick={() => !c.exists && toggle(selectedCustomers, setSelectedCustomers, c.name)}
              >
                <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                  c.exists ? 'border-[#ddd] bg-[#eee]' :
                  selectedCustomers.has(c.name) ? 'border-[#7c3aed] bg-[#7c3aed]' : 'border-[#ccc] bg-white'
                }`}>
                  {(selectedCustomers.has(c.name) || c.exists) && <Check size={12} className="text-white" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-[#1a1a1a]">{c.name}</span>
                    <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                      c.type === 'designer' ? 'bg-purple-50 text-purple-600' :
                      c.type === 'commercial' ? 'bg-blue-50 text-blue-600' :
                      c.type === 'contractor' ? 'bg-orange-50 text-orange-600' :
                      'bg-gray-50 text-gray-500'
                    }`}>
                      {c.type}
                    </span>
                    {c.exists && <span className="text-[10px] font-bold text-[#999] bg-[#f0ece4] px-1.5 py-0.5 rounded">EXISTS</span>}
                  </div>
                  <div className="text-xs text-[#999]">
                    {[c.phone, c.email, c.address].filter(Boolean).join(' · ') || 'No contact info'}
                  </div>
                </div>
                {c.balance > 0 && (
                  <span className="text-sm font-bold text-[#dc2626]">{fmt(c.balance)}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Bottom import bar */}
      <div className="mt-6 flex items-center justify-between">
        <div className="text-sm text-[#999]">
          {selectedItems.size} items + {selectedVendors.size} vendors + {selectedCustomers.size} customers = <span className="font-bold text-[#1a1a1a]">{totalSelected} total</span>
        </div>
        <button
          onClick={handleImport}
          disabled={importing || totalSelected === 0}
          className="flex items-center gap-2 px-8 py-3 text-base font-bold text-white bg-[#16a34a] hover:bg-[#15803d] rounded-xl transition-colors disabled:opacity-50 cursor-pointer"
        >
          {importing ? <Loader2 size={18} className="animate-spin" /> : <Upload size={18} />}
          {importing ? 'Importing...' : `Import ${totalSelected} Selected`}
        </button>
      </div>
    </div>
  );
}
