'use client';
import React, { useState } from 'react';
import {
  Package, Truck, BarChart3, MapPin, DollarSign, Settings,
  Plus, Search, ChevronRight, Check, X, Loader2, Clock,
  ArrowRight, AlertTriangle, ExternalLink, CheckCircle,
  Hash, Calendar, Box, Scale, Tag, Clipboard, RefreshCw,
  Navigation, CircleDot, ChevronDown, Eye, BookOpen, CreditCard
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';

const NAV_SECTIONS = [
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
  { id: 'ship-now', label: 'Ship Now', icon: Truck },
  { id: 'shipments', label: 'Shipments', icon: Package },
  { id: 'tracking', label: 'Tracking', icon: Navigation },
  { id: 'rates', label: 'Rates', icon: DollarSign },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'payments', label: 'Payments', icon: CreditCard },
  { id: 'docs', label: 'Docs', icon: BookOpen },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

const ACCENT = '#2563eb';
const ACCENT_BG = '#dbeafe';
const ACCENT_BORDER = '#93c5fd';

// ============ MOCK DATA ============

const CARRIERS = ['USPS', 'UPS', 'FedEx', 'DHL'] as const;
type Carrier = typeof CARRIERS[number];

const SERVICE_LEVELS: Record<Carrier, string[]> = {
  USPS: ['Priority Mail', 'Priority Mail Express', 'First-Class', 'Ground Advantage', 'Media Mail'],
  UPS: ['Ground', 'Next Day Air', '2nd Day Air', '3 Day Select', 'UPS SurePost'],
  FedEx: ['Ground', 'Express Saver', '2Day', 'Standard Overnight', 'Priority Overnight'],
  DHL: ['Express Worldwide', 'Express 12:00', 'Economy Select', 'eCommerce'],
};

type ShipmentStatus = 'label_created' | 'in_transit' | 'out_for_delivery' | 'delivered' | 'exception';

interface Shipment {
  id: string;
  trackingNumber: string;
  recipient: string;
  recipientCity: string;
  recipientState: string;
  carrier: Carrier;
  service: string;
  status: ShipmentStatus;
  date: string;
  cost: number;
  weight: number;
  dimensions: string;
}

const MOCK_SHIPMENTS: Shipment[] = [
  { id: 'SHP-001', trackingNumber: '9400111899223847561234', recipient: 'Sarah Chen', recipientCity: 'New York', recipientState: 'NY', carrier: 'USPS', service: 'Priority Mail', status: 'delivered', date: '2026-03-08', cost: 8.95, weight: 2.3, dimensions: '12x8x6' },
  { id: 'SHP-002', trackingNumber: '1Z999AA10123456784', recipient: 'Marcus Johnson', recipientCity: 'Los Angeles', recipientState: 'CA', carrier: 'UPS', service: 'Ground', status: 'in_transit', date: '2026-03-08', cost: 12.50, weight: 5.1, dimensions: '16x12x10' },
  { id: 'SHP-003', trackingNumber: '794644790132', recipient: 'Emily Rodriguez', recipientCity: 'Chicago', recipientState: 'IL', carrier: 'FedEx', service: '2Day', status: 'out_for_delivery', date: '2026-03-07', cost: 18.75, weight: 3.8, dimensions: '14x10x8' },
  { id: 'SHP-004', trackingNumber: '9400111899223847561235', recipient: 'James Williams', recipientCity: 'Houston', recipientState: 'TX', carrier: 'USPS', service: 'Ground Advantage', status: 'in_transit', date: '2026-03-07', cost: 5.25, weight: 1.2, dimensions: '10x8x4' },
  { id: 'SHP-005', trackingNumber: '1Z999AA10123456785', recipient: 'Aisha Patel', recipientCity: 'Phoenix', recipientState: 'AZ', carrier: 'UPS', service: 'Next Day Air', status: 'delivered', date: '2026-03-07', cost: 32.40, weight: 4.5, dimensions: '18x14x12' },
  { id: 'SHP-006', trackingNumber: '4987654321098765', recipient: 'David Kim', recipientCity: 'Philadelphia', recipientState: 'PA', carrier: 'DHL', service: 'Express Worldwide', status: 'label_created', date: '2026-03-09', cost: 45.00, weight: 8.2, dimensions: '20x16x14' },
  { id: 'SHP-007', trackingNumber: '794644790133', recipient: 'Lisa Thompson', recipientCity: 'San Antonio', recipientState: 'TX', carrier: 'FedEx', service: 'Ground', status: 'exception', date: '2026-03-06', cost: 9.80, weight: 2.0, dimensions: '12x10x6' },
  { id: 'SHP-008', trackingNumber: '9400111899223847561236', recipient: 'Robert Garcia', recipientCity: 'San Diego', recipientState: 'CA', carrier: 'USPS', service: 'Priority Mail Express', status: 'delivered', date: '2026-03-06', cost: 26.35, weight: 3.0, dimensions: '14x12x8' },
  { id: 'SHP-009', trackingNumber: '1Z999AA10123456786', recipient: 'Jennifer Lee', recipientCity: 'Dallas', recipientState: 'TX', carrier: 'UPS', service: '2nd Day Air', status: 'in_transit', date: '2026-03-09', cost: 22.10, weight: 6.0, dimensions: '22x16x12' },
  { id: 'SHP-010', trackingNumber: '794644790134', recipient: 'Michael Brown', recipientCity: 'San Jose', recipientState: 'CA', carrier: 'FedEx', service: 'Standard Overnight', status: 'label_created', date: '2026-03-09', cost: 38.50, weight: 2.5, dimensions: '12x10x8' },
  { id: 'SHP-011', trackingNumber: '9400111899223847561237', recipient: 'Amanda Wilson', recipientCity: 'Austin', recipientState: 'TX', carrier: 'USPS', service: 'First-Class', status: 'delivered', date: '2026-03-05', cost: 4.50, weight: 0.8, dimensions: '9x6x3' },
  { id: 'SHP-012', trackingNumber: '1Z999AA10123456787', recipient: 'Chris Martinez', recipientCity: 'Jacksonville', recipientState: 'FL', carrier: 'UPS', service: 'UPS SurePost', status: 'delivered', date: '2026-03-05', cost: 7.20, weight: 1.5, dimensions: '10x8x5' },
];

const MOCK_RATES = [
  { carrier: 'USPS' as Carrier, service: 'Priority Mail', days: '1-3', price: 8.95 },
  { carrier: 'USPS' as Carrier, service: 'Ground Advantage', days: '2-5', price: 5.25 },
  { carrier: 'USPS' as Carrier, service: 'Priority Mail Express', days: '1-2', price: 26.35 },
  { carrier: 'UPS' as Carrier, service: 'Ground', days: '3-5', price: 12.50 },
  { carrier: 'UPS' as Carrier, service: '2nd Day Air', days: '2', price: 22.10 },
  { carrier: 'UPS' as Carrier, service: 'Next Day Air', days: '1', price: 32.40 },
  { carrier: 'FedEx' as Carrier, service: 'Ground', days: '3-5', price: 9.80 },
  { carrier: 'FedEx' as Carrier, service: '2Day', days: '2', price: 18.75 },
  { carrier: 'FedEx' as Carrier, service: 'Standard Overnight', days: '1', price: 38.50 },
  { carrier: 'DHL' as Carrier, service: 'eCommerce', days: '5-8', price: 11.00 },
  { carrier: 'DHL' as Carrier, service: 'Express Worldwide', days: '2-4', price: 45.00 },
];

const PACKAGE_PRESETS = [
  { name: 'Small Box', length: 10, width: 8, height: 4, weight: 1.0 },
  { name: 'Medium Box', length: 14, width: 10, height: 8, weight: 3.0 },
  { name: 'Large Box', length: 20, width: 16, height: 14, weight: 5.0 },
  { name: 'Flat Rate Envelope', length: 12.5, width: 9.5, height: 0.75, weight: 0.5 },
  { name: 'Tube', length: 38, width: 6, height: 6, weight: 2.0 },
];

const STATUS_CONFIG: Record<ShipmentStatus, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  label_created: { label: 'Label Created', color: '#6b7280', bg: '#f3f4f6', icon: <Tag size={13} /> },
  in_transit: { label: 'In Transit', color: '#2563eb', bg: '#dbeafe', icon: <Truck size={13} /> },
  out_for_delivery: { label: 'Out for Delivery', color: '#d97706', bg: '#fef3c7', icon: <Navigation size={13} /> },
  delivered: { label: 'Delivered', color: '#16a34a', bg: '#dcfce7', icon: <CheckCircle size={13} /> },
  exception: { label: 'Exception', color: '#dc2626', bg: '#fef2f2', icon: <AlertTriangle size={13} /> },
};

const CARRIER_COLORS: Record<Carrier, string> = {
  USPS: '#004B87',
  UPS: '#351C15',
  FedEx: '#4D148C',
  DHL: '#D40511',
};

// ============ MAIN COMPONENT ============

export default function ShipForgePage() {
  const [section, setSection] = useState<Section>('dashboard');

  const renderContent = () => {
    switch (section) {
      case 'dashboard': return <DashboardSection onNavigate={setSection} />;
      case 'ship-now': return <ShipNowSection />;
      case 'shipments': return <ShipmentsSection />;
      case 'tracking': return <TrackingSection />;
      case 'rates': return <RatesSection />;
      case 'settings': return <SettingsSection />;
      case 'payments': return <PaymentModule product="ship" />;
      case 'docs': return <div style={{ padding: 24 }}><ProductDocs product="ship" /></div>;
      default: return <DashboardSection onNavigate={setSection} />;
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      <nav style={{ width: 200, background: '#fff', borderRight: '1px solid #ece8e0', flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '18px 16px', borderBottom: '1px solid #ece8e0' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: ACCENT_BG }}>
              <Truck size={18} style={{ color: ACCENT }} />
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>ShipForge</div>
              <div style={{ fontSize: 10, color: '#999' }}>Shipping Management</div>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto" style={{ padding: '10px 10px' }}>
          <div className="flex flex-col gap-1.5">
            {NAV_SECTIONS.map(nav => {
              const Icon = nav.icon;
              const isActive = section === nav.id;
              return (
                <button key={nav.id}
                  onClick={() => setSection(nav.id)}
                  className="w-full flex items-center gap-3 text-left cursor-pointer transition-all"
                  style={{
                    padding: '10px 14px', borderRadius: 12, fontSize: 13,
                    fontWeight: isActive ? 700 : 500,
                    background: isActive ? ACCENT_BG : 'transparent',
                    color: isActive ? ACCENT : '#666',
                    border: isActive ? `1.5px solid ${ACCENT_BORDER}` : '1.5px solid transparent',
                  }}
                  onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = '#f5f3ef'; e.currentTarget.style.borderColor = '#ece8e0'; } }}
                  onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'transparent'; } }}
                >
                  <Icon size={17} />
                  {nav.label}
                </button>
              );
            })}
          </div>
        </div>
      </nav>
      <div className="flex-1 overflow-y-auto" style={{ background: '#f5f2ed' }}>
        {renderContent()}
      </div>
    </div>
  );
}

// ============ KPI CARD ============

function KPI({ icon, iconBg, iconColor, label, value, sub, onClick }: {
  icon: React.ReactNode; iconBg: string; iconColor: string; label: string; value: string; sub: string; onClick?: () => void;
}) {
  return (
    <div onClick={onClick} className="empire-card" style={{ cursor: onClick ? 'pointer' : 'default', padding: '16px 18px' }}>
      <div className="flex items-center gap-3 mb-2">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: iconBg, color: iconColor }}>{icon}</div>
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: '#999' }}>{label}</span>
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>{value}</div>
      <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>{sub}</div>
    </div>
  );
}

// ============ STATUS BADGE ============

function StatusBadge({ status }: { status: ShipmentStatus }) {
  const cfg = STATUS_CONFIG[status];
  return (
    <span className="inline-flex items-center gap-1.5" style={{
      padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
      background: cfg.bg, color: cfg.color,
    }}>
      {cfg.icon} {cfg.label}
    </span>
  );
}

// ============ SECTION HEADER ============

function SectionHeader({ title, subtitle, action }: { title: string; subtitle: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a' }}>{title}</h2>
        <p style={{ fontSize: 12, color: '#999', marginTop: 2 }}>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}

// ============ 1. DASHBOARD ============

function DashboardSection({ onNavigate }: { onNavigate: (s: Section) => void }) {
  const today = MOCK_SHIPMENTS.filter(s => s.date === '2026-03-09');
  const thisWeek = MOCK_SHIPMENTS.filter(s => s.date >= '2026-03-03');
  const thisMonth = MOCK_SHIPMENTS;
  const avgCost = thisMonth.reduce((sum, s) => sum + s.cost, 0) / thisMonth.length;
  const pending = MOCK_SHIPMENTS.filter(s => s.status === 'label_created' || s.status === 'in_transit');
  const delivered = MOCK_SHIPMENTS.filter(s => s.status === 'delivered');

  const carrierBreakdown = CARRIERS.map(c => ({
    carrier: c,
    count: MOCK_SHIPMENTS.filter(s => s.carrier === c).length,
    total: MOCK_SHIPMENTS.filter(s => s.carrier === c).reduce((sum, s) => sum + s.cost, 0),
  }));

  return (
    <div style={{ padding: 24 }}>
      <SectionHeader title="Shipping Dashboard" subtitle="Overview of your shipping operations" />

      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPI icon={<Package size={16} />} iconBg={ACCENT_BG} iconColor={ACCENT} label="Shipped Today" value={String(today.length)} sub={`$${today.reduce((s, x) => s + x.cost, 0).toFixed(2)} total`} />
        <KPI icon={<Truck size={16} />} iconBg="#fef3c7" iconColor="#d97706" label="This Week" value={String(thisWeek.length)} sub={`$${thisWeek.reduce((s, x) => s + x.cost, 0).toFixed(2)} total`} />
        <KPI icon={<Calendar size={16} />} iconBg="#dcfce7" iconColor="#16a34a" label="This Month" value={String(thisMonth.length)} sub={`Avg $${avgCost.toFixed(2)} per shipment`} />
        <KPI icon={<Clock size={16} />} iconBg="#fef2f2" iconColor="#dc2626" label="Pending" value={String(pending.length)} sub={`${delivered.length} delivered`} />
      </div>

      {/* Carrier Breakdown */}
      <div className="empire-card mb-6" style={{ padding: '20px 22px' }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Carrier Breakdown</div>
        <div className="grid grid-cols-4 gap-4">
          {carrierBreakdown.map(cb => (
            <div key={cb.carrier} style={{ padding: '14px 16px', borderRadius: 12, border: '1px solid #ece8e0', background: '#fafaf8' }}>
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-md flex items-center justify-center" style={{ background: CARRIER_COLORS[cb.carrier], color: '#fff' }}>
                  <Truck size={12} />
                </div>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{cb.carrier}</span>
              </div>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a' }}>{cb.count} <span style={{ fontSize: 11, fontWeight: 500, color: '#999' }}>shipments</span></div>
              <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>${cb.total.toFixed(2)} total</div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="empire-card mb-6" style={{ padding: '20px 22px' }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 14 }}>Quick Actions</div>
        <div className="grid grid-cols-3 gap-3">
          {[
            { icon: <Plus size={16} />, label: 'Create Shipment', desc: 'Ship a new package', section: 'ship-now' as Section },
            { icon: <Search size={16} />, label: 'Track Package', desc: 'Enter a tracking number', section: 'tracking' as Section },
            { icon: <DollarSign size={16} />, label: 'Compare Rates', desc: 'Find the best rate', section: 'rates' as Section },
          ].map(qa => (
            <div key={qa.label} onClick={() => onNavigate(qa.section)} className="empire-card" style={{ cursor: 'pointer', padding: '14px 16px' }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = ACCENT)}
              onMouseLeave={e => (e.currentTarget.style.borderColor = '#ece8e0')}>
              <div className="flex items-center gap-2 mb-1" style={{ color: ACCENT }}>{qa.icon}<span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{qa.label}</span></div>
              <div style={{ fontSize: 11, color: '#999' }}>{qa.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Shipments */}
      <div className="empire-card" style={{ padding: '20px 22px' }}>
        <div className="flex items-center justify-between mb-4">
          <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Recent Shipments</div>
          <button onClick={() => onNavigate('shipments')} className="flex items-center gap-1 cursor-pointer" style={{ fontSize: 12, color: ACCENT, fontWeight: 600, background: 'none', border: 'none' }}>
            View All <ChevronRight size={14} />
          </button>
        </div>
        <div className="flex flex-col gap-2">
          {MOCK_SHIPMENTS.slice(0, 5).map(s => (
            <div key={s.id} style={{ padding: '10px 14px', borderRadius: 10, border: '1px solid #ece8e0', background: '#fafaf8' }}
              className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: CARRIER_COLORS[s.carrier] + '18', color: CARRIER_COLORS[s.carrier] }}>
                  <Truck size={14} />
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{s.recipient}</div>
                  <div style={{ fontSize: 11, color: '#999' }}>{s.carrier} {s.service} &middot; {s.recipientCity}, {s.recipientState}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={s.status} />
                <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>${s.cost.toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============ 2. SHIP NOW ============

function ShipNowSection() {
  const [fromName, setFromName] = useState('Empire HQ');
  const [fromAddr, setFromAddr] = useState('1234 Business Ave');
  const [fromCity, setFromCity] = useState('Washington');
  const [fromState, setFromState] = useState('DC');
  const [fromZip, setFromZip] = useState('20001');
  const [toName, setToName] = useState('');
  const [toAddr, setToAddr] = useState('');
  const [toCity, setToCity] = useState('');
  const [toState, setToState] = useState('');
  const [toZip, setToZip] = useState('');
  const [length, setLength] = useState('12');
  const [width, setWidth] = useState('10');
  const [height, setHeight] = useState('6');
  const [weight, setWeight] = useState('2');
  const [carrier, setCarrier] = useState<Carrier>('USPS');
  const [service, setService] = useState('');
  const [showRates, setShowRates] = useState(false);
  const [labelGenerated, setLabelGenerated] = useState(false);

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd',
    fontSize: 13, background: '#fff', outline: 'none',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 11, fontWeight: 600, color: '#666', marginBottom: 4, display: 'block', textTransform: 'uppercase', letterSpacing: 0.5,
  };

  const handleCompareRates = () => {
    if (toZip && weight) setShowRates(true);
  };

  const handleGenerateLabel = () => {
    setLabelGenerated(true);
    setTimeout(() => setLabelGenerated(false), 3000);
  };

  const applyPreset = (preset: typeof PACKAGE_PRESETS[0]) => {
    setLength(String(preset.length));
    setWidth(String(preset.width));
    setHeight(String(preset.height));
    setWeight(String(preset.weight));
  };

  return (
    <div style={{ padding: 24 }}>
      <SectionHeader title="Ship Now" subtitle="Create a new shipment and generate a label" />

      <div className="grid grid-cols-2 gap-6">
        {/* From Address */}
        <div className="empire-card" style={{ padding: '20px 22px' }}>
          <div className="flex items-center gap-2 mb-4">
            <MapPin size={16} style={{ color: ACCENT }} />
            <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>From Address</span>
          </div>
          <div className="flex flex-col gap-3">
            <div><label style={labelStyle}>Name / Company</label><input value={fromName} onChange={e => setFromName(e.target.value)} style={inputStyle} /></div>
            <div><label style={labelStyle}>Street Address</label><input value={fromAddr} onChange={e => setFromAddr(e.target.value)} style={inputStyle} /></div>
            <div className="grid grid-cols-3 gap-2">
              <div><label style={labelStyle}>City</label><input value={fromCity} onChange={e => setFromCity(e.target.value)} style={inputStyle} /></div>
              <div><label style={labelStyle}>State</label><input value={fromState} onChange={e => setFromState(e.target.value)} style={inputStyle} /></div>
              <div><label style={labelStyle}>ZIP</label><input value={fromZip} onChange={e => setFromZip(e.target.value)} style={inputStyle} /></div>
            </div>
          </div>
        </div>

        {/* To Address */}
        <div className="empire-card" style={{ padding: '20px 22px' }}>
          <div className="flex items-center gap-2 mb-4">
            <MapPin size={16} style={{ color: '#dc2626' }} />
            <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>To Address</span>
          </div>
          <div className="flex flex-col gap-3">
            <div><label style={labelStyle}>Recipient Name</label><input value={toName} onChange={e => setToName(e.target.value)} placeholder="Full name" style={inputStyle} /></div>
            <div><label style={labelStyle}>Street Address</label><input value={toAddr} onChange={e => setToAddr(e.target.value)} placeholder="123 Main St" style={inputStyle} /></div>
            <div className="grid grid-cols-3 gap-2">
              <div><label style={labelStyle}>City</label><input value={toCity} onChange={e => setToCity(e.target.value)} placeholder="City" style={inputStyle} /></div>
              <div><label style={labelStyle}>State</label><input value={toState} onChange={e => setToState(e.target.value)} placeholder="ST" style={inputStyle} /></div>
              <div><label style={labelStyle}>ZIP</label><input value={toZip} onChange={e => setToZip(e.target.value)} placeholder="00000" style={inputStyle} /></div>
            </div>
          </div>
        </div>
      </div>

      {/* Package Details */}
      <div className="empire-card mt-6" style={{ padding: '20px 22px' }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Box size={16} style={{ color: ACCENT }} />
            <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Package Details</span>
          </div>
          <div className="flex gap-2">
            {PACKAGE_PRESETS.map(p => (
              <button key={p.name} onClick={() => applyPreset(p)}
                className="cursor-pointer"
                style={{ padding: '4px 10px', borderRadius: 8, border: '1px solid #ddd', background: '#fff', fontSize: 11, color: '#666', fontWeight: 500 }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = ACCENT; e.currentTarget.style.color = ACCENT; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = '#ddd'; e.currentTarget.style.color = '#666'; }}>
                {p.name}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-4 gap-4">
          <div><label style={labelStyle}>Length (in)</label><input value={length} onChange={e => setLength(e.target.value)} style={inputStyle} type="number" /></div>
          <div><label style={labelStyle}>Width (in)</label><input value={width} onChange={e => setWidth(e.target.value)} style={inputStyle} type="number" /></div>
          <div><label style={labelStyle}>Height (in)</label><input value={height} onChange={e => setHeight(e.target.value)} style={inputStyle} type="number" /></div>
          <div><label style={labelStyle}>Weight (lbs)</label><input value={weight} onChange={e => setWeight(e.target.value)} style={inputStyle} type="number" step="0.1" /></div>
        </div>
      </div>

      {/* Carrier & Service */}
      <div className="empire-card mt-6" style={{ padding: '20px 22px' }}>
        <div className="flex items-center gap-2 mb-4">
          <Truck size={16} style={{ color: ACCENT }} />
          <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Carrier &amp; Service</span>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label style={labelStyle}>Carrier</label>
            <div className="flex gap-2">
              {CARRIERS.map(c => (
                <button key={c} onClick={() => { setCarrier(c); setService(''); }}
                  className="flex-1 cursor-pointer"
                  style={{
                    padding: '10px', borderRadius: 10, fontSize: 13, fontWeight: carrier === c ? 700 : 500,
                    background: carrier === c ? ACCENT_BG : '#fff',
                    color: carrier === c ? ACCENT : '#666',
                    border: carrier === c ? `2px solid ${ACCENT}` : '1px solid #ddd',
                    textAlign: 'center',
                  }}>
                  {c}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label style={labelStyle}>Service Level</label>
            <select value={service} onChange={e => setService(e.target.value)}
              style={{ ...inputStyle, cursor: 'pointer' }}>
              <option value="">Select service...</option>
              {SERVICE_LEVELS[carrier].map(sl => (
                <option key={sl} value={sl}>{sl}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex gap-3 mt-5">
          <button onClick={handleCompareRates}
            className="flex items-center gap-2 cursor-pointer"
            style={{ padding: '10px 20px', borderRadius: 10, border: `1px solid ${ACCENT}`, background: '#fff', color: ACCENT, fontSize: 13, fontWeight: 600 }}>
            <DollarSign size={15} /> Compare Rates
          </button>
          <button onClick={handleGenerateLabel}
            className="flex items-center gap-2 cursor-pointer"
            style={{ padding: '10px 20px', borderRadius: 10, border: 'none', background: ACCENT, color: '#fff', fontSize: 13, fontWeight: 600 }}>
            {labelGenerated ? <><CheckCircle size={15} /> Label Generated!</> : <><Clipboard size={15} /> Generate Label</>}
          </button>
        </div>
      </div>

      {/* Rate Comparison */}
      {showRates && (
        <div className="empire-card mt-6" style={{ padding: '20px 22px' }}>
          <div className="flex items-center gap-2 mb-4">
            <DollarSign size={16} style={{ color: ACCENT }} />
            <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Rate Comparison</span>
            <span style={{ fontSize: 11, color: '#999', marginLeft: 8 }}>{fromZip} &rarr; {toZip} &middot; {weight} lbs</span>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ece8e0' }}>
                {['Carrier', 'Service', 'Est. Days', 'Price'].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {MOCK_RATES.sort((a, b) => a.price - b.price).map((r, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #f0ede8' }}
                  onMouseEnter={e => (e.currentTarget.style.background = '#fafaf8')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                  <td style={{ padding: '10px 12px' }}>
                    <span className="inline-flex items-center gap-1.5" style={{ fontSize: 12, fontWeight: 600, color: CARRIER_COLORS[r.carrier] }}>
                      <Truck size={12} /> {r.carrier}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', fontSize: 13, color: '#1a1a1a' }}>{r.service}</td>
                  <td style={{ padding: '10px 12px', fontSize: 13, color: '#666' }}>{r.days} days</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{ fontSize: 14, fontWeight: 700, color: i === 0 ? '#16a34a' : '#1a1a1a' }}>
                      ${(r.price * parseFloat(weight || '1')).toFixed(2)}
                      {i === 0 && <span style={{ fontSize: 10, color: '#16a34a', marginLeft: 6, fontWeight: 600 }}>BEST</span>}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ============ 3. SHIPMENTS ============

function ShipmentsSection() {
  const [filter, setFilter] = useState<ShipmentStatus | 'all'>('all');
  const [search, setSearch] = useState('');

  const filtered = MOCK_SHIPMENTS.filter(s => {
    if (filter !== 'all' && s.status !== filter) return false;
    if (search && !s.recipient.toLowerCase().includes(search.toLowerCase()) && !s.trackingNumber.includes(search)) return false;
    return true;
  });

  const statusCounts = {
    all: MOCK_SHIPMENTS.length,
    label_created: MOCK_SHIPMENTS.filter(s => s.status === 'label_created').length,
    in_transit: MOCK_SHIPMENTS.filter(s => s.status === 'in_transit').length,
    out_for_delivery: MOCK_SHIPMENTS.filter(s => s.status === 'out_for_delivery').length,
    delivered: MOCK_SHIPMENTS.filter(s => s.status === 'delivered').length,
    exception: MOCK_SHIPMENTS.filter(s => s.status === 'exception').length,
  };

  return (
    <div style={{ padding: 24 }}>
      <SectionHeader title="Shipments" subtitle={`${MOCK_SHIPMENTS.length} total shipments`} />

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1" style={{ maxWidth: 300 }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: 10, color: '#999' }} />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search by name or tracking #"
            style={{ width: '100%', padding: '8px 12px 8px 30px', borderRadius: 10, border: '1px solid #ddd', fontSize: 13, background: '#fff', outline: 'none' }} />
        </div>
        <div className="flex gap-1.5">
          {(['all', 'label_created', 'in_transit', 'out_for_delivery', 'delivered', 'exception'] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className="cursor-pointer"
              style={{
                padding: '6px 12px', borderRadius: 8, fontSize: 11, fontWeight: filter === f ? 700 : 500,
                background: filter === f ? ACCENT_BG : '#fff',
                color: filter === f ? ACCENT : '#666',
                border: filter === f ? `1.5px solid ${ACCENT_BORDER}` : '1px solid #ddd',
              }}>
              {f === 'all' ? 'All' : STATUS_CONFIG[f].label} ({statusCounts[f]})
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #ece8e0', background: '#fafaf8' }}>
              {['Tracking #', 'Recipient', 'Carrier', 'Service', 'Status', 'Date', 'Cost'].map(h => (
                <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map(s => (
              <tr key={s.id} style={{ borderBottom: '1px solid #f0ede8' }}
                onMouseEnter={e => (e.currentTarget.style.background = '#fafaf8')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                <td style={{ padding: '10px 14px' }}>
                  <span style={{ fontSize: 12, fontFamily: 'monospace', color: ACCENT, fontWeight: 500 }}>{s.trackingNumber.slice(0, 16)}...</span>
                </td>
                <td style={{ padding: '10px 14px' }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{s.recipient}</div>
                  <div style={{ fontSize: 11, color: '#999' }}>{s.recipientCity}, {s.recipientState}</div>
                </td>
                <td style={{ padding: '10px 14px' }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: CARRIER_COLORS[s.carrier] }}>{s.carrier}</span>
                </td>
                <td style={{ padding: '10px 14px', fontSize: 12, color: '#666' }}>{s.service}</td>
                <td style={{ padding: '10px 14px' }}><StatusBadge status={s.status} /></td>
                <td style={{ padding: '10px 14px', fontSize: 12, color: '#666' }}>{s.date}</td>
                <td style={{ padding: '10px 14px', fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>${s.cost.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div style={{ padding: 40, textAlign: 'center', color: '#999', fontSize: 13 }}>No shipments match your filter.</div>
        )}
      </div>
    </div>
  );
}

// ============ 4. TRACKING ============

function TrackingSection() {
  const [trackingInput, setTrackingInput] = useState('');
  const [tracked, setTracked] = useState<Shipment | null>(null);
  const [notFound, setNotFound] = useState(false);

  const handleTrack = () => {
    const found = MOCK_SHIPMENTS.find(s => s.trackingNumber === trackingInput.trim());
    if (found) { setTracked(found); setNotFound(false); }
    else { setTracked(null); setNotFound(true); }
  };

  const timelineSteps: { status: ShipmentStatus; label: string; detail: string }[] = [
    { status: 'label_created', label: 'Label Created', detail: 'Shipping label has been created' },
    { status: 'in_transit', label: 'In Transit', detail: 'Package picked up by carrier' },
    { status: 'out_for_delivery', label: 'Out for Delivery', detail: 'On the delivery vehicle' },
    { status: 'delivered', label: 'Delivered', detail: 'Package delivered to recipient' },
  ];

  const statusOrder: ShipmentStatus[] = ['label_created', 'in_transit', 'out_for_delivery', 'delivered'];
  const currentIndex = tracked ? statusOrder.indexOf(tracked.status === 'exception' ? 'in_transit' : tracked.status) : -1;

  return (
    <div style={{ padding: 24 }}>
      <SectionHeader title="Track a Package" subtitle="Enter a tracking number to see package progress" />

      <div className="empire-card mb-6" style={{ padding: '20px 22px' }}>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Hash size={14} style={{ position: 'absolute', left: 12, top: 12, color: '#999' }} />
            <input value={trackingInput} onChange={e => setTrackingInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleTrack()}
              placeholder="Enter tracking number..."
              style={{ width: '100%', padding: '10px 14px 10px 32px', borderRadius: 10, border: '1px solid #ddd', fontSize: 14, background: '#fff', outline: 'none' }} />
          </div>
          <button onClick={handleTrack}
            className="flex items-center gap-2 cursor-pointer"
            style={{ padding: '10px 24px', borderRadius: 10, border: 'none', background: ACCENT, color: '#fff', fontSize: 13, fontWeight: 600 }}>
            <Search size={15} /> Track
          </button>
        </div>
        <div style={{ fontSize: 11, color: '#999', marginTop: 8 }}>
          Try: <button onClick={() => setTrackingInput('9400111899223847561234')} className="cursor-pointer" style={{ color: ACCENT, background: 'none', border: 'none', fontSize: 11, fontWeight: 600, textDecoration: 'underline' }}>9400111899223847561234</button>
          {' '} or <button onClick={() => setTrackingInput('1Z999AA10123456784')} className="cursor-pointer" style={{ color: ACCENT, background: 'none', border: 'none', fontSize: 11, fontWeight: 600, textDecoration: 'underline' }}>1Z999AA10123456784</button>
        </div>
      </div>

      {notFound && (
        <div className="empire-card" style={{ padding: '20px 22px', borderColor: '#fca5a5' }}>
          <div className="flex items-center gap-2" style={{ color: '#dc2626' }}>
            <AlertTriangle size={16} />
            <span style={{ fontSize: 14, fontWeight: 600 }}>Tracking number not found</span>
          </div>
          <p style={{ fontSize: 12, color: '#999', marginTop: 4 }}>Please check the tracking number and try again.</p>
        </div>
      )}

      {tracked && (
        <>
          {/* Package Info */}
          <div className="empire-card mb-6" style={{ padding: '20px 22px' }}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a' }}>{tracked.recipient}</div>
                <div style={{ fontSize: 12, color: '#999' }}>{tracked.recipientCity}, {tracked.recipientState} &middot; {tracked.carrier} {tracked.service}</div>
              </div>
              <StatusBadge status={tracked.status} />
            </div>
            <div className="grid grid-cols-4 gap-4" style={{ paddingTop: 12, borderTop: '1px solid #ece8e0' }}>
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5 }}>Tracking #</div>
                <div style={{ fontSize: 12, fontFamily: 'monospace', color: ACCENT, marginTop: 2 }}>{tracked.trackingNumber}</div>
              </div>
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5 }}>Ship Date</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', marginTop: 2 }}>{tracked.date}</div>
              </div>
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5 }}>Weight</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', marginTop: 2 }}>{tracked.weight} lbs</div>
              </div>
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5 }}>Cost</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', marginTop: 2 }}>${tracked.cost.toFixed(2)}</div>
              </div>
            </div>
          </div>

          {/* Visual Timeline */}
          <div className="empire-card" style={{ padding: '24px 28px' }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 24 }}>Tracking Timeline</div>

            {tracked.status === 'exception' && (
              <div style={{ padding: '12px 16px', borderRadius: 10, background: '#fef2f2', border: '1px solid #fca5a5', marginBottom: 20 }}
                className="flex items-center gap-2">
                <AlertTriangle size={16} style={{ color: '#dc2626' }} />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#dc2626' }}>Delivery Exception</div>
                  <div style={{ fontSize: 11, color: '#999' }}>Address issue detected. Contact carrier for resolution.</div>
                </div>
              </div>
            )}

            <div className="flex flex-col gap-0">
              {timelineSteps.map((step, i) => {
                const isComplete = i <= currentIndex;
                const isCurrent = i === currentIndex;
                return (
                  <div key={step.status} className="flex items-start gap-4" style={{ position: 'relative', paddingBottom: i < timelineSteps.length - 1 ? 32 : 0 }}>
                    {/* Line */}
                    {i < timelineSteps.length - 1 && (
                      <div style={{
                        position: 'absolute', left: 15, top: 32, width: 2, height: 32,
                        background: i < currentIndex ? ACCENT : '#e5e7eb',
                      }} />
                    )}
                    {/* Dot */}
                    <div style={{
                      width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      background: isComplete ? ACCENT : '#f3f4f6',
                      color: isComplete ? '#fff' : '#9ca3af',
                      border: isCurrent ? `3px solid ${ACCENT_BORDER}` : '2px solid transparent',
                    }}>
                      {isComplete ? <Check size={14} /> : <CircleDot size={14} />}
                    </div>
                    {/* Text */}
                    <div style={{ paddingTop: 4 }}>
                      <div style={{ fontSize: 14, fontWeight: isCurrent ? 700 : isComplete ? 600 : 500, color: isComplete ? '#1a1a1a' : '#9ca3af' }}>{step.label}</div>
                      <div style={{ fontSize: 12, color: isComplete ? '#666' : '#ccc', marginTop: 1 }}>{step.detail}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ============ 5. RATES ============

function RatesSection() {
  const [originZip, setOriginZip] = useState('20001');
  const [destZip, setDestZip] = useState('');
  const [rLength, setRLength] = useState('12');
  const [rWidth, setRWidth] = useState('10');
  const [rHeight, setRHeight] = useState('6');
  const [rWeight, setRWeight] = useState('2');
  const [showResults, setShowResults] = useState(false);

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd',
    fontSize: 13, background: '#fff', outline: 'none',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 11, fontWeight: 600, color: '#666', marginBottom: 4, display: 'block', textTransform: 'uppercase', letterSpacing: 0.5,
  };

  const handleCalculate = () => {
    if (destZip && rWeight) setShowResults(true);
  };

  const wt = parseFloat(rWeight || '1');

  return (
    <div style={{ padding: 24 }}>
      <SectionHeader title="Rate Calculator" subtitle="Compare shipping rates across carriers" />

      <div className="empire-card mb-6" style={{ padding: '20px 22px' }}>
        <div className="grid grid-cols-6 gap-4 items-end">
          <div><label style={labelStyle}>Origin ZIP</label><input value={originZip} onChange={e => setOriginZip(e.target.value)} style={inputStyle} /></div>
          <div><label style={labelStyle}>Destination ZIP</label><input value={destZip} onChange={e => setDestZip(e.target.value)} placeholder="00000" style={inputStyle} /></div>
          <div><label style={labelStyle}>Length (in)</label><input value={rLength} onChange={e => setRLength(e.target.value)} style={inputStyle} type="number" /></div>
          <div><label style={labelStyle}>Width (in)</label><input value={rWidth} onChange={e => setRWidth(e.target.value)} style={inputStyle} type="number" /></div>
          <div><label style={labelStyle}>Height (in)</label><input value={rHeight} onChange={e => setRHeight(e.target.value)} style={inputStyle} type="number" /></div>
          <div><label style={labelStyle}>Weight (lbs)</label><input value={rWeight} onChange={e => setRWeight(e.target.value)} style={inputStyle} type="number" step="0.1" /></div>
        </div>
        <button onClick={handleCalculate}
          className="flex items-center gap-2 cursor-pointer mt-4"
          style={{ padding: '10px 24px', borderRadius: 10, border: 'none', background: ACCENT, color: '#fff', fontSize: 13, fontWeight: 600 }}>
          <Scale size={15} /> Calculate Rates
        </button>
      </div>

      {showResults && (
        <div className="grid grid-cols-4 gap-4">
          {CARRIERS.map(c => {
            const rates = MOCK_RATES.filter(r => r.carrier === c).sort((a, b) => a.price - b.price);
            return (
              <div key={c} className="empire-card" style={{ padding: '20px 22px' }}>
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: CARRIER_COLORS[c], color: '#fff' }}>
                    <Truck size={14} />
                  </div>
                  <span style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>{c}</span>
                </div>
                <div className="flex flex-col gap-2">
                  {rates.map((r, i) => (
                    <div key={r.service} style={{
                      padding: '10px 12px', borderRadius: 10,
                      border: i === 0 ? `1.5px solid ${ACCENT_BORDER}` : '1px solid #ece8e0',
                      background: i === 0 ? ACCENT_BG : '#fafaf8',
                    }}>
                      <div className="flex items-center justify-between">
                        <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{r.service}</span>
                        <span style={{ fontSize: 14, fontWeight: 700, color: i === 0 ? ACCENT : '#1a1a1a' }}>${(r.price * wt).toFixed(2)}</span>
                      </div>
                      <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>{r.days} business days</div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ============ 6. SETTINGS ============

function SettingsSection() {
  const [defaultFromName, setDefaultFromName] = useState('Empire HQ');
  const [defaultFromAddr, setDefaultFromAddr] = useState('1234 Business Ave');
  const [defaultFromCity, setDefaultFromCity] = useState('Washington');
  const [defaultFromState, setDefaultFromState] = useState('DC');
  const [defaultFromZip, setDefaultFromZip] = useState('20001');
  const [saved, setSaved] = useState(false);

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd',
    fontSize: 13, background: '#fff', outline: 'none',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 11, fontWeight: 600, color: '#666', marginBottom: 4, display: 'block', textTransform: 'uppercase', letterSpacing: 0.5,
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div style={{ padding: 24 }}>
      <SectionHeader title="Settings" subtitle="Configure your shipping defaults and integrations" />

      {/* Default Ship-From */}
      <div className="empire-card mb-6" style={{ padding: '20px 22px' }}>
        <div className="flex items-center gap-2 mb-4">
          <MapPin size={16} style={{ color: ACCENT }} />
          <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Default Ship-From Address</span>
        </div>
        <div className="flex flex-col gap-3">
          <div><label style={labelStyle}>Name / Company</label><input value={defaultFromName} onChange={e => setDefaultFromName(e.target.value)} style={inputStyle} /></div>
          <div><label style={labelStyle}>Street Address</label><input value={defaultFromAddr} onChange={e => setDefaultFromAddr(e.target.value)} style={inputStyle} /></div>
          <div className="grid grid-cols-3 gap-3">
            <div><label style={labelStyle}>City</label><input value={defaultFromCity} onChange={e => setDefaultFromCity(e.target.value)} style={inputStyle} /></div>
            <div><label style={labelStyle}>State</label><input value={defaultFromState} onChange={e => setDefaultFromState(e.target.value)} style={inputStyle} /></div>
            <div><label style={labelStyle}>ZIP</label><input value={defaultFromZip} onChange={e => setDefaultFromZip(e.target.value)} style={inputStyle} /></div>
          </div>
        </div>
        <button onClick={handleSave}
          className="flex items-center gap-2 cursor-pointer mt-4"
          style={{ padding: '8px 20px', borderRadius: 10, border: 'none', background: saved ? '#16a34a' : ACCENT, color: '#fff', fontSize: 13, fontWeight: 600 }}>
          {saved ? <><CheckCircle size={15} /> Saved!</> : <><Check size={15} /> Save Address</>}
        </button>
      </div>

      {/* Carrier Accounts */}
      <div className="empire-card mb-6" style={{ padding: '20px 22px' }}>
        <div className="flex items-center gap-2 mb-4">
          <Truck size={16} style={{ color: ACCENT }} />
          <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Carrier Accounts</span>
        </div>
        <div className="flex flex-col gap-3">
          {CARRIERS.map(c => (
            <div key={c} style={{ padding: '12px 16px', borderRadius: 10, border: '1px solid #ece8e0', background: '#fafaf8' }}
              className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: CARRIER_COLORS[c], color: '#fff' }}>
                  <Truck size={14} />
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{c}</div>
                  <div style={{ fontSize: 11, color: '#999' }}>Account #{c === 'USPS' ? 'Stamps.com connected' : 'Not connected'}</div>
                </div>
              </div>
              <button className="cursor-pointer"
                style={{
                  padding: '6px 14px', borderRadius: 8, fontSize: 11, fontWeight: 600,
                  border: c === 'USPS' ? '1px solid #bbf7d0' : `1px solid ${ACCENT_BORDER}`,
                  background: c === 'USPS' ? '#dcfce7' : ACCENT_BG,
                  color: c === 'USPS' ? '#16a34a' : ACCENT,
                }}>
                {c === 'USPS' ? 'Connected' : 'Connect'}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Package Presets */}
      <div className="empire-card" style={{ padding: '20px 22px' }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Box size={16} style={{ color: ACCENT }} />
            <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Package Presets</span>
          </div>
          <button className="flex items-center gap-1 cursor-pointer"
            style={{ padding: '6px 14px', borderRadius: 8, fontSize: 11, fontWeight: 600, border: `1px solid ${ACCENT_BORDER}`, background: ACCENT_BG, color: ACCENT }}>
            <Plus size={13} /> Add Preset
          </button>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {PACKAGE_PRESETS.map(p => (
            <div key={p.name} style={{ padding: '12px 16px', borderRadius: 10, border: '1px solid #ece8e0', background: '#fafaf8' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', marginBottom: 4 }}>{p.name}</div>
              <div style={{ fontSize: 11, color: '#999' }}>{p.length}" x {p.width}" x {p.height}" &middot; {p.weight} lbs</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
