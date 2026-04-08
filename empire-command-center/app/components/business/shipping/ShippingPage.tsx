'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Truck, Search, Package, MapPin, ArrowRight, DollarSign, Calendar, Loader2 } from 'lucide-react';
import DataTable, { Column } from '../shared/DataTable';
import StatusBadge from '../shared/StatusBadge';
import EmptyState from '../shared/EmptyState';

import { API_BASE } from '../../../lib/api';

const SHIP_API = `${API_BASE}/shipping`;

type ShipTab = 'history' | 'rates' | 'track';

const SHIPPING_STATUS_MAP: Record<string, { bg: string; text: string }> = {
  delivered:     { bg: '#f0fdf4', text: '#22c55e' },
  in_transit:    { bg: '#eff6ff', text: '#2563eb' },
  shipped:       { bg: '#eff6ff', text: '#2563eb' },
  pending:       { bg: '#fffbeb', text: '#d97706' },
  label_created: { bg: '#faf5ff', text: '#7c3aed' },
  cancelled:     { bg: '#f0ede8', text: '#999' },
  exception:     { bg: '#fef2f2', text: '#dc2626' },
};

export default function ShippingPage() {
  const [tab, setTab] = useState<ShipTab>('history');

  return (
    <div className="max-w-5xl mx-auto" style={{ padding: '24px 36px' }}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-[#eff6ff] flex items-center justify-center">
          <Truck size={20} className="text-[#2563eb]" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[#1a1a1a]">Shipping</h1>
          <p className="text-[11px] text-[#999]">Labels, tracking, and rate calculations</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 mb-6 empire-card flat" style={{ padding: 4, width: 'fit-content' }}>
        {(['history', 'rates', 'track'] as ShipTab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`filter-tab ${tab === t ? 'active' : ''}`}
            style={{ textTransform: 'capitalize' }}
          >
            {t === 'rates' ? 'Rate Calculator' : t === 'track' ? 'Track Package' : 'History'}
          </button>
        ))}
      </div>

      {tab === 'history' && <HistoryTab />}
      {tab === 'rates' && <RateCalculatorTab />}
      {tab === 'track' && <TrackPackageTab />}
    </div>
  );
}

// ── History Tab ─────────────────────────────────────────────────────

function HistoryTab() {
  const [shipments, setShipments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${SHIP_API}/shipping/history`)
      .then(r => r.json())
      .then(data => setShipments(data.shipments || data || []))
      .catch(() => setShipments([]))
      .finally(() => setLoading(false));
  }, []);

  const columns: Column[] = [
    {
      key: 'tracking_number', label: 'Tracking #', sortable: true,
      render: (row: any) => <span className="font-mono text-xs">{row.tracking_number || '--'}</span>,
    },
    { key: 'carrier', label: 'Carrier', sortable: true },
    { key: 'service', label: 'Service', sortable: true },
    {
      key: 'status', label: 'Status', sortable: true,
      render: (row: any) => <StatusBadge status={row.status || 'pending'} colorMap={SHIPPING_STATUS_MAP} />,
    },
    {
      key: 'ship_date', label: 'Ship Date', sortable: true,
      render: (row: any) => (
        <span className="text-xs text-[#999]" suppressHydrationWarning>
          {row.ship_date ? new Date(row.ship_date).toLocaleDateString() : '--'}
        </span>
      ),
    },
    {
      key: 'delivery_date', label: 'Delivery Date', sortable: true,
      render: (row: any) => (
        <span className="text-xs text-[#999]" suppressHydrationWarning>
          {row.delivery_date ? new Date(row.delivery_date).toLocaleDateString() : '--'}
        </span>
      ),
    },
    {
      key: 'cost', label: 'Cost', sortable: true,
      render: (row: any) => (
        <span className="text-xs font-bold text-[#b8960c]">
          {row.cost != null ? `$${Number(row.cost).toFixed(2)}` : '--'}
        </span>
      ),
    },
  ];

  if (!loading && shipments.length === 0) {
    return (
      <EmptyState
        icon={<Package size={40} />}
        title="No shipping history"
        description="Shipping records will appear here once labels are created."
      />
    );
  }

  return <DataTable columns={columns} data={shipments} loading={loading} emptyMessage="No shipments found." />;
}

// ── Rate Calculator Tab ─────────────────────────────────────────────

function RateCalculatorTab() {
  const [form, setForm] = useState({
    origin_zip: '',
    destination_zip: '',
    weight: '',
    length: '',
    width: '',
    height: '',
  });
  const [rates, setRates] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState<string | null>(null);
  const [toast, setToast] = useState('');

  const handleChange = (key: string, val: string) => {
    setForm(prev => ({ ...prev, [key]: val }));
  };

  const getRates = async () => {
    if (!form.origin_zip || !form.destination_zip || !form.weight) {
      setError('Origin ZIP, Destination ZIP, and Weight are required.');
      return;
    }
    setLoading(true);
    setError('');
    setRates([]);
    try {
      const res = await fetch(`${SHIP_API}/shipping/rates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origin_zip: form.origin_zip,
          destination_zip: form.destination_zip,
          weight: parseFloat(form.weight),
          length: form.length ? parseFloat(form.length) : undefined,
          width: form.width ? parseFloat(form.width) : undefined,
          height: form.height ? parseFloat(form.height) : undefined,
        }),
      });
      if (!res.ok) throw new Error('Failed to get rates');
      const data = await res.json();
      setRates(data.rates || data || []);
    } catch {
      setError('Failed to fetch shipping rates. The service may be unavailable.');
    } finally {
      setLoading(false);
    }
  };

  const createLabel = async (rate: any) => {
    const rateId = rate.rate_id || rate.id || JSON.stringify(rate);
    setCreating(rateId);
    try {
      const res = await fetch(`${SHIP_API}/shipping/labels`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rate_id: rate.rate_id || rate.id,
          origin_zip: form.origin_zip,
          destination_zip: form.destination_zip,
          weight: parseFloat(form.weight),
          carrier: rate.carrier,
          service: rate.service,
        }),
      });
      if (!res.ok) throw new Error('Failed');
      setToast('Label created successfully!');
      setTimeout(() => setToast(''), 3000);
    } catch {
      setToast('Failed to create label');
      setTimeout(() => setToast(''), 3000);
    } finally {
      setCreating(null);
    }
  };

  const inputClass = "w-full px-3.5 py-2.5 text-sm border border-[#ece8e0] rounded-[14px] bg-[#faf9f7] outline-none focus:border-[#b8960c] transition-colors";

  return (
    <div>
      {/* Toast */}
      {toast && (
        <div className={`mb-4 px-4 py-2.5 rounded-xl text-sm font-medium ${toast.includes('Failed') ? 'bg-[#fef2f2] text-red-700' : 'bg-[#f0fdf4] text-[#22c55e]'}`}>
          {toast}
        </div>
      )}

      {/* Form */}
      <div className="empire-card flat" style={{ padding: 20, marginBottom: 24 }}>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="section-label" style={{ fontSize: 10 }}>Origin ZIP</label>
            <input type="text" value={form.origin_zip} onChange={e => handleChange('origin_zip', e.target.value)} className={inputClass} placeholder="e.g. 90210" />
          </div>
          <div>
            <label className="section-label" style={{ fontSize: 10 }}>Destination ZIP</label>
            <input type="text" value={form.destination_zip} onChange={e => handleChange('destination_zip', e.target.value)} className={inputClass} placeholder="e.g. 10001" />
          </div>
          <div>
            <label className="section-label" style={{ fontSize: 10 }}>Weight (lbs)</label>
            <input type="number" value={form.weight} onChange={e => handleChange('weight', e.target.value)} className={inputClass} placeholder="e.g. 5" />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="section-label" style={{ fontSize: 10 }}>Length (in)</label>
            <input type="number" value={form.length} onChange={e => handleChange('length', e.target.value)} className={inputClass} placeholder="Optional" />
          </div>
          <div>
            <label className="section-label" style={{ fontSize: 10 }}>Width (in)</label>
            <input type="number" value={form.width} onChange={e => handleChange('width', e.target.value)} className={inputClass} placeholder="Optional" />
          </div>
          <div>
            <label className="section-label" style={{ fontSize: 10 }}>Height (in)</label>
            <input type="number" value={form.height} onChange={e => handleChange('height', e.target.value)} className={inputClass} placeholder="Optional" />
          </div>
        </div>
        {error && <p className="text-xs text-red-600 mb-3">{error}</p>}
        <button
          onClick={getRates}
          disabled={loading}
          className="flex items-center gap-2 px-5 py-2.5 text-sm font-bold text-white bg-[#b8960c] rounded-xl hover:bg-[#a68500] disabled:opacity-50 transition-colors cursor-pointer"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <DollarSign size={14} />}
          {loading ? 'Getting Rates...' : 'Get Rates'}
        </button>
      </div>

      {/* Rate Results */}
      {rates.length > 0 && (
        <div className="grid grid-cols-2 gap-4">
          {rates.map((rate, i) => (
            <div key={i} className="empire-card" style={{ padding: 20 }}>
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className="text-sm font-bold text-[#1a1a1a]">{rate.carrier || 'Carrier'}</div>
                  <div className="text-[11px] text-[#999]">{rate.service || 'Standard'}</div>
                </div>
                <div className="text-right">
                  <div className="kpi-value gold">${Number(rate.rate || rate.price || 0).toFixed(2)}</div>
                  <div className="text-[11px] text-[#999]">{rate.estimated_days || rate.days || '?'} days</div>
                </div>
              </div>
              <button
                onClick={() => createLabel(rate)}
                disabled={creating === (rate.rate_id || rate.id || JSON.stringify(rate))}
                className="w-full mt-1 px-3 py-2.5 text-xs font-bold text-white bg-[#22c55e] rounded-xl hover:bg-[#16a34a] disabled:opacity-50 transition-colors cursor-pointer"
              >
                {creating === (rate.rate_id || rate.id || JSON.stringify(rate)) ? 'Creating...' : 'Create Label'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Track Package Tab ───────────────────────────────────────────────

function TrackPackageTab() {
  const [trackingNumber, setTrackingNumber] = useState('');
  const [tracking, setTracking] = useState(false);
  const [events, setEvents] = useState<any[] | null>(null);
  const [error, setError] = useState('');

  const handleTrack = async () => {
    if (!trackingNumber.trim()) return;
    setTracking(true);
    setError('');
    setEvents(null);
    try {
      const res = await fetch(`${SHIP_API}/shipping/track/${encodeURIComponent(trackingNumber)}`);
      if (!res.ok) throw new Error('Not found');
      const data = await res.json();
      setEvents(data.events || data.tracking_events || []);
    } catch {
      setError('No tracking info found for this number.');
    } finally {
      setTracking(false);
    }
  };

  return (
    <div>
      {/* Search */}
      <div className="empire-card flat" style={{ padding: 20, marginBottom: 24 }}>
        <label className="section-label" style={{ fontSize: 10 }}>Tracking Number</label>
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={trackingNumber}
            onChange={e => setTrackingNumber(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleTrack()}
            className="flex-1 px-3.5 py-2.5 text-sm border border-[#ece8e0] rounded-[14px] bg-[#faf9f7] outline-none focus:border-[#b8960c] transition-colors"
            placeholder="Enter tracking number..."
          />
          <button
            onClick={handleTrack}
            disabled={tracking || !trackingNumber.trim()}
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-bold text-white bg-[#2563eb] rounded-xl hover:bg-[#1d4ed8] disabled:opacity-50 transition-colors cursor-pointer"
          >
            {tracking ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
            Track
          </button>
        </div>
        {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
      </div>

      {/* Timeline */}
      {events !== null && (
        events.length === 0 ? (
          <EmptyState
            icon={<MapPin size={40} />}
            title="No tracking info found"
            description="This tracking number has no events yet."
          />
        ) : (
          <div className="empire-card flat" style={{ padding: 20 }}>
            <div className="relative pl-6">
              {/* Vertical line */}
              <div className="absolute left-[9px] top-2 bottom-2 w-px bg-[#ece8e0]" />
              <div className="space-y-4">
                {events.map((evt, i) => (
                  <div key={i} className="relative flex items-start gap-3">
                    <div className={`absolute left-[-15px] w-[18px] h-[18px] rounded-full border-2 flex items-center justify-center ${
                      i === 0 ? 'bg-[#2563eb] border-[#2563eb]' : 'bg-[#faf9f7] border-[#ece8e0]'
                    }`}>
                      {i === 0 && <div className="w-2 h-2 rounded-full bg-white" />}
                    </div>
                    <div className="ml-2">
                      <div className="text-sm font-medium text-[#1a1a1a]">{evt.status || evt.description || 'Event'}</div>
                      <div className="text-xs text-[#999]">{evt.location || ''}</div>
                      <div className="text-[10px] text-[#bbb] font-mono" suppressHydrationWarning>
                        {evt.date || evt.timestamp ? new Date(evt.date || evt.timestamp).toLocaleString() : ''}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )
      )}
    </div>
  );
}
