'use client';
import { useState, useEffect, useCallback } from 'react';
import { API } from '../../lib/api';
import ProductDocs from '../business/docs/ProductDocs';

type PricingStatus = {
  status: string;
  pricing_engine_version: string;
  formula_version: string;
  rate_tables: { workroom: string; woodcraft: string };
  business_units: string[];
  snapshot_based: boolean;
  manual_override_requires_reason: boolean;
  unknown_category_fallback: boolean;
};

type WorkroomResult = {
  business_unit: string;
  module: string;
  product_category: string;
  pricing_method: string;
  pricing_inputs: Record<string, any>;
  rate_table_version: string;
  formula_version: string;
  calculation_steps: Array<{ label: string; formula: string; quantity: number; rate: number; amount: number; deposit_percent?: number }>;
  calculated_subtotal: number;
  discount_type: string;
  discount_amount: number;
  tax_amount: number;
  deposit_required: boolean;
  deposit_percent: number;
  deposit_amount: number;
  balance_due: number;
  final_price: number;
  pricing_snapshot: Record<string, any>;
};

type LaborRate = { category: string; rate: number };

const WORKROOM_FIELDS = [
  { key: 'finished_width', label: 'Finished Width (in)', placeholder: '48' },
  { key: 'finished_length', label: 'Finished Length (in)', placeholder: '84' },
  { key: 'fabric_price_per_yard', label: 'Fabric Price/yard ($)', placeholder: '45' },
  { key: 'num_panels', label: 'Number of Panels', placeholder: '2' },
];

const WOODCRAFT_FIELDS = [
  { key: 'width', label: 'Width (in)', placeholder: '24' },
  { key: 'height', label: 'Height (in)', placeholder: '36' },
  { key: 'CNC_time_minutes', label: 'CNC Time (min)', placeholder: '45' },
];

const WORKROOM_TYPES = [
  { value: 'drapery', label: 'Drapery / Curtains' },
  { value: 'roman_shade', label: 'Roman Shade' },
  { value: 'upholstery', label: 'Upholstery / Cushion' },
  { value: 'cushion', label: 'Cushion' },
  { value: 'pillow', label: 'Pillow' },
  { value: 'fabric_materials', label: 'Fabric Materials' },
];

const WOODCRAFT_TYPES = [
  { value: 'cnc_router_time', label: 'CNC Router Time' },
  { value: 'sheet_goods', label: 'Sheet Goods' },
  { value: 'board_foot_material', label: 'Board Foot Material' },
  { value: 'design_drawing_time', label: 'Design / Drawing Time' },
  { value: 'assembly_labor', label: 'Assembly Labor' },
  { value: 'finishing', label: 'Finishing' },
  { value: 'hardware', label: 'Hardware' },
  { value: 'custom_build', label: 'Custom Build / Millwork' },
];

export default function PricingStudioScreen() {
  const [status, setStatus] = useState<PricingStatus | null>(null);
  const [laborRates, setLaborRates] = useState<LaborRate[]>([]);
  const [activeTab, setActiveTab] = useState<'engine' | 'workroom' | 'woodcraft' | 'override' | 'audit' | 'docs'>('engine');
  const [workroomType, setWorkroomType] = useState('drapery');
  const [woodcraftType, setWoodcraftType] = useState('cnc_router_time');
  const [workroomInputs, setWorkroomInputs] = useState<Record<string, string>>({});
  const [woodcraftInputs, setWoodcraftInputs] = useState<Record<string, string>>({});
  const [workroomResult, setWorkroomResult] = useState<WorkroomResult | null>(null);
  const [woodcraftResult, setWoodcraftResult] = useState<WorkroomResult | null>(null);
  const [overrideInputs, setOverrideInputs] = useState({ category: 'drapery', amount: '', reason: '' });
  const [overrideResult, setOverrideResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [unknownResult, setUnknownResult] = useState<any>(null);
  const [unknownCategory, setUnknownCategory] = useState('');

  const loadStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/pricing/canonical/status`);
      if (res.ok) setStatus(await res.json());
      else setStatusError(`Status endpoint returned ${res.status}`);
    } catch (e: any) {
      setStatusError(e.message || 'Failed to load pricing status');
    }
  }, []);

  useEffect(() => {
    loadStatus();
    fetch(`${API}/pricing/labor-rates`)
      .then(r => r.ok ? r.json() : null)
      .then(data => data && setLaborRates(Object.entries(data).map(([k, v]) => ({ category: k, rate: v as number }))))
      .catch(() => {});
  }, [loadStatus]);

  const buildWorkroomPayload = () => ({
    item_type: workroomType,
    pricing_inputs: {
      finished_width: parseFloat(workroomInputs['finished_width']) || 0,
      finished_length: parseFloat(workroomInputs['finished_length']) || 0,
      fabric_price_per_yard: parseFloat(workroomInputs['fabric_price_per_yard']) || 0,
      num_panels: parseInt(workroomInputs['num_panels']) || 1,
    },
  });

  const buildWoodcraftPayload = () => ({
    product_category: woodcraftType,
    pricing_inputs: {
      width: parseFloat(woodcraftInputs['width']) || 0,
      height: parseFloat(woodcraftInputs['height']) || 0,
      CNC_time_minutes: parseFloat(woodcraftInputs['CNC_time_minutes']) || 0,
    },
  });

  const calcWorkroom = async () => {
    setLoading(true);
    setError(null);
    setWorkroomResult(null);
    try {
      const res = await fetch(`${API}/pricing/workroom/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildWorkroomPayload()),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      setWorkroomResult(data);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  const calcWoodcraft = async () => {
    setLoading(true);
    setError(null);
    setWoodcraftResult(null);
    try {
      const res = await fetch(`${API}/pricing/woodcraft/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildWoodcraftPayload()),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      setWoodcraftResult(data);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  const testOverride = async () => {
    if (!overrideInputs.amount || !overrideInputs.reason) {
      setOverrideResult({ error: 'override_amount and override_reason are both required' });
      return;
    }
    setLoading(true);
    setOverrideResult(null);
    try {
      const res = await fetch(`${API}/pricing/workroom/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          item_type: overrideInputs.category,
          pricing_inputs: { finished_width: 0, finished_length: 0 },
          override_amount: parseFloat(overrideInputs.amount),
          override_reason: overrideInputs.reason,
        }),
      });
      const data = await res.json();
      setOverrideResult(data);
    } catch (e: any) {
      setOverrideResult({ error: e.message });
    }
    setLoading(false);
  };

  const testUnknownCategory = async () => {
    if (!unknownCategory.trim()) { setUnknownResult({ error: 'category required' }); return; }
    setLoading(true);
    setUnknownResult(null);
    try {
      const res = await fetch(`${API}/pricing/workroom/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_type: unknownCategory, pricing_inputs: { finished_width: 0, finished_length: 0 } }),
      });
      const data = await res.json();
      setUnknownResult({ status: res.status, body: data });
    } catch (e: any) {
      setUnknownResult({ error: e.message });
    }
    setLoading(false);
  };

  const cardStyle: React.CSSProperties = {
    background: '#fff',
    border: '1px solid #dedbd2',
    borderRadius: 10,
    padding: '18px 20px',
  };

  const labelStyle: React.CSSProperties = { fontSize: 12, fontWeight: 600, color: '#62717f', marginBottom: 4 };
  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '8px 10px',
    border: '1px solid #dedbd2',
    borderRadius: 6,
    fontSize: 13,
    color: '#1a1a1a',
    background: '#fafaf8',
    outline: 'none',
    boxSizing: 'border-box',
  };

  const TABS = [
    { id: 'engine' as const, label: 'Engine Status' },
    { id: 'workroom' as const, label: 'Workroom' },
    { id: 'woodcraft' as const, label: 'Woodcraft' },
    { id: 'override' as const, label: 'Manual Override' },
    { id: 'audit' as const, label: 'Unknown + Audit' },
    { id: 'docs' as const, label: 'Docs' },
  ];

  return (
    <div style={{ minHeight: '100vh', background: '#f7f7f4', color: '#1f2933', fontFamily: 'Inter, system-ui, sans-serif' }}>
      <header style={{ borderBottom: '1px solid #dedbd2', background: '#fff', padding: '16px 24px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <h1 style={{ fontSize: 20, margin: 0, fontWeight: 800 }}>Pricing Studio</h1>
            <p style={{ margin: '3px 0 0', color: '#62717f', fontSize: 12 }}>Empire canonical pricing engine — Workroom + Woodcraft.</p>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ fontSize: 11, color: '#62717f', background: '#f0ede8', padding: '3px 10px', borderRadius: 20, border: '1px solid #dedbd2' }}>
              {status ? `v${status.pricing_engine_version}` : '—'}
            </span>
            <button
              onClick={loadStatus}
              style={{ fontSize: 12, color: '#0f766e', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }}
            >
              Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div style={{ borderBottom: '1px solid #dedbd2', background: '#fff', padding: '0 24px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', gap: 4 }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '12px 16px 10px',
                border: 'none',
                borderBottom: activeTab === tab.id ? '2px solid #b8960c' : '2px solid transparent',
                background: 'none',
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: activeTab === tab.id ? 700 : 500,
                color: activeTab === tab.id ? '#1a1a1a' : '#62717f',
                transition: 'all 0.15s',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px' }}>

        {/* Engine Status */}
        {activeTab === 'engine' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {statusError && (
              <div style={{ ...cardStyle, background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', fontSize: 13 }}>
                {statusError}
              </div>
            )}
            {status && (
              <>
                <div style={{ ...cardStyle, border: '1px solid #237954', background: '#f0fdf4' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e' }} />
                    <span style={{ fontWeight: 700, fontSize: 14, color: '#166534' }}>Pricing Engine Available</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10 }}>
                    {[
                      { label: 'Engine Version', value: status.pricing_engine_version },
                      { label: 'Formula Version', value: status.formula_version },
                      { label: 'Workroom Rate Table', value: status.rate_tables.workroom },
                      { label: 'Woodcraft Rate Table', value: status.rate_tables.woodcraft },
                      { label: 'Snapshot Based', value: String(status.snapshot_based) },
                      { label: 'Override Requires Reason', value: String(status.manual_override_requires_reason) },
                      { label: 'Unknown Category Fallback', value: String(status.unknown_category_fallback) },
                    ].map(f => (
                      <div key={f.label} style={{ background: '#fff', border: '1px solid #d1fae5', borderRadius: 6, padding: '10px 12px' }}>
                        <div style={{ fontSize: 10, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{f.label}</div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginTop: 2 }}>{String(f.value)}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {laborRates.length > 0 && (
                  <div style={cardStyle}>
                    <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 12px' }}>Labor Rates</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 8 }}>
                      {laborRates.map(r => (
                        <div key={r.category} style={{ background: '#fafaf8', border: '1px solid #ebe8df', borderRadius: 6, padding: '8px 12px' }}>
                          <div style={{ fontSize: 11, color: '#62717f', fontWeight: 500 }}>{r.category}</div>
                          <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>${r.rate.toFixed(2)}/hr</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Workroom */}
        {activeTab === 'workroom' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={cardStyle}>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 12px' }}>Workroom Calculation</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: 12, marginBottom: 14 }}>
                <div>
                  <div style={labelStyle}>Product Type</div>
                  <select
                    value={workroomType}
                    onChange={e => setWorkroomType(e.target.value)}
                    style={{ ...inputStyle, appearance: 'none', cursor: 'pointer' }}
                  >
                    {WORKROOM_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                {WORKROOM_FIELDS.map(f => (
                  <div key={f.key}>
                    <div style={labelStyle}>{f.label}</div>
                    <input
                      style={inputStyle}
                      placeholder={f.placeholder}
                      value={workroomInputs[f.key] || ''}
                      onChange={e => setWorkroomInputs(prev => ({ ...prev, [f.key]: e.target.value }))}
                    />
                  </div>
                ))}
              </div>
              <button
                onClick={calcWorkroom}
                disabled={loading}
                style={{
                  padding: '10px 20px',
                  background: '#b8960c',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 8,
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.6 : 1,
                }}
              >
                {loading ? 'Calculating...' : 'Calculate Workroom Price'}
              </button>
            </div>

            {error && (
              <div style={{ ...cardStyle, background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', fontSize: 13 }}>
                {error}
              </div>
            )}

            {workroomResult && (
              <div style={{ ...cardStyle, border: '1px solid #237954' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                  <div>
                    <div style={{ fontSize: 11, color: '#62717f', fontWeight: 600 }}>FINAL PRICE</div>
                    <div style={{ fontSize: 32, fontWeight: 800, color: '#166534', lineHeight: 1 }}>${workroomResult.final_price.toFixed(2)}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 11, color: '#62717f' }}>SUBTOTAL</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a' }}>${workroomResult.calculated_subtotal.toFixed(2)}</div>
                  </div>
                </div>

                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: '#62717f', marginBottom: 6 }}>CALCULATION STEPS</div>
                  {workroomResult.calculation_steps.map((step, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f0ede8', fontSize: 12 }}>
                      <span style={{ color: '#374151' }}>{step.label}</span>
                      <span style={{ color: '#62717f' }}>{step.formula} → ${step.amount.toFixed(2)}</span>
                    </div>
                  ))}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginTop: 12 }}>
                  {[
                    { label: 'Tax', value: `$${workroomResult.tax_amount.toFixed(2)}` },
                    { label: `Deposit (${workroomResult.deposit_percent}%)`, value: `$${workroomResult.deposit_amount.toFixed(2)}` },
                    { label: 'Balance Due', value: `$${workroomResult.balance_due.toFixed(2)}` },
                  ].map(f => (
                    <div key={f.label} style={{ background: '#fafaf8', border: '1px solid #ebe8df', borderRadius: 6, padding: '8px 12px', textAlign: 'center' }}>
                      <div style={{ fontSize: 10, color: '#62717f', fontWeight: 600 }}>{f.label}</div>
                      <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', marginTop: 2 }}>{f.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Woodcraft */}
        {activeTab === 'woodcraft' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={cardStyle}>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 12px' }}>Woodcraft / CraftForge Calculation</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: 12, marginBottom: 14 }}>
                <div>
                  <div style={labelStyle}>Product Type</div>
                  <select
                    value={woodcraftType}
                    onChange={e => setWoodcraftType(e.target.value)}
                    style={{ ...inputStyle, appearance: 'none', cursor: 'pointer' }}
                  >
                    {WOODCRAFT_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                {WOODCRAFT_FIELDS.map(f => (
                  <div key={f.key}>
                    <div style={labelStyle}>{f.label}</div>
                    <input
                      style={inputStyle}
                      placeholder={f.placeholder}
                      value={woodcraftInputs[f.key] || ''}
                      onChange={e => setWoodcraftInputs(prev => ({ ...prev, [f.key]: e.target.value }))}
                    />
                  </div>
                ))}
              </div>
              <button
                onClick={calcWoodcraft}
                disabled={loading}
                style={{
                  padding: '10px 20px',
                  background: '#b8960c',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 8,
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.6 : 1,
                }}
              >
                {loading ? 'Calculating...' : 'Calculate Woodcraft Price'}
              </button>
            </div>

            {woodcraftResult && (
              <div style={{ ...cardStyle, border: '1px solid #237954' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                  <div>
                    <div style={{ fontSize: 11, color: '#62717f', fontWeight: 600 }}>FINAL PRICE</div>
                    <div style={{ fontSize: 32, fontWeight: 800, color: '#166534', lineHeight: 1 }}>${woodcraftResult.final_price.toFixed(2)}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 11, color: '#62717f' }}>SUBTOTAL</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a' }}>${woodcraftResult.calculated_subtotal.toFixed(2)}</div>
                  </div>
                </div>
                <div style={{ fontSize: 12, color: '#62717f' }}>
                  Product: <strong style={{ color: '#1a1a1a' }}>{woodcraftResult.product_category}</strong> · Method: <strong style={{ color: '#1a1a1a' }}>{woodcraftResult.pricing_method}</strong>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Manual Override */}
        {activeTab === 'override' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={cardStyle}>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 8px' }}>Manual Override Test</h3>
              <p style={{ fontSize: 12, color: '#62717f', margin: '0 0 14px' }}>
                Manual override requires override_reason to be set. Empty reason should return an error.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr 1fr', gap: 12, marginBottom: 14 }}>
                <div>
                  <div style={labelStyle}>Category</div>
                  <select
                    value={overrideInputs.category}
                    onChange={e => setOverrideInputs(prev => ({ ...prev, category: e.target.value }))}
                    style={{ ...inputStyle, appearance: 'none', cursor: 'pointer' }}
                  >
                    {WORKROOM_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div>
                  <div style={labelStyle}>Override Amount ($)</div>
                  <input
                    style={inputStyle}
                    placeholder="0.00"
                    value={overrideInputs.amount}
                    onChange={e => setOverrideInputs(prev => ({ ...prev, amount: e.target.value }))}
                  />
                </div>
                <div>
                  <div style={labelStyle}>Override Reason *</div>
                  <input
                    style={inputStyle}
                    placeholder="customer request, competitor quote match..."
                    value={overrideInputs.reason}
                    onChange={e => setOverrideInputs(prev => ({ ...prev, reason: e.target.value }))}
                  />
                </div>
              </div>
              <button
                onClick={testOverride}
                disabled={loading}
                style={{
                  padding: '10px 20px',
                  background: '#b8960c',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 8,
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.6 : 1,
                }}
              >
                {loading ? 'Testing...' : 'Test Override (with reason)'}
              </button>

              <button
                onClick={async () => {
                  setLoading(true);
                  setOverrideResult(null);
                  try {
                    const res = await fetch(`${API}/pricing/workroom/calculate`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        item_type: overrideInputs.category,
                        pricing_inputs: { finished_width: 0, finished_length: 0 },
                        override_amount: 50,
                        override_reason: '',
                      }),
                    });
                    setOverrideResult({ status: res.status, body: await res.json() });
                  } catch (e: any) { setOverrideResult({ error: e.message }); }
                  setLoading(false);
                }}
                disabled={loading}
                style={{
                  marginLeft: 8,
                  padding: '10px 20px',
                  background: '#dc2626',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 8,
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.6 : 1,
                }}
              >
                Test Empty Reason (expect error)
              </button>
            </div>

            {overrideResult && (
              <div style={{
                ...cardStyle,
                border: overrideResult.error ? '1px solid #fecaca' : '1px solid #237954',
                background: overrideResult.error ? '#fef2f2' : '#f0fdf4',
              }}>
                <div style={{ fontSize: 13, color: overrideResult.error ? '#dc2626' : '#166534', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                  {overrideResult.error
                    ? overrideResult.error
                    : JSON.stringify(overrideResult.status ? { status: overrideResult.status, ...overrideResult.body } : overrideResult, null, 2)}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Unknown Category + Audit */}
        {activeTab === 'audit' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={cardStyle}>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 8px' }}>Unknown Category Test</h3>
              <p style={{ fontSize: 12, color: '#62717f', margin: '0 0 14px' }}>
                unknown_category_fallback=false — unknown categories should return HTTP 400, not silently proceed.
              </p>
              <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={labelStyle}>Unknown Category String</div>
                  <input
                    style={inputStyle}
                    placeholder="e.g. 'custom_widget', 'laser_cut', 'something_fake'"
                    value={unknownCategory}
                    onChange={e => setUnknownCategory(e.target.value)}
                  />
                </div>
                <button
                  onClick={testUnknownCategory}
                  disabled={loading}
                  style={{
                    padding: '10px 20px',
                    background: '#b8960c',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 8,
                    fontWeight: 700,
                    fontSize: 13,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    opacity: loading ? 0.6 : 1,
                  }}
                >
                  {loading ? 'Testing...' : 'Test Unknown Category'}
                </button>
              </div>
            </div>

            {unknownResult && (
              <div style={{
                ...cardStyle,
                border: unknownResult.error ? '1px solid #fecaca' : unknownResult.status === 400 ? '1px solid #237954' : '1px solid #fde68a',
                background: unknownResult.error ? '#fef2f2' : unknownResult.status === 400 ? '#f0fdf4' : '#fdf8eb',
              }}>
                <div style={{ fontSize: 12, color: unknownResult.error ? '#dc2626' : '#166534', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                  {unknownResult.error
                    ? unknownResult.error
                    : `HTTP ${unknownResult.status}\n${JSON.stringify(unknownResult.body, null, 2)}`}
                </div>
              </div>
            )}

            {status && (
              <div style={cardStyle}>
                <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 12px' }}>Audit Summary</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {[
                    { label: 'Snapshot preservation', value: status.snapshot_based ? '✓ Enabled — invoice flows preserve inputs' : '✗ Not snapshot-based' },
                    { label: 'Manual override requires reason', value: status.manual_override_requires_reason ? '✓ Enabled — override_reason must be set' : '✗ Bypass possible' },
                    { label: 'Unknown category fallback', value: status.unknown_category_fallback ? '✗ Silent fallback (unsafe)' : '✓ Hard error on unknown category' },
                    { label: 'Business units', value: status.business_units.join(', ') },
                    { label: 'Rate table versions', value: `Workroom: ${status.rate_tables.workroom} · Woodcraft: ${status.rate_tables.woodcraft}` },
                  ].map(row => (
                    <div key={row.label} style={{ display: 'flex', gap: 12, fontSize: 12, borderBottom: '1px solid #f0ede8', paddingBottom: 8 }}>
                      <span style={{ width: 240, color: '#62717f', fontWeight: 600, flexShrink: 0 }}>{row.label}</span>
                      <span style={{ color: '#1a1a1a' }}>{row.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'docs' && (
          <div style={cardStyle}>
            <ProductDocs product="pricing-studio" />
          </div>
        )}
      </div>
    </div>
  );
}
