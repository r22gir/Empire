'use client';
import React, { useState } from 'react';
import {
  Heart, Calendar, ClipboardList, FileText, Pill, DollarSign, Users,
  Search, Plus, ChevronRight, Check, X, Loader2, AlertTriangle,
  Clock, Phone, Mail, User, Activity, Syringe, Stethoscope,
  PawPrint, Eye, Star, Filter, Download, Bell, RefreshCw, BookOpen, CreditCard
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';

// Use Activity as Thermometer substitute
const Thermometer = Activity;

const ACCENT = '#ef4444';
const ACCENT_BG = '#fef2f2';
const ACCENT_BORDER = '#fecaca';

const NAV_SECTIONS = [
  { id: 'dashboard', label: 'Dashboard', icon: Heart },
  { id: 'patients', label: 'Patients', icon: PawPrint },
  { id: 'appointments', label: 'Appointments', icon: Calendar },
  { id: 'records', label: 'Records', icon: FileText },
  { id: 'prescriptions', label: 'Prescriptions', icon: Pill },
  { id: 'billing', label: 'Billing', icon: DollarSign },
  { id: 'portal', label: 'Pet Portal', icon: Users },
  { id: 'payments', label: 'Payments', icon: CreditCard },
  { id: 'docs', label: 'Docs', icon: BookOpen },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

// ============ MOCK DATA ============

const MOCK_PATIENTS = [
  { id: 'P-001', name: 'Buddy', species: 'Dog', breed: 'Golden Retriever', age: '4 yrs', weight: '72 lbs', owner: 'Sarah Mitchell', ownerPhone: '(202) 555-0147', ownerEmail: 'sarah.m@email.com', lastVisit: '2026-03-05', alerts: [{ text: 'Vaccines Due', color: '#f59e0b' }], status: 'active' },
  { id: 'P-002', name: 'Luna', species: 'Cat', breed: 'Tabby', age: '3 yrs', weight: '9 lbs', owner: 'James Carter', ownerPhone: '(202) 555-0231', ownerEmail: 'jcarter@email.com', lastVisit: '2026-03-02', alerts: [{ text: 'Allergy', color: '#ef4444' }], status: 'active' },
  { id: 'P-003', name: 'Rex', species: 'Dog', breed: 'German Shepherd', age: '6 yrs', weight: '88 lbs', owner: 'Maria Lopez', ownerPhone: '(703) 555-0189', ownerEmail: 'mlopez@email.com', lastVisit: '2026-02-28', alerts: [{ text: 'Senior Care', color: '#8b5cf6' }], status: 'active' },
  { id: 'P-004', name: 'Milo', species: 'Cat', breed: 'Siamese', age: '2 yrs', weight: '8 lbs', owner: 'David Kim', ownerPhone: '(301) 555-0276', ownerEmail: 'dkim@email.com', lastVisit: '2026-03-08', alerts: [], status: 'active' },
  { id: 'P-005', name: 'Coco', species: 'Dog', breed: 'French Bulldog', age: '1 yr', weight: '24 lbs', owner: 'Emily Chen', ownerPhone: '(202) 555-0312', ownerEmail: 'echen@email.com', lastVisit: '2026-03-07', alerts: [{ text: 'Puppy Plan', color: '#16a34a' }], status: 'active' },
  { id: 'P-006', name: 'Kiwi', species: 'Bird', breed: 'Cockatiel', age: '5 yrs', weight: '0.2 lbs', owner: 'Amanda Park', ownerPhone: '(571) 555-0198', ownerEmail: 'apark@email.com', lastVisit: '2026-02-15', alerts: [{ text: 'Wing Trim Due', color: '#f59e0b' }], status: 'active' },
  { id: 'P-007', name: 'Spike', species: 'Reptile', breed: 'Bearded Dragon', age: '3 yrs', weight: '1.1 lbs', owner: 'Tom Garcia', ownerPhone: '(240) 555-0145', ownerEmail: 'tgarcia@email.com', lastVisit: '2026-01-20', alerts: [], status: 'active' },
  { id: 'P-008', name: 'Daisy', species: 'Dog', breed: 'Labrador', age: '8 yrs', weight: '65 lbs', owner: 'Karen Wilson', ownerPhone: '(202) 555-0467', ownerEmail: 'kwilson@email.com', lastVisit: '2026-03-01', alerts: [{ text: 'Arthritis Mgmt', color: '#ef4444' }, { text: 'Senior Care', color: '#8b5cf6' }], status: 'active' },
];

const MOCK_APPOINTMENTS = [
  { id: 'A-001', date: '2026-03-09', time: '09:00 AM', patient: 'Buddy', owner: 'Sarah Mitchell', reason: 'Vaccination', vet: 'Dr. Rivera', status: 'confirmed', species: 'Dog' },
  { id: 'A-002', date: '2026-03-09', time: '09:30 AM', patient: 'Luna', owner: 'James Carter', reason: 'Checkup', vet: 'Dr. Rivera', status: 'checked-in', species: 'Cat' },
  { id: 'A-003', date: '2026-03-09', time: '10:00 AM', patient: 'Rex', owner: 'Maria Lopez', reason: 'Surgery', vet: 'Dr. Patel', status: 'in-progress', species: 'Dog' },
  { id: 'A-004', date: '2026-03-09', time: '10:30 AM', patient: 'Coco', owner: 'Emily Chen', reason: 'Vaccination', vet: 'Dr. Rivera', status: 'confirmed', species: 'Dog' },
  { id: 'A-005', date: '2026-03-09', time: '11:00 AM', patient: 'Milo', owner: 'David Kim', reason: 'Grooming', vet: 'Tech. Adams', status: 'confirmed', species: 'Cat' },
  { id: 'A-006', date: '2026-03-09', time: '11:30 AM', patient: 'Kiwi', owner: 'Amanda Park', reason: 'Checkup', vet: 'Dr. Patel', status: 'confirmed', species: 'Bird' },
  { id: 'A-007', date: '2026-03-09', time: '01:00 PM', patient: 'Daisy', owner: 'Karen Wilson', reason: 'Checkup', vet: 'Dr. Rivera', status: 'confirmed', species: 'Dog' },
  { id: 'A-008', date: '2026-03-10', time: '09:00 AM', patient: 'Spike', owner: 'Tom Garcia', reason: 'Checkup', vet: 'Dr. Patel', status: 'scheduled', species: 'Reptile' },
  { id: 'A-009', date: '2026-03-10', time: '10:00 AM', patient: 'Buddy', owner: 'Sarah Mitchell', reason: 'Emergency', vet: 'Dr. Rivera', status: 'scheduled', species: 'Dog' },
];

const MOCK_RECORDS: Record<string, any> = {
  'P-001': {
    visits: [
      { date: '2026-03-05', reason: 'Annual Checkup', vet: 'Dr. Rivera', notes: 'Healthy weight, good vitals. Recommend dental cleaning in 6 months.', vitals: { temp: '101.2°F', hr: '90 bpm', rr: '18/min', weight: '72 lbs' } },
      { date: '2026-01-12', reason: 'Ear Infection', vet: 'Dr. Patel', notes: 'Left ear inflamed. Prescribed Otomax drops 2x daily for 14 days.', vitals: { temp: '102.0°F', hr: '95 bpm', rr: '20/min', weight: '71 lbs' } },
      { date: '2025-09-20', reason: 'Vaccination', vet: 'Dr. Rivera', notes: 'Rabies booster, DHPP administered. No adverse reactions.', vitals: { temp: '101.5°F', hr: '88 bpm', rr: '16/min', weight: '70 lbs' } },
    ],
    vaccinations: [
      { name: 'Rabies', date: '2025-09-20', nextDue: '2026-09-20', status: 'current' },
      { name: 'DHPP', date: '2025-09-20', nextDue: '2026-09-20', status: 'current' },
      { name: 'Bordetella', date: '2025-06-15', nextDue: '2026-06-15', status: 'current' },
      { name: 'Leptospirosis', date: '2025-03-10', nextDue: '2026-03-10', status: 'due-soon' },
    ],
    labResults: [
      { date: '2026-03-05', test: 'CBC Panel', result: 'Normal', notes: 'All values within range' },
      { date: '2026-03-05', test: 'Heartworm Test', result: 'Negative', notes: '' },
      { date: '2025-09-20', test: 'Fecal Exam', result: 'Negative', notes: 'No parasites detected' },
    ],
  },
  'P-002': {
    visits: [
      { date: '2026-03-02', reason: 'Allergy Followup', vet: 'Dr. Rivera', notes: 'Skin irritation improved. Continue hypoallergenic diet. Recheck in 4 weeks.', vitals: { temp: '100.8°F', hr: '140 bpm', rr: '24/min', weight: '9 lbs' } },
      { date: '2026-01-28', reason: 'Dermatology', vet: 'Dr. Patel', notes: 'Suspected food allergy. Started elimination diet. Prescribed antihistamine.', vitals: { temp: '101.0°F', hr: '145 bpm', rr: '22/min', weight: '9.2 lbs' } },
    ],
    vaccinations: [
      { name: 'Rabies', date: '2025-11-10', nextDue: '2026-11-10', status: 'current' },
      { name: 'FVRCP', date: '2025-11-10', nextDue: '2026-11-10', status: 'current' },
      { name: 'FeLV', date: '2025-05-20', nextDue: '2026-05-20', status: 'current' },
    ],
    labResults: [
      { date: '2026-03-02', test: 'Allergy Panel', result: 'Positive - Chicken, Grain', notes: 'Avoid chicken-based food' },
    ],
  },
};

const MOCK_PRESCRIPTIONS = [
  { id: 'RX-001', patient: 'Buddy', medication: 'Heartgard Plus', dosage: '68-136 lbs', frequency: 'Monthly', startDate: '2026-01-01', endDate: '2026-12-31', refills: 9, status: 'active' },
  { id: 'RX-002', patient: 'Luna', medication: 'Apoquel 5.4mg', dosage: '1 tablet', frequency: 'Daily', startDate: '2026-01-28', endDate: '2026-04-28', refills: 2, status: 'active' },
  { id: 'RX-003', patient: 'Rex', medication: 'Carprofen 75mg', dosage: '1 tablet', frequency: 'Twice daily', startDate: '2026-02-15', endDate: '2026-05-15', refills: 1, status: 'active' },
  { id: 'RX-004', patient: 'Buddy', medication: 'Otomax Drops', dosage: '8 drops', frequency: 'Twice daily', startDate: '2026-01-12', endDate: '2026-01-26', refills: 0, status: 'completed' },
  { id: 'RX-005', patient: 'Daisy', medication: 'Rimadyl 100mg', dosage: '1 tablet', frequency: 'Daily', startDate: '2026-02-01', endDate: '2026-08-01', refills: 3, status: 'active' },
  { id: 'RX-006', patient: 'Coco', medication: 'Nexgard 10-24 lbs', dosage: '1 chewable', frequency: 'Monthly', startDate: '2026-03-01', endDate: '2027-03-01', refills: 10, status: 'active' },
  { id: 'RX-007', patient: 'Daisy', medication: 'Glucosamine Supplement', dosage: '500mg', frequency: 'Daily', startDate: '2026-01-15', endDate: '2026-07-15', refills: 4, status: 'active' },
];

const MOCK_INVOICES = [
  { id: 'INV-001', owner: 'Sarah Mitchell', patient: 'Buddy', services: ['Annual Exam', 'CBC Panel', 'Heartworm Test'], amount: 285, date: '2026-03-05', status: 'paid' },
  { id: 'INV-002', owner: 'James Carter', patient: 'Luna', services: ['Allergy Followup', 'Allergy Panel'], amount: 195, date: '2026-03-02', status: 'paid' },
  { id: 'INV-003', owner: 'Maria Lopez', patient: 'Rex', services: ['Surgery Consult', 'Pre-Op Bloodwork'], amount: 420, date: '2026-02-28', status: 'pending' },
  { id: 'INV-004', owner: 'Emily Chen', patient: 'Coco', services: ['Puppy Exam', 'Vaccination (DHPP)', 'Fecal Exam'], amount: 210, date: '2026-03-07', status: 'paid' },
  { id: 'INV-005', owner: 'Karen Wilson', patient: 'Daisy', services: ['Senior Wellness Exam', 'Arthritis Consult', 'X-Ray'], amount: 375, date: '2026-03-01', status: 'overdue' },
  { id: 'INV-006', owner: 'David Kim', patient: 'Milo', services: ['Wellness Exam', 'Nail Trim'], amount: 95, date: '2026-03-08', status: 'paid' },
  { id: 'INV-007', owner: 'Amanda Park', patient: 'Kiwi', services: ['Avian Exam', 'Wing Trim'], amount: 120, date: '2026-02-15', status: 'paid' },
  { id: 'INV-008', owner: 'Maria Lopez', patient: 'Rex', services: ['Hip Surgery', 'Anesthesia', 'Post-Op Meds'], amount: 2850, date: '2026-03-09', status: 'pending' },
];

const APPT_STATUS_COLORS: Record<string, { bg: string; color: string; label: string }> = {
  scheduled: { bg: '#f3f4f6', color: '#6b7280', label: 'Scheduled' },
  confirmed: { bg: '#dbeafe', color: '#2563eb', label: 'Confirmed' },
  'checked-in': { bg: '#fdf8eb', color: '#b8960c', label: 'Checked In' },
  'in-progress': { bg: '#fef2f2', color: '#ef4444', label: 'In Progress' },
  completed: { bg: '#dcfce7', color: '#16a34a', label: 'Completed' },
  cancelled: { bg: '#f3f4f6', color: '#9ca3af', label: 'Cancelled' },
  'no-show': { bg: '#fef2f2', color: '#dc2626', label: 'No Show' },
};

const REASON_COLORS: Record<string, { bg: string; color: string }> = {
  Checkup: { bg: '#dbeafe', color: '#2563eb' },
  Vaccination: { bg: '#dcfce7', color: '#16a34a' },
  Surgery: { bg: '#fef2f2', color: '#ef4444' },
  Emergency: { bg: '#fef2f2', color: '#dc2626' },
  Grooming: { bg: '#fdf8eb', color: '#b8960c' },
};

const INVOICE_STATUS_COLORS: Record<string, { bg: string; color: string; label: string }> = {
  paid: { bg: '#dcfce7', color: '#16a34a', label: 'Paid' },
  pending: { bg: '#fdf8eb', color: '#b8960c', label: 'Pending' },
  overdue: { bg: '#fef2f2', color: '#ef4444', label: 'Overdue' },
};

const VACC_STATUS_COLORS: Record<string, { bg: string; color: string; label: string }> = {
  current: { bg: '#dcfce7', color: '#16a34a', label: 'Current' },
  'due-soon': { bg: '#fdf8eb', color: '#b8960c', label: 'Due Soon' },
  overdue: { bg: '#fef2f2', color: '#ef4444', label: 'Overdue' },
};

const RX_STATUS_COLORS: Record<string, { bg: string; color: string; label: string }> = {
  active: { bg: '#dcfce7', color: '#16a34a', label: 'Active' },
  completed: { bg: '#f3f4f6', color: '#6b7280', label: 'Completed' },
  refill: { bg: '#fdf8eb', color: '#b8960c', label: 'Refill Needed' },
};

const SPECIES_ICONS: Record<string, string> = {
  Dog: '🐕',
  Cat: '🐈',
  Bird: '🐦',
  Reptile: '🦎',
};

// ============ MAIN COMPONENT ============

export default function PetForgePage() {
  const [section, setSection] = useState<Section>('dashboard');

  const renderContent = () => {
    switch (section) {
      case 'dashboard': return <DashboardSection onNavigate={setSection} />;
      case 'patients': return <PatientsSection />;
      case 'appointments': return <AppointmentsSection />;
      case 'records': return <RecordsSection />;
      case 'prescriptions': return <PrescriptionsSection />;
      case 'billing': return <BillingSection />;
      case 'portal': return <PetPortalSection />;
      case 'payments': return <PaymentModule product="petforge" />;
      case 'docs': return <div style={{ padding: 24 }}><ProductDocs product="vetforge" /></div>;
      default: return <DashboardSection onNavigate={setSection} />;
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      <nav style={{ width: 200, background: '#fff', borderRight: '1px solid #ece8e0', flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '18px 16px', borderBottom: '1px solid #ece8e0' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: ACCENT_BG }}>
              <Heart size={18} style={{ color: ACCENT }} />
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>PetForge</div>
              <div style={{ fontSize: 10, color: '#999' }}>Veterinary Practice</div>
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

// ============ 1. DASHBOARD ============

function DashboardSection({ onNavigate }: { onNavigate: (s: Section) => void }) {
  const todayAppts = MOCK_APPOINTMENTS.filter(a => a.date === '2026-03-09');
  const patientsSeenToday = todayAppts.filter(a => a.status === 'completed' || a.status === 'in-progress').length;
  const revenueToday = MOCK_INVOICES.filter(i => i.date === '2026-03-09').reduce((sum, i) => sum + i.amount, 0);
  const vaccinesDue = MOCK_PATIENTS.filter(p => p.alerts.some(a => a.text.includes('Vaccines Due'))).length;

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center gap-3 mb-1">
        <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>PetForge</h1>
        <span style={{ fontSize: 13, color: '#aaa' }} suppressHydrationWarning>
          {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
        </span>
      </div>

      <div className="grid grid-cols-4 gap-3 mt-5 mb-6">
        <KPI icon={<Calendar size={18} />} iconBg="#dbeafe" iconColor="#2563eb" label="Today's Appts" value={String(todayAppts.length)} sub="Scheduled today" onClick={() => onNavigate('appointments')} />
        <KPI icon={<Stethoscope size={18} />} iconBg="#dcfce7" iconColor="#16a34a" label="Patients Seen" value={String(patientsSeenToday)} sub="Today" />
        <KPI icon={<DollarSign size={18} />} iconBg={ACCENT_BG} iconColor={ACCENT} label="Revenue Today" value={`$${revenueToday.toLocaleString()}`} sub="Invoiced" onClick={() => onNavigate('billing')} />
        <KPI icon={<Syringe size={18} />} iconBg="#fdf8eb" iconColor="#b8960c" label="Vaccines Due" value={String(vaccinesDue)} sub="Patients need attention" onClick={() => onNavigate('patients')} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Today's Schedule */}
        <div className="empire-card">
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }} className="flex items-center gap-2">
            <Calendar size={15} style={{ color: ACCENT }} /> Today&apos;s Schedule
          </h3>
          <div className="space-y-2">
            {todayAppts.map((a, i) => {
              const st = APPT_STATUS_COLORS[a.status] || APPT_STATUS_COLORS.scheduled;
              const rc = REASON_COLORS[a.reason] || { bg: '#f3f4f6', color: '#6b7280' };
              return (
                <div key={i} style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0' }}
                  className="hover:border-[#ef4444] hover:bg-[#fef2f2] transition-all cursor-pointer flex items-center justify-between">
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{a.time} &mdash; {a.patient} {SPECIES_ICONS[a.species] || ''}</div>
                    <div style={{ fontSize: 10, color: '#777' }}>{a.owner} &middot; {a.vet}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: rc.bg, color: rc.color, fontWeight: 600 }}>{a.reason}</span>
                    <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: st.bg, color: st.color, fontWeight: 600 }}>{st.label}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Patient Alerts */}
        <div className="empire-card">
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }} className="flex items-center gap-2">
            <AlertTriangle size={15} style={{ color: '#f59e0b' }} /> Patient Alerts
          </h3>
          <div className="space-y-2">
            {MOCK_PATIENTS.filter(p => p.alerts.length > 0).map((p, i) => (
              <div key={i} style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0' }}
                className="hover:border-[#ef4444] hover:bg-[#fef2f2] transition-all cursor-pointer flex items-center justify-between">
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{SPECIES_ICONS[p.species] || ''} {p.name}</div>
                  <div style={{ fontSize: 10, color: '#777' }}>{p.breed} &middot; {p.owner}</div>
                </div>
                <div className="flex items-center gap-1">
                  {p.alerts.map((a, j) => (
                    <span key={j} style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: a.color + '18', color: a.color, fontWeight: 600 }}>{a.text}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Invoices */}
        <div className="empire-card">
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }} className="flex items-center gap-2">
            <DollarSign size={15} style={{ color: '#16a34a' }} /> Recent Invoices
          </h3>
          <div className="space-y-2">
            {MOCK_INVOICES.slice(0, 5).map((inv, i) => {
              const st = INVOICE_STATUS_COLORS[inv.status] || INVOICE_STATUS_COLORS.pending;
              return (
                <div key={i} style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0' }}
                  className="hover:border-[#ef4444] hover:bg-[#fef2f2] transition-all cursor-pointer flex items-center justify-between">
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{inv.patient} &mdash; {inv.owner}</div>
                    <div style={{ fontSize: 10, color: '#777' }}>{inv.services.join(', ')}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: st.bg, color: st.color, fontWeight: 600 }}>{st.label}</span>
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>${inv.amount}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Active Prescriptions */}
        <div className="empire-card">
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }} className="flex items-center gap-2">
            <Pill size={15} style={{ color: '#8b5cf6' }} /> Active Prescriptions
          </h3>
          <div className="space-y-2">
            {MOCK_PRESCRIPTIONS.filter(rx => rx.status === 'active').slice(0, 5).map((rx, i) => (
              <div key={i} style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0' }}
                className="hover:border-[#ef4444] hover:bg-[#fef2f2] transition-all cursor-pointer flex items-center justify-between">
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{rx.patient} &mdash; {rx.medication}</div>
                  <div style={{ fontSize: 10, color: '#777' }}>{rx.dosage} &middot; {rx.frequency}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span style={{ fontSize: 10, color: '#999' }}>{rx.refills} refills</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============ 2. PATIENTS ============

function PatientsSection() {
  const [search, setSearch] = useState('');
  const [speciesFilter, setSpeciesFilter] = useState<string>('all');

  const filtered = MOCK_PATIENTS.filter(p => {
    const matchSearch = !search || p.name.toLowerCase().includes(search.toLowerCase()) || p.owner.toLowerCase().includes(search.toLowerCase()) || p.breed.toLowerCase().includes(search.toLowerCase());
    const matchSpecies = speciesFilter === 'all' || p.species === speciesFilter;
    return matchSearch && matchSpecies;
  });

  return (
    <div style={{ maxWidth: 1060, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-5">
        <h2 style={{ fontSize: 20, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Patients</h2>
        <button style={{ padding: '8px 16px', borderRadius: 10, background: ACCENT, color: '#fff', fontSize: 12, fontWeight: 600, border: 'none', cursor: 'pointer' }}
          className="flex items-center gap-2"><Plus size={14} /> New Patient</button>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1">
          <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#999' }} />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search patients, owners, breeds..."
            style={{ width: '100%', padding: '9px 12px 9px 34px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 12, background: '#fff', outline: 'none' }} />
        </div>
        <select value={speciesFilter} onChange={e => setSpeciesFilter(e.target.value)}
          style={{ padding: '9px 14px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 12, background: '#fff', cursor: 'pointer' }}>
          <option value="all">All Species</option>
          <option value="Dog">Dog</option>
          <option value="Cat">Cat</option>
          <option value="Bird">Bird</option>
          <option value="Reptile">Reptile</option>
        </select>
      </div>

      <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: '#fafaf8', borderBottom: '1px solid #ece8e0' }}>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Patient</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Species</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Breed</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Age</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Weight</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Owner</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Last Visit</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Alerts</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((p, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #f0ede8' }}
                className="hover:bg-[#fef2f2] transition-all cursor-pointer">
                <td style={{ padding: '11px 14px', fontWeight: 600, color: '#1a1a1a' }}>
                  <span>{SPECIES_ICONS[p.species] || ''} {p.name}</span>
                </td>
                <td style={{ padding: '11px 14px', color: '#666' }}>{p.species}</td>
                <td style={{ padding: '11px 14px', color: '#666' }}>{p.breed}</td>
                <td style={{ padding: '11px 14px', color: '#666' }}>{p.age}</td>
                <td style={{ padding: '11px 14px', color: '#666' }}>{p.weight}</td>
                <td style={{ padding: '11px 14px', color: '#1a1a1a', fontWeight: 500 }}>{p.owner}</td>
                <td style={{ padding: '11px 14px', color: '#999' }}>{p.lastVisit}</td>
                <td style={{ padding: '11px 14px' }}>
                  <div className="flex items-center gap-1 flex-wrap">
                    {p.alerts.length === 0 && <span style={{ fontSize: 10, color: '#ccc' }}>&mdash;</span>}
                    {p.alerts.map((a, j) => (
                      <span key={j} style={{ fontSize: 9, padding: '2px 7px', borderRadius: 20, background: a.color + '18', color: a.color, fontWeight: 600 }}>{a.text}</span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============ 3. APPOINTMENTS ============

function AppointmentsSection() {
  const [dateFilter, setDateFilter] = useState('2026-03-09');
  const [statusFilter, setStatusFilter] = useState('all');

  const filtered = MOCK_APPOINTMENTS.filter(a => {
    const matchDate = !dateFilter || a.date === dateFilter;
    const matchStatus = statusFilter === 'all' || a.status === statusFilter;
    return matchDate && matchStatus;
  });

  return (
    <div style={{ maxWidth: 1060, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-5">
        <h2 style={{ fontSize: 20, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Appointments</h2>
        <button style={{ padding: '8px 16px', borderRadius: 10, background: ACCENT, color: '#fff', fontSize: 12, fontWeight: 600, border: 'none', cursor: 'pointer' }}
          className="flex items-center gap-2"><Plus size={14} /> New Appointment</button>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <input type="date" value={dateFilter} onChange={e => setDateFilter(e.target.value)}
          style={{ padding: '9px 14px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 12, background: '#fff' }} />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          style={{ padding: '9px 14px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 12, background: '#fff', cursor: 'pointer' }}>
          <option value="all">All Status</option>
          <option value="scheduled">Scheduled</option>
          <option value="confirmed">Confirmed</option>
          <option value="checked-in">Checked In</option>
          <option value="in-progress">In Progress</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: '#fafaf8', borderBottom: '1px solid #ece8e0' }}>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Time</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Patient</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Owner</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Reason</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Vet</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Status</th>
              <th style={{ padding: '11px 14px', textAlign: 'right', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((a, i) => {
              const st = APPT_STATUS_COLORS[a.status] || APPT_STATUS_COLORS.scheduled;
              const rc = REASON_COLORS[a.reason] || { bg: '#f3f4f6', color: '#6b7280' };
              return (
                <tr key={i} style={{ borderBottom: '1px solid #f0ede8' }}
                  className="hover:bg-[#fef2f2] transition-all cursor-pointer">
                  <td style={{ padding: '11px 14px', fontWeight: 600, color: '#1a1a1a' }}>{a.time}</td>
                  <td style={{ padding: '11px 14px', fontWeight: 600, color: '#1a1a1a' }}>{SPECIES_ICONS[a.species] || ''} {a.patient}</td>
                  <td style={{ padding: '11px 14px', color: '#666' }}>{a.owner}</td>
                  <td style={{ padding: '11px 14px' }}>
                    <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: rc.bg, color: rc.color, fontWeight: 600 }}>{a.reason}</span>
                  </td>
                  <td style={{ padding: '11px 14px', color: '#666' }}>{a.vet}</td>
                  <td style={{ padding: '11px 14px' }}>
                    <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: st.bg, color: st.color, fontWeight: 600 }}>{st.label}</span>
                  </td>
                  <td style={{ padding: '11px 14px', textAlign: 'right' }}>
                    <button style={{ padding: '4px 10px', borderRadius: 8, background: '#f5f3ef', border: '1px solid #ece8e0', fontSize: 10, color: '#666', cursor: 'pointer', fontWeight: 600 }}
                      className="hover:bg-[#fef2f2] hover:border-[#ef4444] hover:text-[#ef4444] transition-all">
                      View
                    </button>
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && (
              <tr><td colSpan={7} style={{ padding: 32, textAlign: 'center', color: '#999', fontSize: 12 }}>No appointments found</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============ 4. RECORDS ============

function RecordsSection() {
  const [selectedPatient, setSelectedPatient] = useState<string>('P-001');
  const [recordTab, setRecordTab] = useState<'visits' | 'vaccinations' | 'labs'>('visits');
  const patient = MOCK_PATIENTS.find(p => p.id === selectedPatient);
  const records = MOCK_RECORDS[selectedPatient];

  return (
    <div style={{ maxWidth: 1060, margin: '0 auto', padding: '24px 36px' }}>
      <h2 style={{ fontSize: 20, fontWeight: 600, color: '#1a1a1a', margin: '0 0 20px' }}>Medical Records</h2>

      <div className="flex gap-4">
        {/* Patient selector */}
        <div style={{ width: 220, flexShrink: 0 }}>
          <div className="empire-card" style={{ padding: '10px' }}>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', padding: '4px 8px', marginBottom: 4, letterSpacing: 1 }}>Select Patient</div>
            <div className="space-y-1">
              {MOCK_PATIENTS.filter(p => MOCK_RECORDS[p.id]).map(p => (
                <button key={p.id} onClick={() => { setSelectedPatient(p.id); setRecordTab('visits'); }}
                  className="w-full text-left transition-all"
                  style={{
                    padding: '8px 10px', borderRadius: 8, fontSize: 12, cursor: 'pointer',
                    fontWeight: selectedPatient === p.id ? 700 : 500,
                    background: selectedPatient === p.id ? ACCENT_BG : 'transparent',
                    color: selectedPatient === p.id ? ACCENT : '#666',
                    border: selectedPatient === p.id ? `1px solid ${ACCENT_BORDER}` : '1px solid transparent',
                  }}>
                  {SPECIES_ICONS[p.species] || ''} {p.name}
                  <div style={{ fontSize: 10, color: '#999', fontWeight: 400 }}>{p.breed}</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Records content */}
        <div className="flex-1">
          {patient && records ? (
            <>
              {/* Patient header */}
              <div className="empire-card mb-4" style={{ padding: '16px 20px' }}>
                <div className="flex items-center justify-between">
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a' }}>{SPECIES_ICONS[patient.species] || ''} {patient.name}</div>
                    <div style={{ fontSize: 12, color: '#777' }}>{patient.breed} &middot; {patient.age} &middot; {patient.weight} &middot; Owner: {patient.owner}</div>
                  </div>
                  <div className="flex items-center gap-1">
                    {patient.alerts.map((a, j) => (
                      <span key={j} style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: a.color + '18', color: a.color, fontWeight: 600 }}>{a.text}</span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex items-center gap-2 mb-4">
                {(['visits', 'vaccinations', 'labs'] as const).map(tab => (
                  <button key={tab} onClick={() => setRecordTab(tab)}
                    style={{
                      padding: '7px 16px', borderRadius: 10, fontSize: 12, fontWeight: recordTab === tab ? 700 : 500, cursor: 'pointer',
                      background: recordTab === tab ? ACCENT_BG : '#fff',
                      color: recordTab === tab ? ACCENT : '#666',
                      border: recordTab === tab ? `1.5px solid ${ACCENT_BORDER}` : '1.5px solid #ece8e0',
                    }}>
                    {tab === 'visits' ? 'Visit History' : tab === 'vaccinations' ? 'Vaccinations' : 'Lab Results'}
                  </button>
                ))}
              </div>

              {/* Visit History */}
              {recordTab === 'visits' && (
                <div className="space-y-3">
                  {records.visits.map((v: any, i: number) => (
                    <div key={i} className="empire-card" style={{ padding: '16px 20px' }}>
                      <div className="flex items-center justify-between mb-2">
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{v.reason}</div>
                        <div style={{ fontSize: 11, color: '#999' }}>{v.date} &middot; {v.vet}</div>
                      </div>
                      <div style={{ fontSize: 12, color: '#555', lineHeight: 1.6, marginBottom: 10 }}>{v.notes}</div>
                      <div className="flex items-center gap-4" style={{ fontSize: 10, color: '#999' }}>
                        <span>Temp: <b style={{ color: '#1a1a1a' }}>{v.vitals.temp}</b></span>
                        <span>HR: <b style={{ color: '#1a1a1a' }}>{v.vitals.hr}</b></span>
                        <span>RR: <b style={{ color: '#1a1a1a' }}>{v.vitals.rr}</b></span>
                        <span>Weight: <b style={{ color: '#1a1a1a' }}>{v.vitals.weight}</b></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Vaccinations */}
              {recordTab === 'vaccinations' && (
                <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                    <thead>
                      <tr style={{ background: '#fafaf8', borderBottom: '1px solid #ece8e0' }}>
                        <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Vaccine</th>
                        <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Date Given</th>
                        <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Next Due</th>
                        <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {records.vaccinations.map((v: any, i: number) => {
                        const st = VACC_STATUS_COLORS[v.status] || VACC_STATUS_COLORS.current;
                        return (
                          <tr key={i} style={{ borderBottom: '1px solid #f0ede8' }}>
                            <td style={{ padding: '11px 14px', fontWeight: 600, color: '#1a1a1a' }}>{v.name}</td>
                            <td style={{ padding: '11px 14px', color: '#666' }}>{v.date}</td>
                            <td style={{ padding: '11px 14px', color: '#666' }}>{v.nextDue}</td>
                            <td style={{ padding: '11px 14px' }}>
                              <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: st.bg, color: st.color, fontWeight: 600 }}>{st.label}</span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Lab Results */}
              {recordTab === 'labs' && (
                <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                    <thead>
                      <tr style={{ background: '#fafaf8', borderBottom: '1px solid #ece8e0' }}>
                        <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Date</th>
                        <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Test</th>
                        <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Result</th>
                        <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {records.labResults.map((l: any, i: number) => (
                        <tr key={i} style={{ borderBottom: '1px solid #f0ede8' }}>
                          <td style={{ padding: '11px 14px', color: '#666' }}>{l.date}</td>
                          <td style={{ padding: '11px 14px', fontWeight: 600, color: '#1a1a1a' }}>{l.test}</td>
                          <td style={{ padding: '11px 14px' }}>
                            <span style={{
                              fontSize: 10, padding: '3px 8px', borderRadius: 20, fontWeight: 600,
                              background: l.result.includes('Negative') || l.result === 'Normal' ? '#dcfce7' : '#fef2f2',
                              color: l.result.includes('Negative') || l.result === 'Normal' ? '#16a34a' : '#ef4444',
                            }}>{l.result}</span>
                          </td>
                          <td style={{ padding: '11px 14px', color: '#777', fontSize: 11 }}>{l.notes || '\u2014'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          ) : (
            <div className="empire-card" style={{ padding: 40, textAlign: 'center', color: '#999' }}>
              <FileText size={32} style={{ margin: '0 auto 12px', opacity: 0.3 }} />
              <div style={{ fontSize: 13 }}>Select a patient to view their medical records</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============ 5. PRESCRIPTIONS ============

function PrescriptionsSection() {
  const [statusFilter, setStatusFilter] = useState('all');
  const [search, setSearch] = useState('');

  const filtered = MOCK_PRESCRIPTIONS.filter(rx => {
    const matchStatus = statusFilter === 'all' || rx.status === statusFilter;
    const matchSearch = !search || rx.patient.toLowerCase().includes(search.toLowerCase()) || rx.medication.toLowerCase().includes(search.toLowerCase());
    return matchStatus && matchSearch;
  });

  return (
    <div style={{ maxWidth: 1060, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-5">
        <h2 style={{ fontSize: 20, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Prescriptions</h2>
        <button style={{ padding: '8px 16px', borderRadius: 10, background: ACCENT, color: '#fff', fontSize: 12, fontWeight: 600, border: 'none', cursor: 'pointer' }}
          className="flex items-center gap-2"><Plus size={14} /> New Prescription</button>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1">
          <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#999' }} />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search patient or medication..."
            style={{ width: '100%', padding: '9px 12px 9px 34px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 12, background: '#fff', outline: 'none' }} />
        </div>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          style={{ padding: '9px 14px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 12, background: '#fff', cursor: 'pointer' }}>
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: '#fafaf8', borderBottom: '1px solid #ece8e0' }}>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Patient</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Medication</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Dosage</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Frequency</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Start</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>End</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Refills</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((rx, i) => {
              const st = RX_STATUS_COLORS[rx.status] || RX_STATUS_COLORS.active;
              return (
                <tr key={i} style={{ borderBottom: '1px solid #f0ede8' }}
                  className="hover:bg-[#fef2f2] transition-all cursor-pointer">
                  <td style={{ padding: '11px 14px', fontWeight: 600, color: '#1a1a1a' }}>{rx.patient}</td>
                  <td style={{ padding: '11px 14px', fontWeight: 500, color: '#1a1a1a' }}>{rx.medication}</td>
                  <td style={{ padding: '11px 14px', color: '#666' }}>{rx.dosage}</td>
                  <td style={{ padding: '11px 14px', color: '#666' }}>{rx.frequency}</td>
                  <td style={{ padding: '11px 14px', color: '#999' }}>{rx.startDate}</td>
                  <td style={{ padding: '11px 14px', color: '#999' }}>{rx.endDate}</td>
                  <td style={{ padding: '11px 14px', color: '#666', fontWeight: 600 }}>{rx.refills}</td>
                  <td style={{ padding: '11px 14px' }}>
                    <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: st.bg, color: st.color, fontWeight: 600 }}>{st.label}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============ 6. BILLING ============

function BillingSection() {
  const [statusFilter, setStatusFilter] = useState('all');

  const filtered = MOCK_INVOICES.filter(inv => statusFilter === 'all' || inv.status === statusFilter);
  const totalRevenue = MOCK_INVOICES.filter(i => i.status === 'paid').reduce((sum, i) => sum + i.amount, 0);
  const totalPending = MOCK_INVOICES.filter(i => i.status === 'pending').reduce((sum, i) => sum + i.amount, 0);
  const totalOverdue = MOCK_INVOICES.filter(i => i.status === 'overdue').reduce((sum, i) => sum + i.amount, 0);

  return (
    <div style={{ maxWidth: 1060, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-5">
        <h2 style={{ fontSize: 20, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Billing</h2>
        <button style={{ padding: '8px 16px', borderRadius: 10, background: ACCENT, color: '#fff', fontSize: 12, fontWeight: 600, border: 'none', cursor: 'pointer' }}
          className="flex items-center gap-2"><Plus size={14} /> New Invoice</button>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-5">
        <KPI icon={<DollarSign size={18} />} iconBg="#dcfce7" iconColor="#16a34a" label="Collected" value={`$${totalRevenue.toLocaleString()}`} sub="Paid invoices" />
        <KPI icon={<Clock size={18} />} iconBg="#fdf8eb" iconColor="#b8960c" label="Pending" value={`$${totalPending.toLocaleString()}`} sub="Awaiting payment" />
        <KPI icon={<AlertTriangle size={18} />} iconBg={ACCENT_BG} iconColor={ACCENT} label="Overdue" value={`$${totalOverdue.toLocaleString()}`} sub="Past due" />
      </div>

      <div className="flex items-center gap-3 mb-4">
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          style={{ padding: '9px 14px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 12, background: '#fff', cursor: 'pointer' }}>
          <option value="all">All Status</option>
          <option value="paid">Paid</option>
          <option value="pending">Pending</option>
          <option value="overdue">Overdue</option>
        </select>
      </div>

      <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: '#fafaf8', borderBottom: '1px solid #ece8e0' }}>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Invoice</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Owner</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Patient</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Services</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Date</th>
              <th style={{ padding: '11px 14px', textAlign: 'right', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Amount</th>
              <th style={{ padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: '#999', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((inv, i) => {
              const st = INVOICE_STATUS_COLORS[inv.status] || INVOICE_STATUS_COLORS.pending;
              return (
                <tr key={i} style={{ borderBottom: '1px solid #f0ede8' }}
                  className="hover:bg-[#fef2f2] transition-all cursor-pointer">
                  <td style={{ padding: '11px 14px', fontWeight: 600, color: ACCENT }}>{inv.id}</td>
                  <td style={{ padding: '11px 14px', fontWeight: 500, color: '#1a1a1a' }}>{inv.owner}</td>
                  <td style={{ padding: '11px 14px', fontWeight: 500, color: '#1a1a1a' }}>{inv.patient}</td>
                  <td style={{ padding: '11px 14px', color: '#777', fontSize: 11 }}>{inv.services.join(', ')}</td>
                  <td style={{ padding: '11px 14px', color: '#999' }}>{inv.date}</td>
                  <td style={{ padding: '11px 14px', textAlign: 'right', fontWeight: 700, color: '#1a1a1a' }}>${inv.amount.toLocaleString()}</td>
                  <td style={{ padding: '11px 14px' }}>
                    <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: st.bg, color: st.color, fontWeight: 600 }}>{st.label}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============ 7. PET PORTAL ============

function PetPortalSection() {
  const [selectedOwner, setSelectedOwner] = useState('Sarah Mitchell');

  const owners = [...new Set(MOCK_PATIENTS.map(p => p.owner))];
  const ownerPatients = MOCK_PATIENTS.filter(p => p.owner === selectedOwner);
  const ownerAppts = MOCK_APPOINTMENTS.filter(a => a.owner === selectedOwner && a.date >= '2026-03-09');
  const ownerRx = MOCK_PRESCRIPTIONS.filter(rx => ownerPatients.some(p => p.name === rx.patient) && rx.status === 'active');
  const ownerInvoices = MOCK_INVOICES.filter(inv => inv.owner === selectedOwner);

  // Vaccination schedule for owner's pets
  const ownerVaccinations: { patient: string; vaccine: string; nextDue: string; status: string }[] = [];
  ownerPatients.forEach(p => {
    const recs = MOCK_RECORDS[p.id];
    if (recs?.vaccinations) {
      recs.vaccinations.forEach((v: any) => {
        ownerVaccinations.push({ patient: p.name, vaccine: v.name, nextDue: v.nextDue, status: v.status });
      });
    }
  });

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center gap-3 mb-5">
        <Users size={20} style={{ color: ACCENT }} />
        <h2 style={{ fontSize: 20, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Pet Portal</h2>
        <span style={{ fontSize: 11, color: '#999' }}>&mdash; Owner View</span>
      </div>

      {/* Owner selector */}
      <div className="flex items-center gap-3 mb-5">
        <span style={{ fontSize: 12, color: '#666', fontWeight: 500 }}>Viewing as:</span>
        <select value={selectedOwner} onChange={e => setSelectedOwner(e.target.value)}
          style={{ padding: '8px 14px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 12, background: '#fff', cursor: 'pointer', fontWeight: 600 }}>
          {owners.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      </div>

      {/* My Pets */}
      <div className="empire-card mb-4" style={{ padding: '16px 20px' }}>
        <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }} className="flex items-center gap-2">
          <PawPrint size={15} style={{ color: ACCENT }} /> My Pets
        </h3>
        <div className="grid grid-cols-3 gap-3">
          {ownerPatients.map((p, i) => (
            <div key={i} style={{ padding: '12px 14px', borderRadius: 10, border: '1px solid #ece8e0', background: '#fafaf8' }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>{SPECIES_ICONS[p.species] || ''} {p.name}</div>
              <div style={{ fontSize: 11, color: '#777' }}>{p.breed} &middot; {p.age} &middot; {p.weight}</div>
              <div className="flex items-center gap-1 mt-2">
                {p.alerts.map((a, j) => (
                  <span key={j} style={{ fontSize: 9, padding: '2px 7px', borderRadius: 20, background: a.color + '18', color: a.color, fontWeight: 600 }}>{a.text}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Upcoming Appointments */}
        <div className="empire-card" style={{ padding: '16px 20px' }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }} className="flex items-center gap-2">
            <Calendar size={15} style={{ color: '#2563eb' }} /> Upcoming Appointments
          </h3>
          {ownerAppts.length === 0 ? (
            <div style={{ fontSize: 12, color: '#999', padding: '16px 0', textAlign: 'center' }}>No upcoming appointments</div>
          ) : (
            <div className="space-y-2">
              {ownerAppts.map((a, i) => {
                const rc = REASON_COLORS[a.reason] || { bg: '#f3f4f6', color: '#6b7280' };
                return (
                  <div key={i} style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0' }}>
                    <div className="flex items-center justify-between">
                      <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{a.date} at {a.time}</div>
                      <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: rc.bg, color: rc.color, fontWeight: 600 }}>{a.reason}</span>
                    </div>
                    <div style={{ fontSize: 10, color: '#777', marginTop: 2 }}>{a.patient} &middot; {a.vet}</div>
                  </div>
                );
              })}
            </div>
          )}
          <button style={{ marginTop: 12, width: '100%', padding: '8px', borderRadius: 8, background: ACCENT_BG, border: `1px solid ${ACCENT_BORDER}`, color: ACCENT, fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>
            Request New Appointment
          </button>
        </div>

        {/* Vaccination Schedule */}
        <div className="empire-card" style={{ padding: '16px 20px' }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }} className="flex items-center gap-2">
            <Syringe size={15} style={{ color: '#16a34a' }} /> Vaccination Schedule
          </h3>
          {ownerVaccinations.length === 0 ? (
            <div style={{ fontSize: 12, color: '#999', padding: '16px 0', textAlign: 'center' }}>No vaccination records</div>
          ) : (
            <div className="space-y-2">
              {ownerVaccinations.map((v, i) => {
                const st = VACC_STATUS_COLORS[v.status] || VACC_STATUS_COLORS.current;
                return (
                  <div key={i} style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid #ece8e0' }}
                    className="flex items-center justify-between">
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{v.vaccine}</div>
                      <div style={{ fontSize: 10, color: '#777' }}>{v.patient} &middot; Due: {v.nextDue}</div>
                    </div>
                    <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: st.bg, color: st.color, fontWeight: 600 }}>{st.label}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Refill Requests */}
        <div className="empire-card" style={{ padding: '16px 20px' }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }} className="flex items-center gap-2">
            <Pill size={15} style={{ color: '#8b5cf6' }} /> Active Medications
          </h3>
          {ownerRx.length === 0 ? (
            <div style={{ fontSize: 12, color: '#999', padding: '16px 0', textAlign: 'center' }}>No active medications</div>
          ) : (
            <div className="space-y-2">
              {ownerRx.map((rx, i) => (
                <div key={i} style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0' }}
                  className="flex items-center justify-between">
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{rx.medication}</div>
                    <div style={{ fontSize: 10, color: '#777' }}>{rx.patient} &middot; {rx.dosage} &middot; {rx.frequency}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span style={{ fontSize: 10, color: '#999' }}>{rx.refills} refills left</span>
                    <button style={{ padding: '4px 10px', borderRadius: 8, background: ACCENT_BG, border: `1px solid ${ACCENT_BORDER}`, fontSize: 10, color: ACCENT, cursor: 'pointer', fontWeight: 600 }}>
                      Refill
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Invoices */}
        <div className="empire-card" style={{ padding: '16px 20px' }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }} className="flex items-center gap-2">
            <DollarSign size={15} style={{ color: '#16a34a' }} /> My Invoices
          </h3>
          <div className="space-y-2">
            {ownerInvoices.map((inv, i) => {
              const st = INVOICE_STATUS_COLORS[inv.status] || INVOICE_STATUS_COLORS.pending;
              return (
                <div key={i} style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid #ece8e0' }}
                  className="flex items-center justify-between">
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{inv.id} &mdash; {inv.patient}</div>
                    <div style={{ fontSize: 10, color: '#777' }}>{inv.date} &middot; {inv.services.join(', ')}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: st.bg, color: st.color, fontWeight: 600 }}>{st.label}</span>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a' }}>${inv.amount}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
