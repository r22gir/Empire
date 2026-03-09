'use client';
import React, { useState } from 'react';
import {
  Shield, FileText, Video, Users, Heart, CheckCircle, Clock, AlertTriangle,
  Star, Award, Search, Plus, ChevronRight, ChevronDown, Check, X,
  Phone, Mail, User, ExternalLink, Calendar,
  Activity, BookOpen, Scale, Clipboard, Eye,
  DollarSign, Globe, CreditCard
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';

const GOLD = '#b8960c';
const GOLD_BG = '#faf9f7';
const GOLD_BORDER = '#e8dcc8';
const NAVY = '#1e3a5f';
const NAVY_LIGHT = '#2c5282';
const NAVY_BG = '#edf2f7';

const NAV_SECTIONS = [
  { id: 'dashboard', label: 'Dashboard', icon: Activity },
  { id: 'claims', label: 'Claims', icon: FileText },
  { id: 'consultations', label: 'Consultations', icon: Video },
  { id: 'conditions', label: 'Conditions', icon: Heart },
  { id: 'providers', label: 'Providers', icon: Users },
  { id: 'compliance', label: 'Compliance', icon: Shield },
  { id: 'resources', label: 'Resources', icon: BookOpen },
  { id: 'payments', label: 'Payments', icon: CreditCard },
  { id: 'docs', label: 'Docs', icon: FileText },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

// ============ MOCK DATA ============

const MOCK_VETERANS = [
  { id: 'VET-1001', name: 'James Rodriguez', branch: 'Army', serviceYears: '2004-2012', state: 'TX', email: 'jrodriguez@email.com', phone: '(512) 555-0147' },
  { id: 'VET-1002', name: 'Michael Thompson', branch: 'Marines', serviceYears: '2008-2016', state: 'CA', email: 'mthompson@email.com', phone: '(619) 555-0231' },
  { id: 'VET-1003', name: 'Sarah Williams', branch: 'Air Force', serviceYears: '2010-2018', state: 'VA', email: 'swilliams@email.com', phone: '(703) 555-0189' },
  { id: 'VET-1004', name: 'David Chen', branch: 'Navy', serviceYears: '2006-2014', state: 'WA', email: 'dchen@email.com', phone: '(206) 555-0276' },
  { id: 'VET-1005', name: 'Robert Jackson', branch: 'Army', serviceYears: '2001-2009', state: 'FL', email: 'rjackson@email.com', phone: '(813) 555-0312' },
  { id: 'VET-1006', name: 'Amanda Martinez', branch: 'Coast Guard', serviceYears: '2012-2020', state: 'NC', email: 'amartinez@email.com', phone: '(919) 555-0198' },
  { id: 'VET-1007', name: 'Kevin Brown', branch: 'Marines', serviceYears: '2003-2011', state: 'OH', email: 'kbrown@email.com', phone: '(614) 555-0145' },
  { id: 'VET-1008', name: 'Patricia Davis', branch: 'Army', serviceYears: '2007-2015', state: 'GA', email: 'pdavis@email.com', phone: '(404) 555-0467' },
];

type ClaimStatus = 'filed' | 'pending' | 'approved' | 'denied' | 'appeal';

const MOCK_CLAIMS: {
  id: string; veteranId: string; veteranName: string; condition: string; ratingPercent: number | null;
  status: ClaimStatus; filedDate: string; lastUpdate: string; notes: string; branch: string;
}[] = [
  { id: 'CLM-2401', veteranId: 'VET-1001', veteranName: 'James Rodriguez', condition: 'PTSD', ratingPercent: 70, status: 'approved', filedDate: '2025-11-15', lastUpdate: '2026-02-20', notes: 'Combat-related PTSD. Nexus letter provided by Dr. Patel. Rating decision received.', branch: 'Army' },
  { id: 'CLM-2402', veteranId: 'VET-1002', veteranName: 'Michael Thompson', condition: 'Chronic Back Pain (Lumbar)', ratingPercent: null, status: 'pending', filedDate: '2026-01-10', lastUpdate: '2026-03-01', notes: 'Service-connected lumbar strain. Telehealth evaluation completed. Awaiting VA decision.', branch: 'Marines' },
  { id: 'CLM-2403', veteranId: 'VET-1003', veteranName: 'Sarah Williams', condition: 'Tinnitus', ratingPercent: 10, status: 'approved', filedDate: '2025-12-05', lastUpdate: '2026-02-15', notes: 'Bilateral tinnitus from flight line exposure. Standard 10% rating awarded.', branch: 'Air Force' },
  { id: 'CLM-2404', veteranId: 'VET-1004', veteranName: 'David Chen', condition: 'Sleep Apnea', ratingPercent: null, status: 'filed', filedDate: '2026-03-01', lastUpdate: '2026-03-01', notes: 'Initial claim filed. Sleep study results attached. Awaiting C&P exam scheduling.', branch: 'Navy' },
  { id: 'CLM-2405', veteranId: 'VET-1005', veteranName: 'Robert Jackson', condition: 'Depression / Anxiety', ratingPercent: 30, status: 'appeal', filedDate: '2025-08-20', lastUpdate: '2026-03-05', notes: 'Initial rating of 30%. Veteran believes symptoms warrant higher rating. Supplemental claim filed with new buddy statements.', branch: 'Army' },
  { id: 'CLM-2406', veteranId: 'VET-1006', veteranName: 'Amanda Martinez', condition: 'Migraine Headaches', ratingPercent: null, status: 'pending', filedDate: '2026-02-10', lastUpdate: '2026-03-03', notes: 'Prostrating migraines documented during service. Telehealth evaluation scheduled.', branch: 'Coast Guard' },
  { id: 'CLM-2407', veteranId: 'VET-1007', veteranName: 'Kevin Brown', condition: 'TBI Residuals', ratingPercent: null, status: 'denied', filedDate: '2025-09-15', lastUpdate: '2026-01-30', notes: 'Denied due to insufficient medical evidence linking current symptoms to service. Preparing appeal with additional documentation.', branch: 'Marines' },
  { id: 'CLM-2408', veteranId: 'VET-1008', veteranName: 'Patricia Davis', condition: 'Knee Condition (Bilateral)', ratingPercent: null, status: 'filed', filedDate: '2026-03-05', lastUpdate: '2026-03-05', notes: 'Bilateral knee instability from repeated ruck marches. Orthopedic records from service included.', branch: 'Army' },
  { id: 'CLM-2409', veteranId: 'VET-1001', veteranName: 'James Rodriguez', condition: 'Tinnitus', ratingPercent: 10, status: 'approved', filedDate: '2025-11-15', lastUpdate: '2026-02-20', notes: 'Secondary to PTSD claim. Bilateral tinnitus confirmed via audiogram.', branch: 'Army' },
  { id: 'CLM-2410', veteranId: 'VET-1005', veteranName: 'Robert Jackson', condition: 'Skin Condition (Eczema)', ratingPercent: null, status: 'pending', filedDate: '2026-02-25', lastUpdate: '2026-03-07', notes: 'Chronic eczema potentially related to chemical exposure during deployment. Dermatological telehealth evaluation completed.', branch: 'Army' },
];

type ConsultationStatus = 'scheduled' | 'in-progress' | 'completed' | 'cancelled' | 'no-show';

const MOCK_CONSULTATIONS: {
  id: string; veteranName: string; veteranId: string; provider: string; condition: string;
  date: string; time: string; platform: string; status: ConsultationStatus; notes: string; duration: string;
}[] = [
  { id: 'CON-301', veteranName: 'Michael Thompson', veteranId: 'VET-1002', provider: 'Dr. Angela Patel', condition: 'Chronic Back Pain', date: '2026-03-09', time: '10:00 AM', platform: 'Doxy.me', status: 'scheduled', notes: 'Initial evaluation for lumbar claim. Have veteran demonstrate range of motion.', duration: '45 min' },
  { id: 'CON-302', veteranName: 'Amanda Martinez', veteranId: 'VET-1006', provider: 'Dr. Robert Kim', condition: 'Migraine Headaches', date: '2026-03-09', time: '11:30 AM', platform: 'Doxy.me', status: 'scheduled', notes: 'Evaluate frequency and severity of prostrating migraines. Review headache journal.', duration: '30 min' },
  { id: 'CON-303', veteranName: 'Robert Jackson', veteranId: 'VET-1005', provider: 'Dr. Marcus Webb', condition: 'Depression / Anxiety', date: '2026-03-09', time: '02:00 PM', platform: 'Zoom Healthcare', status: 'scheduled', notes: 'Follow-up for supplemental claim. Reassess symptom severity using PHQ-9 and GAD-7.', duration: '60 min' },
  { id: 'CON-304', veteranName: 'David Chen', veteranId: 'VET-1004', provider: 'Dr. Lisa Tran', condition: 'Sleep Apnea', date: '2026-03-10', time: '09:00 AM', platform: 'Doxy.me', status: 'scheduled', notes: 'Review sleep study results. Evaluate for nexus opinion connecting to service.', duration: '30 min' },
  { id: 'CON-305', veteranName: 'James Rodriguez', veteranId: 'VET-1001', provider: 'Dr. Marcus Webb', condition: 'PTSD Follow-up', date: '2026-03-07', time: '01:00 PM', platform: 'Doxy.me', status: 'completed', notes: 'Quarterly follow-up. Veteran reports improved sleep with CPAP. PTSD symptoms stable on current medication.', duration: '45 min' },
  { id: 'CON-306', veteranName: 'Robert Jackson', veteranId: 'VET-1005', provider: 'Dr. Angela Patel', condition: 'Skin Condition', date: '2026-03-06', time: '03:30 PM', platform: 'Doxy.me', status: 'completed', notes: 'Dermatological evaluation via high-res video. Documented lesion locations and severity. Photos taken by veteran for record.', duration: '30 min' },
];

const MOCK_PROVIDERS = [
  { id: 'PRV-01', name: 'Dr. Angela Patel', credential: 'MD', specialty: 'Internal Medicine / Pain Management', licenseStates: ['TX', 'CA', 'FL', 'VA', 'NC'], imlc: true, rating: 4.9, reviewCount: 127, availability: 'Mon-Fri 9AM-5PM', phone: '(800) 555-0100', email: 'dr.patel@vetforge.com', bio: 'Board-certified internist with 12 years experience in VA disability evaluations. Specializes in musculoskeletal and chronic pain assessments.' },
  { id: 'PRV-02', name: 'Dr. Marcus Webb', credential: 'MD', specialty: 'Psychiatry', licenseStates: ['TX', 'CA', 'FL', 'VA', 'OH', 'GA', 'WA', 'NC'], imlc: true, rating: 4.8, reviewCount: 203, availability: 'Mon-Fri 8AM-6PM', phone: '(800) 555-0101', email: 'dr.webb@vetforge.com', bio: 'Psychiatrist with extensive experience evaluating PTSD, depression, anxiety, and TBI in veterans. Former VA staff psychiatrist.' },
  { id: 'PRV-03', name: 'Dr. Robert Kim', credential: 'DO', specialty: 'Neurology', licenseStates: ['CA', 'WA', 'TX', 'FL'], imlc: true, rating: 4.7, reviewCount: 89, availability: 'Tue-Sat 10AM-6PM', phone: '(800) 555-0102', email: 'dr.kim@vetforge.com', bio: 'Osteopathic neurologist specializing in TBI, migraines, tinnitus, and sleep disorders. 8 years of telehealth experience.' },
  { id: 'PRV-04', name: 'Dr. Lisa Tran', credential: 'NP', specialty: 'Pulmonology / Sleep Medicine', licenseStates: ['VA', 'NC', 'GA', 'FL', 'TX', 'OH'], imlc: false, rating: 4.9, reviewCount: 156, availability: 'Mon-Thu 8AM-4PM', phone: '(800) 555-0103', email: 'dr.tran@vetforge.com', bio: 'Nurse Practitioner specializing in respiratory conditions and sleep disorders. Certified in sleep medicine with 10 years clinical experience.' },
  { id: 'PRV-05', name: 'Dr. William Harris', credential: 'PA', specialty: 'Dermatology', licenseStates: ['TX', 'CA', 'FL', 'GA', 'NC', 'VA', 'OH', 'WA'], imlc: false, rating: 4.6, reviewCount: 74, availability: 'Mon-Fri 9AM-5PM', phone: '(800) 555-0104', email: 'dr.harris@vetforge.com', bio: 'Physician Assistant specializing in dermatological evaluations for service-connected skin conditions, scarring, and burn injuries.' },
];

const CONDITIONS_DATA = [
  {
    category: 'Mental Health',
    icon: Activity,
    color: NAVY,
    conditions: [
      { name: 'PTSD', suitability: 'telehealth', description: 'Post-Traumatic Stress Disorder evaluation via structured clinical interview. PHQ-PCL5 assessment.', commonRatings: '10%, 30%, 50%, 70%, 100%' },
      { name: 'Depression (Major Depressive Disorder)', suitability: 'telehealth', description: 'Evaluate using PHQ-9, clinical interview, and functional impact assessment.', commonRatings: '10%, 30%, 50%, 70%, 100%' },
      { name: 'Anxiety (Generalized Anxiety Disorder)', suitability: 'telehealth', description: 'GAD-7 screening and clinical interview. Assess occupational and social impairment.', commonRatings: '10%, 30%, 50%, 70%, 100%' },
      { name: 'TBI Residual Effects', suitability: 'hybrid', description: 'Cognitive and behavioral symptoms can be assessed via telehealth. Physical neurological exam may require in-person.', commonRatings: '10%, 40%, 70%, 100%' },
    ],
  },
  {
    category: 'Dermatological',
    icon: Eye,
    color: '#7c3aed',
    conditions: [
      { name: 'Eczema / Dermatitis', suitability: 'telehealth', description: 'Visual assessment via high-resolution video. Veteran photographs supplement evaluation.', commonRatings: '0%, 10%, 30%, 60%' },
      { name: 'Scarring (Service-Connected)', suitability: 'telehealth', description: 'Document scar dimensions, location, and functional impact via video.', commonRatings: '0%, 10%, 20%, 30%, 50%, 80%' },
      { name: 'Psoriasis', suitability: 'telehealth', description: 'Assess body surface area affected and treatment response via video.', commonRatings: '0%, 10%, 30%, 60%' },
    ],
  },
  {
    category: 'Respiratory',
    icon: Heart,
    color: '#059669',
    conditions: [
      { name: 'Asthma', suitability: 'hybrid', description: 'History and medication review via telehealth. PFT results required from local lab.', commonRatings: '10%, 30%, 60%, 100%' },
      { name: 'Sleep Apnea', suitability: 'telehealth', description: 'Review sleep study results, CPAP usage data. Evaluate functional impact.', commonRatings: '0%, 30%, 50%, 100%' },
    ],
  },
  {
    category: 'Chronic Pain',
    icon: AlertTriangle,
    color: '#dc2626',
    conditions: [
      { name: 'Back Conditions (Cervical/Lumbar)', suitability: 'hybrid', description: 'History and functional impact via telehealth. Range of motion may need in-person measurement or veteran self-measurement with guidance.', commonRatings: '10%, 20%, 30%, 40%, 50%' },
      { name: 'Joint Conditions (Knee, Shoulder, Hip)', suitability: 'hybrid', description: 'Functional limitation assessment via video. Formal ROM testing may require in-person.', commonRatings: '0%, 10%, 20%, 30%, 40%, 50%' },
      { name: 'Migraine Headaches', suitability: 'telehealth', description: 'Evaluate frequency, duration, and prostrating nature of attacks. Review headache journal.', commonRatings: '0%, 10%, 30%, 50%' },
    ],
  },
  {
    category: 'Other Common Conditions',
    icon: Clipboard,
    color: '#0891b2',
    conditions: [
      { name: 'Tinnitus', suitability: 'telehealth', description: 'Subjective report of ringing/buzzing. Audiogram results from local facility supplement claim.', commonRatings: '10%' },
      { name: 'Diabetes Mellitus (Type II)', suitability: 'telehealth', description: 'Review A1C labs, medication regimen, and activity restriction via telehealth.', commonRatings: '10%, 20%, 40%, 60%, 100%' },
      { name: 'Hypertension', suitability: 'telehealth', description: 'Review home blood pressure readings, medication history. Veteran takes readings at home.', commonRatings: '0%, 10%, 20%, 40%, 60%' },
    ],
  },
];

const COMPLIANCE_ITEMS: { id: string; category: string; item: string; status: 'complete' | 'in-progress' | 'not-started'; lastChecked: string; notes: string }[] = [
  { id: 'CMP-01', category: 'HIPAA', item: 'Business Associate Agreements (BAAs) signed with all vendors', status: 'complete', lastChecked: '2026-03-01', notes: 'BAAs in place with Doxy.me, AWS, and document storage provider.' },
  { id: 'CMP-02', category: 'HIPAA', item: 'End-to-end encryption verified (AES-256)', status: 'complete', lastChecked: '2026-03-01', notes: 'All data encrypted at rest and in transit. TLS 1.3 enforced.' },
  { id: 'CMP-03', category: 'HIPAA', item: 'Audit logging enabled for all PHI access', status: 'complete', lastChecked: '2026-03-05', notes: 'Comprehensive audit trail with user, timestamp, action, and resource.' },
  { id: 'CMP-04', category: 'HIPAA', item: 'Breach notification procedures documented', status: 'complete', lastChecked: '2026-02-15', notes: '60-day notification protocol established per HIPAA requirements.' },
  { id: 'CMP-05', category: 'HIPAA', item: 'Staff HIPAA training completed (annual)', status: 'in-progress', lastChecked: '2026-01-15', notes: '4 of 5 providers completed. Dr. Harris renewal due March 15.' },
  { id: 'CMP-06', category: 'Consent', item: 'Informed consent forms — all states current', status: 'complete', lastChecked: '2026-02-28', notes: 'State-specific consent forms updated for TX, CA, FL, VA, NC, GA, OH, WA.' },
  { id: 'CMP-07', category: 'Consent', item: 'Electronic signature system operational', status: 'complete', lastChecked: '2026-03-01', notes: 'DocuSign integration with HIPAA-compliant storage.' },
  { id: 'CMP-08', category: 'Consent', item: 'Telehealth limitations disclosure in consent', status: 'complete', lastChecked: '2026-02-28', notes: 'Plain language disclosure of telehealth limitations included in all consent forms.' },
  { id: 'CMP-09', category: 'Provider', item: 'All provider licenses verified (primary source)', status: 'complete', lastChecked: '2026-03-01', notes: 'All 5 providers verified through state medical boards.' },
  { id: 'CMP-10', category: 'Provider', item: 'Provider malpractice insurance current ($1M+)', status: 'complete', lastChecked: '2026-02-15', notes: 'All providers maintain minimum $1M per occurrence, $3M aggregate.' },
  { id: 'CMP-11', category: 'Provider', item: 'VA evaluation standards training completed', status: 'in-progress', lastChecked: '2026-02-01', notes: 'Annual VASRD training. 3 of 5 providers current. 2 scheduled for March.' },
  { id: 'CMP-12', category: 'Platform', item: 'Doxy.me HIPAA compliance verified', status: 'complete', lastChecked: '2026-03-01', notes: 'BAA signed. Platform provides end-to-end encryption, no recording by default.' },
  { id: 'CMP-13', category: 'Platform', item: 'Zoom Healthcare HIPAA compliance verified', status: 'complete', lastChecked: '2026-03-01', notes: 'Healthcare-specific Zoom plan with BAA. Used as backup platform.' },
  { id: 'CMP-14', category: 'Data', item: 'Data retention policy enforced (7-year minimum)', status: 'complete', lastChecked: '2026-02-15', notes: 'Automated retention with 7-year minimum. Some states require longer; system configured per state.' },
  { id: 'CMP-15', category: 'Data', item: 'Annual HIPAA risk assessment', status: 'not-started', lastChecked: '2025-06-15', notes: 'Next annual assessment due June 2026. External auditor engaged.' },
];

const PLATFORM_COMPLIANCE = [
  { name: 'Doxy.me', compliant: true, baa: true, encryption: 'AES-256 E2E', notes: 'Primary platform. No download required.' },
  { name: 'Zoom for Healthcare', compliant: true, baa: true, encryption: 'AES-256 GCM', notes: 'Backup platform. Healthcare-specific plan required.' },
  { name: 'VSee', compliant: true, baa: true, encryption: 'AES-256 E2E', notes: 'Alternative option. Designed for telemedicine.' },
  { name: 'Standard Zoom', compliant: false, baa: false, encryption: 'AES-256 GCM', notes: 'NOT acceptable. No BAA available on standard plans.' },
  { name: 'Skype / FaceTime', compliant: false, baa: false, encryption: 'Varies', notes: 'NOT acceptable. No BAA, not HIPAA-compliant.' },
  { name: 'WhatsApp Video', compliant: false, baa: false, encryption: 'E2E', notes: 'NOT acceptable. No BAA despite encryption.' },
];

const RECENT_ACTIVITY = [
  { time: '2 hours ago', text: 'Claim CLM-2404 filed for David Chen — Sleep Apnea', type: 'claim' },
  { time: '3 hours ago', text: 'Consultation completed: James Rodriguez — PTSD Follow-up', type: 'consultation' },
  { time: '5 hours ago', text: 'Dr. Patel completed dermatological evaluation for Robert Jackson', type: 'consultation' },
  { time: '1 day ago', text: 'Claim CLM-2408 filed for Patricia Davis — Bilateral Knee', type: 'claim' },
  { time: '2 days ago', text: 'Provider credential renewal: Dr. Kim — CA license verified', type: 'compliance' },
  { time: '3 days ago', text: 'Claim CLM-2405 appeal submitted for Robert Jackson — Depression', type: 'claim' },
];

// ============ STYLE HELPERS ============

const statusColor = (status: ClaimStatus) => {
  switch (status) {
    case 'filed': return { bg: '#dbeafe', text: '#1e40af', border: '#93c5fd' };
    case 'pending': return { bg: '#fef3c7', text: '#92400e', border: '#fcd34d' };
    case 'approved': return { bg: '#d1fae5', text: '#065f46', border: '#6ee7b7' };
    case 'denied': return { bg: '#fee2e2', text: '#991b1b', border: '#fca5a5' };
    case 'appeal': return { bg: '#ede9fe', text: '#5b21b6', border: '#c4b5fd' };
  }
};

const consultationStatusColor = (status: ConsultationStatus) => {
  switch (status) {
    case 'scheduled': return { bg: '#dbeafe', text: '#1e40af' };
    case 'in-progress': return { bg: '#fef3c7', text: '#92400e' };
    case 'completed': return { bg: '#d1fae5', text: '#065f46' };
    case 'cancelled': return { bg: '#f3f4f6', text: '#6b7280' };
    case 'no-show': return { bg: '#fee2e2', text: '#991b1b' };
  }
};

const suitabilityBadge = (suit: string) => {
  switch (suit) {
    case 'telehealth': return { bg: '#d1fae5', text: '#065f46', label: 'Telehealth Friendly' };
    case 'hybrid': return { bg: '#fef3c7', text: '#92400e', label: 'Hybrid (Telehealth + In-Person)' };
    case 'in-person': return { bg: '#fee2e2', text: '#991b1b', label: 'In-Person Required' };
    default: return { bg: '#f3f4f6', text: '#6b7280', label: suit };
  }
};

// ============ COMPONENT ============

export default function VetForgePage() {
  const [activeSection, setActiveSection] = useState<Section>('dashboard');
  const [claimFilter, setClaimFilter] = useState<ClaimStatus | 'all'>('all');
  const [expandedClaim, setExpandedClaim] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);

  const filteredClaims = MOCK_CLAIMS.filter(c => {
    const matchesFilter = claimFilter === 'all' || c.status === claimFilter;
    const matchesSearch = searchQuery === '' ||
      c.veteranName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.condition.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  // ============ SECTION RENDERERS ============

  const renderDashboard = () => {
    const activeClaims = MOCK_CLAIMS.filter(c => c.status !== 'approved' && c.status !== 'denied').length;
    const consultationsToday = MOCK_CONSULTATIONS.filter(c => c.date === '2026-03-09').length;
    const approvedThisMonth = MOCK_CLAIMS.filter(c => c.status === 'approved' && c.lastUpdate.startsWith('2026-02')).length;

    return (
      <div className="space-y-6">
        {/* KPIs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'Active Claims', value: activeClaims, icon: FileText, color: NAVY, delta: '+2 this week' },
            { label: 'Consultations Today', value: consultationsToday, icon: Video, color: '#7c3aed', delta: '3 scheduled' },
            { label: 'Approved This Month', value: approvedThisMonth, icon: CheckCircle, color: '#059669', delta: '80% approval rate' },
            { label: 'Monthly Revenue', value: '$12,450', icon: DollarSign, color: GOLD, delta: '+18% vs last month' },
          ].map((kpi, i) => (
            <div key={i} className="empire-card" style={{ background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, padding: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <p style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>{kpi.label}</p>
                  <p style={{ fontSize: 28, fontWeight: 700, color: '#111827' }}>{kpi.value}</p>
                  <p style={{ fontSize: 12, color: '#059669', marginTop: 4 }}>{kpi.delta}</p>
                </div>
                <div style={{ background: `${kpi.color}15`, borderRadius: 10, padding: 10 }}>
                  <kpi.icon size={22} color={kpi.color} />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Quick Actions */}
        <div className="empire-card" style={{ background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, padding: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: '#111827', marginBottom: 16 }}>Quick Actions</h3>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {[
              { label: 'New Consultation', icon: Video, color: NAVY },
              { label: 'File Claim', icon: FileText, color: GOLD },
              { label: 'Schedule Evaluation', icon: Calendar, color: '#7c3aed' },
            ].map((action, i) => (
              <button key={i} style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '10px 20px',
                background: `${action.color}10`, border: `1px solid ${action.color}40`,
                borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 500, color: action.color,
                transition: 'all 0.15s',
              }}
                onMouseOver={e => { (e.target as HTMLElement).style.background = `${action.color}20`; }}
                onMouseOut={e => { (e.target as HTMLElement).style.background = `${action.color}10`; }}
              >
                <Plus size={16} />
                {action.label}
              </button>
            ))}
          </div>
        </div>

        {/* Two column: Recent Activity + Upcoming Consultations */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Recent Activity */}
          <div className="empire-card" style={{ background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, padding: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: '#111827', marginBottom: 16 }}>Recent Activity</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {RECENT_ACTIVITY.map((item, i) => (
                <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', paddingBottom: 12, borderBottom: i < RECENT_ACTIVITY.length - 1 ? `1px solid ${GOLD_BORDER}` : 'none' }}>
                  <div style={{
                    background: item.type === 'claim' ? '#dbeafe' : item.type === 'consultation' ? '#ede9fe' : '#d1fae5',
                    borderRadius: 8, padding: 6, flexShrink: 0, marginTop: 2,
                  }}>
                    {item.type === 'claim' ? <FileText size={14} color="#1e40af" /> :
                     item.type === 'consultation' ? <Video size={14} color="#5b21b6" /> :
                     <Shield size={14} color="#065f46" />}
                  </div>
                  <div>
                    <p style={{ fontSize: 13, color: '#374151', lineHeight: 1.4 }}>{item.text}</p>
                    <p style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{item.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Upcoming Consultations */}
          <div className="empire-card" style={{ background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, padding: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: '#111827', marginBottom: 16 }}>Upcoming Consultations</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {MOCK_CONSULTATIONS.filter(c => c.status === 'scheduled').map(c => (
                <div key={c.id} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: 12, background: GOLD_BG, borderRadius: 8, border: `1px solid ${GOLD_BORDER}`,
                }}>
                  <div>
                    <p style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{c.veteranName}</p>
                    <p style={{ fontSize: 12, color: '#6b7280' }}>{c.condition} — {c.provider}</p>
                    <p style={{ fontSize: 12, color: NAVY, fontWeight: 500, marginTop: 2 }}>{c.date} at {c.time}</p>
                  </div>
                  <button style={{
                    padding: '6px 14px', background: NAVY, color: '#fff', border: 'none',
                    borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 4,
                  }}>
                    <Video size={14} /> Join
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Veterans Crisis Line Banner */}
        <div style={{
          background: `linear-gradient(135deg, ${NAVY} 0%, ${NAVY_LIGHT} 100%)`,
          borderRadius: 12, padding: 16, display: 'flex', alignItems: 'center', gap: 16,
          color: '#fff',
        }}>
          <Phone size={24} style={{ flexShrink: 0 }} />
          <div>
            <p style={{ fontSize: 14, fontWeight: 600 }}>Veterans Crisis Line: Dial 988, Press 1</p>
            <p style={{ fontSize: 12, opacity: 0.85 }}>If you or a veteran you know is in crisis, help is available 24/7. Text 838255 or chat at VeteransCrisisLine.net</p>
          </div>
        </div>
      </div>
    );
  };

  const renderClaims = () => (
    <div className="space-y-4">
      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
          <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#9ca3af' }} />
          <input
            type="text"
            placeholder="Search by veteran name, condition, or claim #..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{
              width: '100%', padding: '10px 12px 10px 36px', border: `1px solid ${GOLD_BORDER}`,
              borderRadius: 8, fontSize: 14, background: '#fff', outline: 'none',
            }}
          />
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {(['all', 'filed', 'pending', 'approved', 'denied', 'appeal'] as const).map(f => (
            <button key={f} onClick={() => setClaimFilter(f)} style={{
              padding: '8px 14px', borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: 'pointer',
              border: claimFilter === f ? `2px solid ${NAVY}` : `1px solid ${GOLD_BORDER}`,
              background: claimFilter === f ? `${NAVY}10` : '#fff',
              color: claimFilter === f ? NAVY : '#6b7280',
              textTransform: 'capitalize',
            }}>
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Claims Table */}
      <div className="empire-card" style={{ background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: NAVY_BG }}>
              {['Claim #', 'Veteran', 'Condition', 'Rating %', 'Status', 'Filed Date', ''].map((h, i) => (
                <th key={i} style={{ padding: '12px 16px', textAlign: 'left', fontSize: 12, fontWeight: 600, color: NAVY, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredClaims.map(claim => {
              const sc = statusColor(claim.status);
              const isExpanded = expandedClaim === claim.id;
              return (
                <React.Fragment key={claim.id}>
                  <tr
                    style={{ borderBottom: `1px solid ${GOLD_BORDER}`, cursor: 'pointer', transition: 'background 0.1s' }}
                    onClick={() => setExpandedClaim(isExpanded ? null : claim.id)}
                    onMouseOver={e => { (e.currentTarget as HTMLElement).style.background = GOLD_BG; }}
                    onMouseOut={e => { (e.currentTarget as HTMLElement).style.background = '#fff'; }}
                  >
                    <td style={{ padding: '12px 16px', fontSize: 13, fontWeight: 600, color: NAVY }}>{claim.id}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <p style={{ fontSize: 13, fontWeight: 500, color: '#111827' }}>{claim.veteranName}</p>
                      <p style={{ fontSize: 11, color: '#9ca3af' }}>{claim.branch}</p>
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: 13, color: '#374151' }}>{claim.condition}</td>
                    <td style={{ padding: '12px 16px', fontSize: 13, fontWeight: 600, color: claim.ratingPercent ? '#111827' : '#9ca3af' }}>
                      {claim.ratingPercent !== null ? `${claim.ratingPercent}%` : 'Pending'}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{
                        display: 'inline-block', padding: '4px 10px', borderRadius: 20,
                        fontSize: 11, fontWeight: 600, textTransform: 'capitalize',
                        background: sc.bg, color: sc.text, border: `1px solid ${sc.border}`,
                      }}>
                        {claim.status}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: 13, color: '#6b7280' }}>{claim.filedDate}</td>
                    <td style={{ padding: '12px 16px' }}>
                      {isExpanded ? <ChevronDown size={16} color="#9ca3af" /> : <ChevronRight size={16} color="#9ca3af" />}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr>
                      <td colSpan={7} style={{ padding: '0 16px 16px 16px', background: GOLD_BG }}>
                        <div style={{ padding: 16, background: '#fff', borderRadius: 8, border: `1px solid ${GOLD_BORDER}`, marginTop: 8 }}>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 12 }}>
                            <div>
                              <p style={{ fontSize: 11, color: '#9ca3af', marginBottom: 2 }}>Veteran ID</p>
                              <p style={{ fontSize: 13, color: '#111827' }}>{claim.veteranId}</p>
                            </div>
                            <div>
                              <p style={{ fontSize: 11, color: '#9ca3af', marginBottom: 2 }}>Last Update</p>
                              <p style={{ fontSize: 13, color: '#111827' }}>{claim.lastUpdate}</p>
                            </div>
                          </div>
                          <div>
                            <p style={{ fontSize: 11, color: '#9ca3af', marginBottom: 4 }}>Notes</p>
                            <p style={{ fontSize: 13, color: '#374151', lineHeight: 1.5 }}>{claim.notes}</p>
                          </div>
                          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                            <button style={{ padding: '6px 14px', background: NAVY, color: '#fff', border: 'none', borderRadius: 6, fontSize: 12, cursor: 'pointer' }}>
                              View Full Claim
                            </button>
                            <button style={{ padding: '6px 14px', background: '#fff', color: NAVY, border: `1px solid ${NAVY}`, borderRadius: 6, fontSize: 12, cursor: 'pointer' }}>
                              Schedule Consultation
                            </button>
                            {claim.status === 'denied' && (
                              <button style={{ padding: '6px 14px', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 6, fontSize: 12, cursor: 'pointer' }}>
                                File Appeal
                              </button>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
        {filteredClaims.length === 0 && (
          <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
            <FileText size={32} style={{ margin: '0 auto 8px' }} />
            <p>No claims match your current filters.</p>
          </div>
        )}
      </div>
    </div>
  );

  const renderConsultations = () => (
    <div className="space-y-4">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: '#111827' }}>Telehealth Consultations</h3>
        <button style={{
          display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
          background: NAVY, color: '#fff', border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: 'pointer',
        }}>
          <Plus size={16} /> Schedule Consultation
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {MOCK_CONSULTATIONS.map(c => {
          const cs = consultationStatusColor(c.status);
          const isToday = c.date === '2026-03-09';
          return (
            <div key={c.id} className="empire-card" style={{
              background: '#fff', border: `1px solid ${isToday && c.status === 'scheduled' ? NAVY : GOLD_BORDER}`,
              borderRadius: 12, padding: 20, borderLeft: isToday && c.status === 'scheduled' ? `4px solid ${NAVY}` : undefined,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <h4 style={{ fontSize: 15, fontWeight: 600, color: '#111827' }}>{c.veteranName}</h4>
                    <span style={{
                      padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
                      background: cs.bg, color: cs.text, textTransform: 'capitalize',
                    }}>
                      {c.status}
                    </span>
                    {isToday && c.status === 'scheduled' && (
                      <span style={{ padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 600, background: '#fef3c7', color: '#92400e' }}>
                        Today
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 8, fontSize: 13, color: '#6b7280' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Heart size={14} color={NAVY} /> {c.condition}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <User size={14} color={NAVY} /> {c.provider}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Calendar size={14} color={NAVY} /> {c.date} at {c.time}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Clock size={14} color={NAVY} /> {c.duration}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Globe size={14} color={NAVY} /> {c.platform}
                    </div>
                  </div>
                  {c.notes && (
                    <p style={{ fontSize: 12, color: '#9ca3af', marginTop: 8, fontStyle: 'italic' }}>{c.notes}</p>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  {c.status === 'scheduled' && (
                    <button style={{
                      display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
                      background: NAVY, color: '#fff', border: 'none', borderRadius: 8,
                      fontSize: 13, fontWeight: 500, cursor: 'pointer',
                    }}>
                      <Video size={16} /> Start Video Call
                    </button>
                  )}
                  {c.status === 'completed' && (
                    <button style={{
                      display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
                      background: '#fff', color: NAVY, border: `1px solid ${NAVY}`, borderRadius: 8,
                      fontSize: 13, fontWeight: 500, cursor: 'pointer',
                    }}>
                      <FileText size={16} /> View Report
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderConditions = () => (
    <div className="space-y-6">
      <div>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: '#111827', marginBottom: 4 }}>Conditions Reference Guide</h3>
        <p style={{ fontSize: 13, color: '#6b7280' }}>
          Conditions suitable for telehealth evaluation per VA standards. Suitability ratings based on VA Schedule for Rating Disabilities (VASRD).
        </p>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        {[
          { label: 'Telehealth Friendly', bg: '#d1fae5', color: '#065f46' },
          { label: 'Hybrid (Telehealth + In-Person)', bg: '#fef3c7', color: '#92400e' },
          { label: 'In-Person Required', bg: '#fee2e2', color: '#991b1b' },
        ].map((l, i) => (
          <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
            <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 3, background: l.bg, border: `1px solid ${l.color}30` }} />
            <span style={{ color: l.color, fontWeight: 500 }}>{l.label}</span>
          </span>
        ))}
      </div>

      {CONDITIONS_DATA.map((cat, ci) => (
        <div key={ci} className="empire-card" style={{ background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, overflow: 'hidden' }}>
          <div style={{
            padding: '14px 20px', background: `${cat.color}08`, borderBottom: `1px solid ${GOLD_BORDER}`,
            display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <cat.icon size={18} color={cat.color} />
            <h4 style={{ fontSize: 15, fontWeight: 600, color: cat.color }}>{cat.category}</h4>
          </div>
          <div>
            {cat.conditions.map((cond, i) => {
              const sb = suitabilityBadge(cond.suitability);
              return (
                <div key={i} style={{
                  padding: '14px 20px', borderBottom: i < cat.conditions.length - 1 ? `1px solid ${GOLD_BORDER}` : 'none',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap',
                }}>
                  <div style={{ flex: 1, minWidth: 250 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                      <p style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{cond.name}</p>
                      <span style={{
                        padding: '2px 8px', borderRadius: 20, fontSize: 10, fontWeight: 600,
                        background: sb.bg, color: sb.text,
                      }}>
                        {sb.label}
                      </span>
                    </div>
                    <p style={{ fontSize: 12, color: '#6b7280', lineHeight: 1.5 }}>{cond.description}</p>
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <p style={{ fontSize: 11, color: '#9ca3af', marginBottom: 2 }}>Common VA Ratings</p>
                    <p style={{ fontSize: 12, fontWeight: 500, color: NAVY }}>{cond.commonRatings}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );

  const renderProviders = () => (
    <div className="space-y-4">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: '#111827' }}>Provider Directory</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#6b7280' }}>
          <Users size={14} /> {MOCK_PROVIDERS.length} providers in network
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16 }}>
        {MOCK_PROVIDERS.map(p => {
          const isExpanded = expandedProvider === p.id;
          return (
            <div key={p.id} className="empire-card" style={{
              background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, overflow: 'hidden',
              transition: 'box-shadow 0.15s',
            }}>
              <div style={{ padding: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                  <div>
                    <h4 style={{ fontSize: 15, fontWeight: 600, color: '#111827' }}>{p.name}</h4>
                    <p style={{ fontSize: 12, color: '#6b7280' }}>{p.credential} — {p.specialty}</p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Star size={14} fill={GOLD} color={GOLD} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#111827' }}>{p.rating}</span>
                    <span style={{ fontSize: 11, color: '#9ca3af' }}>({p.reviewCount})</span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
                  <span style={{
                    padding: '3px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                    background: p.imlc ? '#d1fae5' : '#fef3c7',
                    color: p.imlc ? '#065f46' : '#92400e',
                  }}>
                    {p.imlc ? 'IMLC Member' : 'State Licensed'}
                  </span>
                  <span style={{ padding: '3px 8px', borderRadius: 4, fontSize: 11, fontWeight: 500, background: NAVY_BG, color: NAVY }}>
                    {p.credential}
                  </span>
                </div>

                <div style={{ marginBottom: 12 }}>
                  <p style={{ fontSize: 11, color: '#9ca3af', marginBottom: 4 }}>Licensed States</p>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {p.licenseStates.map(s => (
                      <span key={s} style={{
                        padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 500,
                        background: GOLD_BG, border: `1px solid ${GOLD_BORDER}`, color: '#374151',
                      }}>
                        {s}
                      </span>
                    ))}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#6b7280', marginBottom: 12 }}>
                  <Clock size={14} /> {p.availability}
                </div>

                <button
                  onClick={() => setExpandedProvider(isExpanded ? null : p.id)}
                  style={{
                    width: '100%', padding: '8px 0', background: 'none', border: 'none',
                    fontSize: 12, color: NAVY, fontWeight: 500, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                  }}
                >
                  {isExpanded ? 'Show Less' : 'View Full Profile'}
                  {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </button>

                {isExpanded && (
                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${GOLD_BORDER}` }}>
                    <p style={{ fontSize: 13, color: '#374151', lineHeight: 1.5, marginBottom: 12 }}>{p.bio}</p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#6b7280' }}>
                        <Phone size={14} /> {p.phone}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#6b7280' }}>
                        <Mail size={14} /> {p.email}
                      </div>
                    </div>
                    <button style={{
                      marginTop: 12, width: '100%', padding: '10px 0', background: NAVY, color: '#fff',
                      border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: 'pointer',
                    }}>
                      Schedule with {p.name.split(' ')[0]}. {p.name.split(' ').slice(1).join(' ')}
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderCompliance = () => {
    const completedCount = COMPLIANCE_ITEMS.filter(c => c.status === 'complete').length;
    const totalCount = COMPLIANCE_ITEMS.length;
    const compliancePercent = Math.round((completedCount / totalCount) * 100);
    const categories = [...new Set(COMPLIANCE_ITEMS.map(c => c.category))];

    return (
      <div className="space-y-6">
        {/* Overview */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="empire-card" style={{ background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, padding: 20 }}>
            <p style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>Overall Compliance</p>
            <p style={{ fontSize: 28, fontWeight: 700, color: compliancePercent >= 80 ? '#059669' : '#f59e0b' }}>
              {compliancePercent}%
            </p>
            <p style={{ fontSize: 12, color: '#9ca3af' }}>{completedCount} of {totalCount} items complete</p>
            <div style={{ marginTop: 8, height: 6, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{ width: `${compliancePercent}%`, height: '100%', background: compliancePercent >= 80 ? '#059669' : '#f59e0b', borderRadius: 3 }} />
            </div>
          </div>
          <div className="empire-card" style={{ background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, padding: 20 }}>
            <p style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>Last Full Audit</p>
            <p style={{ fontSize: 28, fontWeight: 700, color: '#111827' }}>Jun 2025</p>
            <p style={{ fontSize: 12, color: '#9ca3af' }}>Next audit: June 2026</p>
          </div>
          <div className="empire-card" style={{ background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, padding: 20 }}>
            <p style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>Data Retention</p>
            <p style={{ fontSize: 28, fontWeight: 700, color: '#111827' }}>7 yr</p>
            <p style={{ fontSize: 12, color: '#9ca3af' }}>Minimum retention period (medical records)</p>
          </div>
        </div>

        {/* Compliance Checklist by Category */}
        {categories.map(cat => (
          <div key={cat} className="empire-card" style={{ background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, overflow: 'hidden' }}>
            <div style={{ padding: '14px 20px', background: NAVY_BG, borderBottom: `1px solid ${GOLD_BORDER}`, display: 'flex', alignItems: 'center', gap: 10 }}>
              <Shield size={16} color={NAVY} />
              <h4 style={{ fontSize: 14, fontWeight: 600, color: NAVY }}>{cat}</h4>
              <span style={{ fontSize: 11, color: '#6b7280', marginLeft: 'auto' }}>
                {COMPLIANCE_ITEMS.filter(c => c.category === cat && c.status === 'complete').length}/{COMPLIANCE_ITEMS.filter(c => c.category === cat).length} complete
              </span>
            </div>
            {COMPLIANCE_ITEMS.filter(c => c.category === cat).map((item, i, arr) => (
              <div key={item.id} style={{
                padding: '12px 20px', borderBottom: i < arr.length - 1 ? `1px solid ${GOLD_BORDER}` : 'none',
                display: 'flex', alignItems: 'flex-start', gap: 12,
              }}>
                <div style={{ marginTop: 2, flexShrink: 0 }}>
                  {item.status === 'complete' ? (
                    <CheckCircle size={18} color="#059669" />
                  ) : item.status === 'in-progress' ? (
                    <Clock size={18} color="#f59e0b" />
                  ) : (
                    <AlertTriangle size={18} color="#dc2626" />
                  )}
                </div>
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: 13, fontWeight: 500, color: '#111827' }}>{item.item}</p>
                  <p style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{item.notes}</p>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <span style={{
                    padding: '2px 8px', borderRadius: 20, fontSize: 10, fontWeight: 600,
                    background: item.status === 'complete' ? '#d1fae5' : item.status === 'in-progress' ? '#fef3c7' : '#fee2e2',
                    color: item.status === 'complete' ? '#065f46' : item.status === 'in-progress' ? '#92400e' : '#991b1b',
                    textTransform: 'capitalize',
                  }}>
                    {item.status === 'not-started' ? 'Not Started' : item.status === 'in-progress' ? 'In Progress' : 'Complete'}
                  </span>
                  <p style={{ fontSize: 10, color: '#9ca3af', marginTop: 4 }}>Checked: {item.lastChecked}</p>
                </div>
              </div>
            ))}
          </div>
        ))}

        {/* Platform Compliance */}
        <div className="empire-card" style={{ background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', background: NAVY_BG, borderBottom: `1px solid ${GOLD_BORDER}`, display: 'flex', alignItems: 'center', gap: 10 }}>
            <Video size={16} color={NAVY} />
            <h4 style={{ fontSize: 14, fontWeight: 600, color: NAVY }}>Video Platform Compliance</h4>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: GOLD_BG }}>
                {['Platform', 'HIPAA Compliant', 'BAA Available', 'Encryption', 'Notes'].map((h, i) => (
                  <th key={i} style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {PLATFORM_COMPLIANCE.map((p, i) => (
                <tr key={i} style={{ borderBottom: `1px solid ${GOLD_BORDER}` }}>
                  <td style={{ padding: '10px 16px', fontSize: 13, fontWeight: 500, color: '#111827' }}>{p.name}</td>
                  <td style={{ padding: '10px 16px' }}>
                    {p.compliant ? <Check size={16} color="#059669" /> : <X size={16} color="#dc2626" />}
                  </td>
                  <td style={{ padding: '10px 16px' }}>
                    {p.baa ? <Check size={16} color="#059669" /> : <X size={16} color="#dc2626" />}
                  </td>
                  <td style={{ padding: '10px 16px', fontSize: 12, color: '#6b7280' }}>{p.encryption}</td>
                  <td style={{ padding: '10px 16px', fontSize: 12, color: p.compliant ? '#059669' : '#dc2626', fontWeight: 500 }}>{p.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderResources = () => (
    <div className="space-y-6">
      {/* VA Links */}
      <div className="empire-card" style={{ background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, padding: 20 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: '#111827', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Globe size={18} color={NAVY} /> Official VA Resources
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {[
            { title: 'VA.gov — Benefits', url: 'https://www.va.gov/disability/', desc: 'Official VA disability benefits and application portal' },
            { title: 'VA Health Care', url: 'https://www.va.gov/health-care/', desc: 'Enroll and manage VA health care benefits' },
            { title: 'eBenefits Portal', url: 'https://www.ebenefits.va.gov/', desc: 'Apply for benefits, check claim status, and more' },
            { title: 'VA Forms Library', url: 'https://www.va.gov/find-forms/', desc: 'Access all VA forms including claim forms' },
            { title: 'Board of Veterans Appeals', url: 'https://www.bva.va.gov/', desc: 'Appeal decisions on your VA claims' },
            { title: 'Veterans Crisis Line', url: 'https://www.veteranscrisisline.net/', desc: 'Dial 988 then press 1. Text 838255. Chat online 24/7.' },
          ].map((link, i) => (
            <a key={i} href={link.url} target="_blank" rel="noopener noreferrer" style={{
              display: 'block', padding: 14, background: GOLD_BG, border: `1px solid ${GOLD_BORDER}`,
              borderRadius: 8, textDecoration: 'none', transition: 'all 0.15s',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <p style={{ fontSize: 14, fontWeight: 600, color: NAVY }}>{link.title}</p>
                <ExternalLink size={14} color="#9ca3af" />
              </div>
              <p style={{ fontSize: 12, color: '#6b7280', marginTop: 4, lineHeight: 1.4 }}>{link.desc}</p>
            </a>
          ))}
        </div>
      </div>

      {/* P&T Disability Info */}
      <div className="empire-card" style={{ background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, padding: 20 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: '#111827', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Award size={18} color={GOLD} /> Permanent & Total (P&T) Disability
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <h4 style={{ fontSize: 14, fontWeight: 600, color: NAVY, marginBottom: 6 }}>What is P&T?</h4>
            <p style={{ fontSize: 13, color: '#374151', lineHeight: 1.6 }}>
              Permanent and Total (P&T) disability means the VA has determined that your service-connected disability is total (100% rating)
              and permanent (not expected to improve). This designation provides the highest level of benefits and protections, including
              no future re-examinations.
            </p>
          </div>
          <div>
            <h4 style={{ fontSize: 14, fontWeight: 600, color: NAVY, marginBottom: 6 }}>P&T Benefits Include:</h4>
            <ul style={{ fontSize: 13, color: '#374151', lineHeight: 1.8, listStyle: 'none', padding: 0 }}>
              {[
                'Tax-free monthly compensation (2026 rate: $3,737.85/month for 100% single veteran)',
                'Chapter 35 Dependents Educational Assistance (DEA) for spouse and children',
                'Commissary, exchange, and MWR privileges',
                'CHAMPVA health coverage for dependents',
                'Property tax exemptions (varies by state)',
                'No future scheduled re-examinations',
                'Eligibility for Individual Unemployability (TDIU) if not at schedular 100%',
                'State-specific benefits: free license plates, hunting/fishing licenses, property tax waivers',
              ].map((item, i) => (
                <li key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                  <CheckCircle size={14} color="#059669" style={{ flexShrink: 0, marginTop: 4 }} />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Benefits Calculator */}
      <div className="empire-card" style={{ background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, padding: 20 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: '#111827', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Scale size={18} color={NAVY} /> VA Disability Compensation Rates (2026)
        </h3>
        <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 16 }}>
          Monthly compensation rates for a single veteran with no dependents. Rates increase with dependents.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 8 }}>
          {[
            { rating: '10%', amount: '$171.23' },
            { rating: '20%', amount: '$338.49' },
            { rating: '30%', amount: '$524.31' },
            { rating: '40%', amount: '$755.28' },
            { rating: '50%', amount: '$1,075.16' },
            { rating: '60%', amount: '$1,361.88' },
            { rating: '70%', amount: '$1,716.28' },
            { rating: '80%', amount: '$1,995.01' },
            { rating: '90%', amount: '$2,241.91' },
            { rating: '100%', amount: '$3,737.85' },
          ].map((r, i) => (
            <div key={i} style={{
              padding: 12, textAlign: 'center', borderRadius: 8,
              background: r.rating === '100%' ? `${GOLD}15` : GOLD_BG,
              border: `1px solid ${r.rating === '100%' ? GOLD : GOLD_BORDER}`,
            }}>
              <p style={{ fontSize: 16, fontWeight: 700, color: r.rating === '100%' ? GOLD : NAVY }}>{r.rating}</p>
              <p style={{ fontSize: 12, fontWeight: 500, color: '#374151', marginTop: 4 }}>{r.amount}</p>
            </div>
          ))}
        </div>
      </div>

      {/* FAQ */}
      <div className="empire-card" style={{ background: '#fff', border: `1px solid ${GOLD_BORDER}`, borderRadius: 12, padding: 20 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: '#111827', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <BookOpen size={18} color={NAVY} /> Frequently Asked Questions
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[
            {
              q: 'Can a telehealth evaluation be used for VA disability claims?',
              a: 'Yes. Telehealth evaluations are legal and accepted by the VA for disability claim support. The evaluation must meet the same standards of care as an in-person examination. The provider must be licensed in the state where you are located during the evaluation.',
            },
            {
              q: 'How does the claims process work?',
              a: 'You file a claim with the VA (VA Form 21-526EZ). The VA reviews your service records and may schedule a Compensation & Pension (C&P) exam. Our telehealth evaluations provide independent medical evidence and nexus letters to support your claim. The VA then makes a rating decision.',
            },
            {
              q: 'What is a nexus letter?',
              a: 'A nexus letter is a document from a qualified medical provider that establishes a connection ("nexus") between your current condition and your military service. It is one of the most important pieces of evidence in a VA disability claim.',
            },
            {
              q: 'How long does the VA claims process take?',
              a: 'The VA target is 125 days for initial claims. In practice, times vary from 3-6 months for straightforward claims to over a year for complex or appealed claims. Having thorough medical evidence upfront can help expedite the process.',
            },
            {
              q: 'Can I file multiple claims at once?',
              a: 'Yes. You can file claims for multiple conditions simultaneously. The VA uses "VA math" to calculate a combined rating. For example, a 50% rating plus a 30% rating does not equal 80% — the combined rating would be 65% (rounded to 70%).',
            },
            {
              q: 'What if my claim is denied?',
              a: 'You have several appeal options: Supplemental Claim (new evidence), Higher-Level Review (different reviewer), or Board Appeal. You have one year from the decision date to file an appeal. We can help gather additional medical evidence to support your appeal.',
            },
          ].map((faq, i) => (
            <div key={i} style={{ paddingBottom: 16, borderBottom: i < 5 ? `1px solid ${GOLD_BORDER}` : 'none' }}>
              <p style={{ fontSize: 14, fontWeight: 600, color: NAVY, marginBottom: 6 }}>{faq.q}</p>
              <p style={{ fontSize: 13, color: '#374151', lineHeight: 1.6 }}>{faq.a}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Emergency Info */}
      <div style={{
        background: `linear-gradient(135deg, ${NAVY} 0%, ${NAVY_LIGHT} 100%)`,
        borderRadius: 12, padding: 20, color: '#fff',
      }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Emergency & Crisis Resources</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 16 }}>
          {[
            { label: 'Veterans Crisis Line', detail: 'Dial 988, then press 1', icon: Phone },
            { label: 'Crisis Text Line', detail: 'Text 838255', icon: Mail },
            { label: 'VA Benefits Hotline', detail: '1-800-827-1000', icon: Phone },
            { label: 'Online Crisis Chat', detail: 'VeteransCrisisLine.net/Chat', icon: Globe },
          ].map((r, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ background: 'rgba(255,255,255,0.15)', borderRadius: 8, padding: 8 }}>
                <r.icon size={18} />
              </div>
              <div>
                <p style={{ fontSize: 13, fontWeight: 600 }}>{r.label}</p>
                <p style={{ fontSize: 12, opacity: 0.85 }}>{r.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderSection = () => {
    switch (activeSection) {
      case 'dashboard': return renderDashboard();
      case 'claims': return renderClaims();
      case 'consultations': return renderConsultations();
      case 'conditions': return renderConditions();
      case 'providers': return renderProviders();
      case 'compliance': return renderCompliance();
      case 'resources': return renderResources();
      case 'payments': return <PaymentModule product="vetforge" />;
      case 'docs': return <div style={{ padding: 24 }}><ProductDocs product="vetforge" /></div>;
      default: return renderDashboard();
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: GOLD_BG }}>
      {/* Header */}
      <div style={{
        background: `linear-gradient(135deg, ${NAVY} 0%, ${NAVY_LIGHT} 100%)`,
        padding: '20px 24px', color: '#fff',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ background: 'rgba(255,255,255,0.15)', borderRadius: 10, padding: 8 }}>
            <Shield size={24} color={GOLD} />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em' }}>VeteranForge</h1>
            <p style={{ fontSize: 13, opacity: 0.85, marginTop: 2 }}>VA Disability Claims & Telehealth Evaluation Platform</p>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div style={{
        background: '#fff', borderBottom: `1px solid ${GOLD_BORDER}`, padding: '0 24px',
        overflowX: 'auto', whiteSpace: 'nowrap' as const,
      }}>
        <div style={{ display: 'flex', gap: 0 }}>
          {NAV_SECTIONS.map(s => {
            const isActive = activeSection === s.id;
            return (
              <button
                key={s.id}
                onClick={() => setActiveSection(s.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6, padding: '14px 18px',
                  background: 'none', border: 'none', cursor: 'pointer',
                  fontSize: 13, fontWeight: isActive ? 600 : 400,
                  color: isActive ? NAVY : '#6b7280',
                  borderBottom: isActive ? `2px solid ${GOLD}` : '2px solid transparent',
                  transition: 'all 0.15s',
                }}
              >
                <s.icon size={16} />
                {s.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
        {renderSection()}
      </div>
    </div>
  );
}
