'use client';
import { useState } from 'react';
import { API_URL } from '@/lib/api';
import { Plus, Trash2, FileText, Send, Calculator, X } from 'lucide-react';

interface LineItem {
  description: string;
  quantity: number;
  unit: string;
  rate: number;
  amount: number;
  category: 'labor' | 'materials' | 'other';
}

interface QuoteData {
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  customer_address: string;
  project_name: string;
  project_description: string;
  line_items: LineItem[];
  measurements: {
    width: number | null;
    height: number | null;
    depth: number | null;
    unit: string;
    room: string;
    window_type: string;
    notes: string;
  };
  tax_rate: number;
  discount_amount: number;
  deposit: {
    deposit_percent: number;
    deposit_amount: number;
    deposit_due: string;
    balance_due: string;
  };
  terms: string;
  valid_days: number;
  install_date: string;
  notes: string;
  business_name: string;
  business_logo_url: string;
}

const EMPTY_ITEM: LineItem = { description: '', quantity: 1, unit: 'ea', rate: 0, amount: 0, category: 'labor' };

const UNITS = ['ea', 'hr', 'sqft', 'width', 'fixture', 'linear ft', 'set'];

interface Props {
  onClose: () => void;
}

export default function QuoteBuilder({ onClose }: Props) {
  const [saving, setSaving] = useState(false);
  const [savedQuote, setSavedQuote] = useState<{ id: string; quote_number: string } | null>(null);
  const [activeTab, setActiveTab] = useState<'customer' | 'items' | 'details'>('customer');

  const [data, setData] = useState<QuoteData>({
    customer_name: '',
    customer_email: '',
    customer_phone: '',
    customer_address: '',
    project_name: '',
    project_description: '',
    line_items: [{ ...EMPTY_ITEM }],
    measurements: { width: null, height: null, depth: null, unit: 'in', room: '', window_type: '', notes: '' },
    tax_rate: 0.08,
    discount_amount: 0,
    deposit: { deposit_percent: 50, deposit_amount: 0, deposit_due: '', balance_due: '' },
    terms: '50% deposit required to begin work. Balance due upon completion. Payment by check, card, or Zelle.',
    valid_days: 30,
    install_date: '',
    notes: '',
    business_name: '',
    business_logo_url: '',
  });

  // ── Computed financials ──────────────────────────────────
  const subtotal = data.line_items.reduce((s, i) => s + i.quantity * i.rate, 0);
  const taxAmount = subtotal * data.tax_rate;
  const total = subtotal + taxAmount - data.discount_amount;
  const depositAmount = total * data.deposit.deposit_percent / 100;

  // ── Item management ──────────────────────────────────────
  const updateItem = (idx: number, field: keyof LineItem, value: string | number) => {
    const items = [...data.line_items];
    (items[idx] as unknown as Record<string, unknown>)[field] = value;
    items[idx].amount = items[idx].quantity * items[idx].rate;
    setData({ ...data, line_items: items });
  };

  const addItem = () => setData({ ...data, line_items: [...data.line_items, { ...EMPTY_ITEM }] });
  const removeItem = (idx: number) => {
    if (data.line_items.length <= 1) return;
    setData({ ...data, line_items: data.line_items.filter((_, i) => i !== idx) });
  };

  // ── Save quote ───────────────────────────────────────────
  const saveQuote = async () => {
    if (!data.customer_name.trim()) return;
    setSaving(true);
    try {
      const payload = {
        ...data,
        subtotal,
        tax_amount: taxAmount,
        total,
        deposit: { ...data.deposit, deposit_amount: depositAmount },
      };
      const res = await fetch(API_URL + '/quotes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await res.json();
      if (result.status === 'created') {
        setSavedQuote({ id: result.quote.id, quote_number: result.quote.quote_number });
      }
    } catch { /* */ }
    finally { setSaving(false); }
  };

  // ── Generate PDF ─────────────────────────────────────────
  const generatePdf = async () => {
    if (!savedQuote) return;
    try {
      const res = await fetch(API_URL + `/quotes/${savedQuote.id}/pdf`, { method: 'POST' });
      const result = await res.json();
      if (result.html) {
        const win = window.open('', '_blank');
        if (win) { win.document.write(result.html); win.document.close(); }
      }
    } catch { /* */ }
  };

  const inputStyle = {
    background: 'var(--raised)',
    border: '1px solid var(--border)',
    color: 'var(--text-primary)',
  };

  const TABS = [
    { key: 'customer' as const, label: 'Customer' },
    { key: 'items' as const, label: 'Line Items' },
    { key: 'details' as const, label: 'Details' },
  ];

  const laborTotal = data.line_items.filter(i => i.category === 'labor').reduce((s, i) => s + i.quantity * i.rate, 0);
  const materialsTotal = data.line_items.filter(i => i.category === 'materials').reduce((s, i) => s + i.quantity * i.rate, 0);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2">
          <Calculator className="w-4 h-4" style={{ color: 'var(--gold)' }} />
          <h2 className="text-sm font-semibold" style={{ color: 'var(--gold)' }}>
            {savedQuote ? savedQuote.quote_number : 'New Estimate'}
          </h2>
        </div>
        <div className="flex items-center gap-2">
          {savedQuote && (
            <button onClick={generatePdf} className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition"
              style={{ background: 'var(--surface)', color: 'var(--purple)', border: '1px solid var(--purple-border)' }}>
              <FileText className="w-3 h-3" /> PDF
            </button>
          )}
          <button onClick={saveQuote} disabled={saving || !data.customer_name.trim()}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition"
            style={{
              background: data.customer_name.trim() ? 'var(--gold)' : 'var(--elevated)',
              color: data.customer_name.trim() ? '#0a0a0a' : 'var(--text-muted)',
            }}>
            <Send className="w-3 h-3" /> {saving ? 'Saving…' : savedQuote ? 'Update' : 'Save'}
          </button>
          <button onClick={onClose} className="p-1" style={{ color: 'var(--text-muted)' }}>
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 px-3 pt-2">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className="px-3 py-1 rounded-t-lg text-[11px] font-medium transition"
            style={{
              background: activeTab === t.key ? 'var(--raised)' : 'transparent',
              color: activeTab === t.key ? 'var(--gold)' : 'var(--text-muted)',
              borderBottom: activeTab === t.key ? '2px solid var(--gold)' : '2px solid transparent',
            }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">

        {/* ── Customer Tab ─────────────────────────────────── */}
        {activeTab === 'customer' && (
          <>
            <div className="grid grid-cols-2 gap-2">
              <input placeholder="Customer name *" value={data.customer_name}
                onChange={e => setData({ ...data, customer_name: e.target.value })}
                className="rounded-lg px-3 py-2 text-xs outline-none" style={inputStyle} />
              <input placeholder="Email" value={data.customer_email}
                onChange={e => setData({ ...data, customer_email: e.target.value })}
                className="rounded-lg px-3 py-2 text-xs outline-none" style={inputStyle} />
              <input placeholder="Phone" value={data.customer_phone}
                onChange={e => setData({ ...data, customer_phone: e.target.value })}
                className="rounded-lg px-3 py-2 text-xs outline-none" style={inputStyle} />
              <input placeholder="Project name" value={data.project_name}
                onChange={e => setData({ ...data, project_name: e.target.value })}
                className="rounded-lg px-3 py-2 text-xs outline-none" style={inputStyle} />
            </div>
            <textarea placeholder="Address" value={data.customer_address}
              onChange={e => setData({ ...data, customer_address: e.target.value })}
              className="w-full rounded-lg px-3 py-2 text-xs outline-none resize-none" style={inputStyle} rows={2} />
            <textarea placeholder="Project description" value={data.project_description}
              onChange={e => setData({ ...data, project_description: e.target.value })}
              className="w-full rounded-lg px-3 py-2 text-xs outline-none resize-none" style={inputStyle} rows={2} />

            {/* Measurements */}
            <div className="rounded-xl p-3" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
              <p className="text-[10px] font-semibold mb-2" style={{ color: 'var(--text-muted)' }}>MEASUREMENTS</p>
              <div className="grid grid-cols-4 gap-2">
                <input type="number" placeholder="Width" value={data.measurements.width ?? ''}
                  onChange={e => setData({ ...data, measurements: { ...data.measurements, width: e.target.value ? parseFloat(e.target.value) : null } })}
                  className="rounded-lg px-2 py-1.5 text-xs outline-none" style={inputStyle} />
                <input type="number" placeholder="Height" value={data.measurements.height ?? ''}
                  onChange={e => setData({ ...data, measurements: { ...data.measurements, height: e.target.value ? parseFloat(e.target.value) : null } })}
                  className="rounded-lg px-2 py-1.5 text-xs outline-none" style={inputStyle} />
                <input type="number" placeholder="Depth" value={data.measurements.depth ?? ''}
                  onChange={e => setData({ ...data, measurements: { ...data.measurements, depth: e.target.value ? parseFloat(e.target.value) : null } })}
                  className="rounded-lg px-2 py-1.5 text-xs outline-none" style={inputStyle} />
                <select value={data.measurements.unit}
                  onChange={e => setData({ ...data, measurements: { ...data.measurements, unit: e.target.value } })}
                  className="rounded-lg px-2 py-1.5 text-xs outline-none cursor-pointer" style={inputStyle}>
                  <option value="in">inches</option>
                  <option value="ft">feet</option>
                  <option value="cm">cm</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-2 mt-2">
                <input placeholder="Room" value={data.measurements.room}
                  onChange={e => setData({ ...data, measurements: { ...data.measurements, room: e.target.value } })}
                  className="rounded-lg px-2 py-1.5 text-xs outline-none" style={inputStyle} />
                <input placeholder="Window type" value={data.measurements.window_type}
                  onChange={e => setData({ ...data, measurements: { ...data.measurements, window_type: e.target.value } })}
                  className="rounded-lg px-2 py-1.5 text-xs outline-none" style={inputStyle} />
              </div>
            </div>
          </>
        )}

        {/* ── Line Items Tab ───────────────────────────────── */}
        {activeTab === 'items' && (
          <>
            {/* Header */}
            <div className="grid gap-1.5 text-[9px] font-semibold" style={{ color: 'var(--text-muted)', gridTemplateColumns: '1fr 60px 70px 70px 80px 70px 28px' }}>
              <span>Description</span><span>Qty</span><span>Unit</span><span>Rate</span><span>Amount</span><span>Type</span><span />
            </div>

            {data.line_items.map((item, idx) => (
              <div key={idx} className="grid gap-1.5 items-center" style={{ gridTemplateColumns: '1fr 60px 70px 70px 80px 70px 28px' }}>
                <input placeholder="Description" value={item.description}
                  onChange={e => updateItem(idx, 'description', e.target.value)}
                  className="rounded-lg px-2 py-1.5 text-xs outline-none" style={inputStyle} />
                <input type="number" value={item.quantity} min={0} step={0.5}
                  onChange={e => updateItem(idx, 'quantity', parseFloat(e.target.value) || 0)}
                  className="rounded-lg px-2 py-1.5 text-xs outline-none text-center" style={inputStyle} />
                <select value={item.unit} onChange={e => updateItem(idx, 'unit', e.target.value)}
                  className="rounded-lg px-1 py-1.5 text-xs outline-none cursor-pointer" style={inputStyle}>
                  {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                </select>
                <input type="number" value={item.rate} min={0} step={0.01}
                  onChange={e => updateItem(idx, 'rate', parseFloat(e.target.value) || 0)}
                  className="rounded-lg px-2 py-1.5 text-xs outline-none text-right" style={inputStyle} />
                <span className="text-xs text-right font-mono px-2" style={{ color: 'var(--gold)' }}>
                  ${(item.quantity * item.rate).toFixed(2)}
                </span>
                <select value={item.category} onChange={e => updateItem(idx, 'category', e.target.value)}
                  className="rounded-lg px-1 py-1.5 text-[10px] outline-none cursor-pointer" style={inputStyle}>
                  <option value="labor">Labor</option>
                  <option value="materials">Material</option>
                  <option value="other">Other</option>
                </select>
                <button onClick={() => removeItem(idx)} className="p-1 rounded" style={{ color: 'var(--text-muted)' }}>
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}

            <button onClick={addItem}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-medium transition"
              style={{ background: 'var(--raised)', color: 'var(--gold)', border: '1px solid var(--gold-border)' }}>
              <Plus className="w-3 h-3" /> Add Item
            </button>

            {/* Breakdown */}
            <div className="rounded-xl p-3 space-y-1" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
              <div className="flex justify-between text-[11px]">
                <span style={{ color: 'var(--text-muted)' }}>Labor</span>
                <span className="font-mono" style={{ color: 'var(--text-primary)' }}>${laborTotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-[11px]">
                <span style={{ color: 'var(--text-muted)' }}>Materials</span>
                <span className="font-mono" style={{ color: 'var(--text-primary)' }}>${materialsTotal.toFixed(2)}</span>
              </div>
              <div className="h-px my-1" style={{ background: 'var(--border)' }} />
              <div className="flex justify-between text-[11px]">
                <span style={{ color: 'var(--text-muted)' }}>Subtotal</span>
                <span className="font-mono" style={{ color: 'var(--text-primary)' }}>${subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-[11px]">
                <span style={{ color: 'var(--text-muted)' }}>Tax ({(data.tax_rate * 100).toFixed(1)}%)</span>
                <span className="font-mono" style={{ color: 'var(--text-primary)' }}>${taxAmount.toFixed(2)}</span>
              </div>
              {data.discount_amount > 0 && (
                <div className="flex justify-between text-[11px]">
                  <span style={{ color: 'var(--text-muted)' }}>Discount</span>
                  <span className="font-mono" style={{ color: '#ef4444' }}>-${data.discount_amount.toFixed(2)}</span>
                </div>
              )}
              <div className="h-px my-1" style={{ background: 'var(--gold-border)' }} />
              <div className="flex justify-between text-sm font-semibold">
                <span style={{ color: 'var(--gold)' }}>Total</span>
                <span className="font-mono" style={{ color: 'var(--gold)' }}>${total.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-[11px]">
                <span style={{ color: 'var(--text-muted)' }}>Deposit ({data.deposit.deposit_percent}%)</span>
                <span className="font-mono" style={{ color: 'var(--text-primary)' }}>${depositAmount.toFixed(2)}</span>
              </div>
            </div>
          </>
        )}

        {/* ── Details Tab ──────────────────────────────────── */}
        {activeTab === 'details' && (
          <>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[9px] font-semibold mb-1 block" style={{ color: 'var(--text-muted)' }}>TAX RATE (%)</label>
                <input type="number" value={(data.tax_rate * 100).toFixed(1)} step={0.1} min={0} max={20}
                  onChange={e => setData({ ...data, tax_rate: (parseFloat(e.target.value) || 0) / 100 })}
                  className="w-full rounded-lg px-3 py-2 text-xs outline-none" style={inputStyle} />
              </div>
              <div>
                <label className="text-[9px] font-semibold mb-1 block" style={{ color: 'var(--text-muted)' }}>DISCOUNT ($)</label>
                <input type="number" value={data.discount_amount} step={1} min={0}
                  onChange={e => setData({ ...data, discount_amount: parseFloat(e.target.value) || 0 })}
                  className="w-full rounded-lg px-3 py-2 text-xs outline-none" style={inputStyle} />
              </div>
              <div>
                <label className="text-[9px] font-semibold mb-1 block" style={{ color: 'var(--text-muted)' }}>DEPOSIT %</label>
                <input type="number" value={data.deposit.deposit_percent} step={5} min={0} max={100}
                  onChange={e => setData({ ...data, deposit: { ...data.deposit, deposit_percent: parseFloat(e.target.value) || 0 } })}
                  className="w-full rounded-lg px-3 py-2 text-xs outline-none" style={inputStyle} />
              </div>
              <div>
                <label className="text-[9px] font-semibold mb-1 block" style={{ color: 'var(--text-muted)' }}>VALID DAYS</label>
                <input type="number" value={data.valid_days} step={1} min={1}
                  onChange={e => setData({ ...data, valid_days: parseInt(e.target.value) || 30 })}
                  className="w-full rounded-lg px-3 py-2 text-xs outline-none" style={inputStyle} />
              </div>
            </div>

            <div>
              <label className="text-[9px] font-semibold mb-1 block" style={{ color: 'var(--text-muted)' }}>INSTALL DATE</label>
              <input type="date" value={data.install_date}
                onChange={e => setData({ ...data, install_date: e.target.value })}
                className="w-full rounded-lg px-3 py-2 text-xs outline-none" style={inputStyle} />
            </div>

            <div>
              <label className="text-[9px] font-semibold mb-1 block" style={{ color: 'var(--text-muted)' }}>TERMS</label>
              <textarea value={data.terms}
                onChange={e => setData({ ...data, terms: e.target.value })}
                className="w-full rounded-lg px-3 py-2 text-xs outline-none resize-none" style={inputStyle} rows={3} />
            </div>

            <div>
              <label className="text-[9px] font-semibold mb-1 block" style={{ color: 'var(--text-muted)' }}>INTERNAL NOTES</label>
              <textarea value={data.notes}
                onChange={e => setData({ ...data, notes: e.target.value })}
                className="w-full rounded-lg px-3 py-2 text-xs outline-none resize-none" style={inputStyle} rows={2} />
            </div>

            <div className="rounded-xl p-3" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
              <p className="text-[10px] font-semibold mb-2" style={{ color: 'var(--text-muted)' }}>BUSINESS BRANDING</p>
              <div className="grid grid-cols-2 gap-2">
                <input placeholder="Business name" value={data.business_name}
                  onChange={e => setData({ ...data, business_name: e.target.value })}
                  className="rounded-lg px-3 py-2 text-xs outline-none" style={inputStyle} />
                <input placeholder="Logo URL" value={data.business_logo_url}
                  onChange={e => setData({ ...data, business_logo_url: e.target.value })}
                  className="rounded-lg px-3 py-2 text-xs outline-none" style={inputStyle} />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
