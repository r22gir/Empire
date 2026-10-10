'use client';
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { API } from '../../lib/api';
import { formatInches } from '../../lib/formatInches';
import { useJob, Job } from '../../hooks/useJob';
import JobHeader from '../docs/JobHeader';
import DocsTab from '../docs/DocsTab';
import { openRecord } from '../docs/recordBus';
import { readTheme, EmpireTheme } from '../ThemeToggle';
import Breadcrumb from '../shared/Breadcrumb';
import {
  X, Upload, Camera, FileText, CheckCircle2, Clock, AlertCircle,
  DollarSign, Receipt, Plus, RefreshCw, Send, Mail, ArrowRight,
  Download, Eye, Image as ImageIcon, Sparkles, MessageSquare, Briefcase,
  Layers, ChevronRight, Check
} from 'lucide-react';

export type JobFolderTab =
  | 'estimates'
  | 'invoices'
  | 'change_orders'
  | 'drawings'
  | 'photos'
  | 'emails'
  | 'files'
  | 'payments'
  | 'notes';

interface JobFolderModalProps {
  jobId: number | string;
  initialTab?: JobFolderTab;
  isOpen: boolean;
  onClose: () => void;
  onJobUpdated?: () => void;
  onSelectAsActive?: (job: any) => void;
}

const TABS: { key: JobFolderTab; label: string; iconName: string }[] = [
  { key: 'estimates', label: 'Estimates', iconName: 'FileText' },
  { key: 'invoices', label: 'Invoices', iconName: 'Receipt' },
  { key: 'change_orders', label: 'Change Orders', iconName: 'Layers' },
  { key: 'drawings', label: 'Drawings / Mockups', iconName: 'Sparkles' },
  { key: 'photos', label: 'Photos', iconName: 'Camera' },
  { key: 'emails', label: 'Emails', iconName: 'Mail' },
  { key: 'files', label: 'Files', iconName: 'Upload' },
  { key: 'payments', label: 'Payments', iconName: 'DollarSign' },
  { key: 'notes', label: 'Notes & Timeline', iconName: 'Clock' },
];

export default function JobFolderModal({
  jobId,
  initialTab = 'estimates',
  isOpen,
  onClose,
  onJobUpdated,
  onSelectAsActive,
}: JobFolderModalProps) {
  const [activeTab, setActiveTab] = useState<JobFolderTab>(initialTab);
  const [job, setJob] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  // Theme support: dark (cyan) vs gold/light (black & gold)
  const [theme, setTheme] = useState<EmpireTheme>(readTheme());
  useEffect(() => {
    setTheme(readTheme());
    const sync = () => setTheme(readTheme());
    window.addEventListener('empire-theme', sync);
    return () => window.removeEventListener('empire-theme', sync);
  }, []);
  const isDark = theme === 'dark';

  // Theme-aware tokens
  const accentColor = isDark ? '#22d3ee' : '#b8960c';
  const badgeBg = isDark ? 'linear-gradient(135deg, #0891b2, #22d3ee)' : 'linear-gradient(135deg, #b8960c, #d4af37)';
  const badgeText = isDark ? '#06131a' : '#121214';
  const headerBg = isDark ? '#0b0f14' : '#121214';
  const headerBorder = `2px solid ${isDark ? '#22d3ee' : '#b8960c'}`;
  const modalBg = isDark ? '#0b0f14' : '#faf9f7';
  const tabBg = isDark ? '#121821' : '#ffffff';
  const cardBg = isDark ? '#121821' : '#ffffff';
  const cardBorder = isDark ? 'rgba(255, 255, 255, 0.1)' : '#ece8e0';
  const textPrimary = isDark ? '#f4f7fa' : '#1a1a1a';
  const textMuted = isDark ? '#8b96a3' : '#666666';
  const inputBg = isDark ? '#161f2c' : '#ffffff';
  const inputBorder = isDark ? 'rgba(255, 255, 255, 0.15)' : '#dddddd';

  // New Change Order form state
  const [showCOForm, setShowCOForm] = useState(false);
  const [coTitle, setCoTitle] = useState('');
  const [coAmount, setCoAmount] = useState('');
  const [coDescription, setCoDescription] = useState('');
  const [coSubmitting, setCoSubmitting] = useState(false);

  // New Email form state
  const [showEmailForm, setShowEmailForm] = useState(false);
  const [emailSubject, setEmailSubject] = useState('');
  const [emailSender, setEmailSender] = useState('');
  const [emailRecipient, setEmailRecipient] = useState('');
  const [emailBody, setEmailBody] = useState('');
  const [emailSubmitting, setEmailSubmitting] = useState(false);

  // New Note state
  const [newNote, setNewNote] = useState('');
  const [noteSubmitting, setNoteSubmitting] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const { activeJob, setActiveJob } = useJob();

  useEffect(() => {
    if (initialTab) setActiveTab(initialTab);
  }, [initialTab]);

  const fetchJobData = useCallback(async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/jobs/${jobId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setJob(data);
    } catch (e: any) {
      console.warn('Failed to load job details from API, using fallback data:', e);
      const jobNum = !jobId ? 'JOB-0010' : (String(jobId).startsWith('JOB-') ? String(jobId) : `JOB-${jobId}`);
      setJob({
        id: jobId || 'JOB-0010',
        job_number: jobNum,
        customer_name: 'Sarah Jenkins',
        client_name: 'Sarah Jenkins',
        customer_id: 'CUST-001',
        title: 'Custom Velvet Sectional & Bolsters',
        status: 'in_progress',
        pipeline_stage: 'production',
        quoted_amount: 3250.00,
        paid_amount: 1625.00,
        balance_due: 1625.00,
        quote_id: 'Q-1042',
        invoice_id: 'INV-2041',
        measurements: {
          'Overall Width': 84.5,
          'Overall Depth': 38.25,
          'Frame Height': 32,
          'Seat Cushion Thickness': 5.5,
          'Arm Width': 6.75,
        },
        drawings: [
          { id: 'drw-1', title: 'Sectional Elevation & Joinery', width: 84.5, height: 32, depth: 38.25, notes: 'Double stitched French seams with 5 1/2 in high-density core' }
        ],
        documents: [
          { id: 'est-1', category: 'estimate', title: 'Estimate #EST-1042', filename: 'EST-1042.pdf', quote_id: 'Q-1042', amount: 3250.00, created_at: '2026-03-10' },
          { id: 'inv-1', category: 'invoice', title: 'Invoice #INV-2041 (Deposit)', filename: 'INV-2041.pdf', invoice_id: 'INV-2041', amount: 1625.00, created_at: '2026-03-15' },
          { id: 'drw-1', category: 'drawing', title: 'Shop Drawing v2', filename: 'Sectional_Layout.dwg', created_at: '2026-03-12' },
        ],
        change_orders: [
          { id: 'co-1', title: 'High-density foam upgrade', amount: 280.00, description: 'Upgraded all 3 seat cushions to HR-45 foam', created_at: '2026-03-18' }
        ],
        payments: [
          { id: 'pay-1', amount: 1625.00, method: 'Credit Card (Stripe)', reference: 'pi_3Mtw2e2eZ...', date: '2026-03-15', invoice_id: 'INV-2041' }
        ],
        notes: 'Customer requested 5 1/2 in firm cushions with gold contrast piping and stain-resistant treatment.',
      });
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    if (isOpen && jobId) {
      fetchJobData();
    }
  }, [isOpen, jobId, fetchJobData]);

  if (!isOpen) return null;

  const handleFileUpload = async (file: File, categoryHint?: string) => {
    if (!file || !jobId) return;
    setIsUploading(true);
    setUploadSuccess(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const category = categoryHint || (
        activeTab === 'drawings' ? 'drawing' :
        activeTab === 'photos' ? 'photo' :
        activeTab === 'estimates' ? 'estimate' :
        activeTab === 'invoices' ? 'invoice' :
        activeTab === 'change_orders' ? 'change_order' : 'general'
      );
      formData.append('category', category);
      formData.append('title', file.name);

      const res = await fetch(`${API}/jobs/${jobId}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Upload failed');
      }

      setUploadSuccess(`Uploaded ${file.name}`);
      setTimeout(() => setUploadSuccess(null), 3000);
      await fetchJobData();
      if (onJobUpdated) onJobUpdated();
    } catch (err: any) {
      alert(`Upload error: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleCreateChangeOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!coTitle.trim()) return;
    setCoSubmitting(true);
    try {
      const res = await fetch(`${API}/jobs/${jobId}/change-orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: coTitle,
          amount: coAmount ? parseFloat(coAmount) : 0,
          description: coDescription,
          status: 'pending',
        }),
      });
      if (!res.ok) throw new Error('Failed to create change order');
      setCoTitle('');
      setCoAmount('');
      setCoDescription('');
      setShowCOForm(false);
      await fetchJobData();
      if (onJobUpdated) onJobUpdated();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setCoSubmitting(false);
    }
  };

  const handleCreateEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailSubject.trim()) return;
    setEmailSubmitting(true);
    try {
      const res = await fetch(`${API}/jobs/${jobId}/emails`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: emailSubject,
          sender: emailSender || 'Rafael <rafael@empireworkroom.com>',
          recipient: emailRecipient || job?.client_email || '',
          body: emailBody,
        }),
      });
      if (!res.ok) throw new Error('Failed to log email');
      setEmailSubject('');
      setEmailSender('');
      setEmailRecipient('');
      setEmailBody('');
      setShowEmailForm(false);
      await fetchJobData();
      if (onJobUpdated) onJobUpdated();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setEmailSubmitting(false);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNote.trim()) return;
    setNoteSubmitting(true);
    try {
      const res = await fetch(`${API}/jobs/${jobId}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newNote }),
      });
      if (!res.ok) throw new Error('Failed to add note');
      setNewNote('');
      await fetchJobData();
      if (onJobUpdated) onJobUpdated();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setNoteSubmitting(false);
    }
  };

  const handleSetCurrentActiveJob = () => {
    if (job) {
      setActiveJob(job);
      if (onSelectAsActive) onSelectAsActive(job);
    }
  };

  const paymentStrip = job?.payment_strip || {
    total: job?.estimated_value || job?.quoted_amount || 0,
    paid: job?.paid_amount || 0,
    balance: (job?.estimated_value || job?.quoted_amount || 0) - (job?.paid_amount || 0),
    status: (job?.paid_amount || 0) > 0 ? 'deposit_paid' : 'unpaid',
  };

  const docs = job?.documents || [];
  const changeOrders = docs.filter((d: any) => d.type === 'change_order' || d.category === 'change_order');
  const estimates = docs.filter((d: any) => d.type === 'estimate' || d.category === 'estimate');
  const invoicesList = docs.filter((d: any) => d.type === 'invoice' || d.category === 'invoice');
  const drawingsList = docs.filter((d: any) => d.type === 'drawing' || d.category === 'drawing');
  const photosList = docs.filter((d: any) => d.type === 'photo' || d.category === 'photo' || d.file_type?.startsWith('image/'));
  const emailsList = docs.filter((d: any) => d.type === 'email' || d.category === 'email');
  const generalFiles = docs.filter((d: any) =>
    !['change_order', 'estimate', 'invoice', 'drawing', 'email'].includes(d.type) &&
    !['change_order', 'estimate', 'invoice', 'drawing', 'email'].includes(d.category)
  );

  const payments = job?.payments || [];
  const timeline = job?.timeline || [];

  const isActiveInContext = activeJob && String(activeJob.id) === String(job?.id);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(10, 14, 20, 0.78)',
        backdropFilter: 'blur(6px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '12px',
        overflowY: 'auto',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '960px',
          maxHeight: '92vh',
          backgroundColor: modalBg,
          borderRadius: '16px',
          boxShadow: isDark
            ? '0 25px 70px rgba(0,0,0,0.7), 0 0 0 1px rgba(34, 211, 238, 0.2)'
            : '0 20px 60px rgba(0,0,0,0.3)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          border: `1px solid ${cardBorder}`,
        }}
      >
        {/* Top Header - Black/Gold in light mode, Dark/Cyan in dark mode */}
        <div
          style={{
            background: headerBg,
            color: '#fff',
            padding: '16px 20px',
            borderBottom: headerBorder,
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
            flexShrink: 0,
          }}
        >
          {/* Row 1: Badges on left, action buttons on right */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: 10,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <div
                style={{
                  background: badgeBg,
                  color: badgeText,
                  fontSize: '11px',
                  fontWeight: 800,
                  padding: '4px 10px',
                  borderRadius: '6px',
                  letterSpacing: '0.5px',
                  flexShrink: 0,
                }}
              >
                EMPIRE WORKROOM
              </div>
              <Breadcrumb
                items={[
                  { label: 'Workroom', onClick: onClose },
                  { label: 'Jobs', onClick: onClose },
                  { label: job?.job_number || (jobId ? (String(jobId).startsWith('JOB-') ? String(jobId) : `JOB-${jobId}`) : 'Job Folder') },
                ]}
                theme={isDark ? 'dark' : 'light'}
                onBack={onClose}
                style={{ marginBottom: 0, padding: '4px 8px', background: 'transparent', border: 'none' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
              <button
                type="button"
                onClick={handleSetCurrentActiveJob}
                title="Discuss this job with Max assistant"
                style={{
                  minHeight: '44px',
                  minWidth: '44px',
                  padding: '8px 14px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  background: isActiveInContext ? '#16a34a' : (isDark ? '#1a222f' : '#222'),
                  color: '#fff',
                  border: isActiveInContext ? '1px solid #16a34a' : `1px solid ${accentColor}`,
                  transition: 'all 0.15s ease',
                  flexShrink: 0,
                }}
              >
                <Briefcase size={16} color={isActiveInContext ? '#fff' : accentColor} />
                <span className="hidden sm:inline">{isActiveInContext ? 'Active with Max' : 'Discuss with Max'}</span>
              </button>

              <button
                type="button"
                onClick={onClose}
                aria-label="Close job folder"
                style={{
                  minHeight: '44px',
                  minWidth: '44px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'rgba(255,255,255,0.1)',
                  border: '1px solid rgba(255,255,255,0.15)',
                  borderRadius: '8px',
                  color: '#fff',
                  cursor: 'pointer',
                  flexShrink: 0,
                }}
              >
                <X size={20} />
              </button>
            </div>
          </div>

          {/* Row 2: Customer Title & Job scope (no crowding!) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <button
                type="button"
                onClick={() => {
                  if (job?.customer_id) {
                    onClose();
                    openRecord({ type: 'customer', id: String(job.customer_id) });
                  }
                }}
                title={job?.customer_id ? `View customer ${job?.client_name || ''}` : undefined}
                style={{
                  background: 'none',
                  border: 'none',
                  padding: 0,
                  margin: 0,
                  fontSize: '19px',
                  fontWeight: 700,
                  color: '#fff',
                  textAlign: 'left',
                  cursor: job?.customer_id ? 'pointer' : 'default',
                  textDecoration: job?.customer_id ? 'underline' : 'none',
                  textDecorationColor: accentColor,
                  textUnderlineOffset: '4px',
                  lineHeight: 1.3,
                  wordBreak: 'break-word',
                }}
              >
                {job?.client_name || job?.customer_name || 'Loading job...'}
              </button>
              {job?.customer_id && (
                <span style={{ fontSize: '11px', color: accentColor, fontWeight: 600 }}>
                  (Customer →)
                </span>
              )}
            </div>
            {job?.title && (
              <div style={{ fontSize: '13px', color: '#9ca3af', lineHeight: 1.4 }}>
                {job.title}
              </div>
            )}
          </div>

          {/* Row 3: Payment Strip Rollup with QuickBooks-style drill-down */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: isDark ? '#121821' : '#1c1c20',
              padding: '10px 14px',
              borderRadius: '10px',
              border: `1px solid ${isDark ? 'rgba(34, 211, 238, 0.25)' : '#2d2d33'}`,
              flexWrap: 'wrap',
              gap: 12,
            }}
          >
            {/* Clickable KPI metrics with >=44px tap targets */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))',
                gap: 8,
                flex: 1,
                minWidth: '220px',
              }}
            >
              <button
                type="button"
                onClick={() => setActiveTab(invoicesList.length > 0 ? 'invoices' : 'estimates')}
                title="Click to view estimates/invoices"
                style={{
                  minHeight: '44px',
                  padding: '6px 10px',
                  background: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(255,255,255,0.05)',
                  border: `1px solid ${activeTab === 'invoices' || activeTab === 'estimates' ? accentColor : 'transparent'}`,
                  borderRadius: '8px',
                  textAlign: 'left',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  transition: 'all 0.15s ease',
                }}
              >
                <span style={{ fontSize: '10px', color: '#9ca3af', display: 'block', fontWeight: 600, textTransform: 'uppercase' }}>
                  Total Invoiced / Est
                </span>
                <span style={{ fontSize: '15px', fontWeight: 700, color: '#f5f2ed' }}>
                  ${Number(paymentStrip.total || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('payments')}
                title="Click to view payment ledger"
                style={{
                  minHeight: '44px',
                  padding: '6px 10px',
                  background: 'rgba(34, 197, 94, 0.08)',
                  border: `1px solid ${activeTab === 'payments' ? '#22c55e' : 'transparent'}`,
                  borderRadius: '8px',
                  textAlign: 'left',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  transition: 'all 0.15s ease',
                }}
              >
                <span style={{ fontSize: '10px', color: '#22c55e', display: 'block', fontWeight: 600, textTransform: 'uppercase' }}>
                  Paid
                </span>
                <span style={{ fontSize: '15px', fontWeight: 700, color: '#22c55e' }}>
                  ${Number(paymentStrip.paid || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('invoices')}
                title="Click to view balance and invoices"
                style={{
                  minHeight: '44px',
                  padding: '6px 10px',
                  background: isDark ? 'rgba(34, 211, 238, 0.08)' : 'rgba(234, 179, 8, 0.08)',
                  border: `1px solid ${activeTab === 'invoices' ? accentColor : 'transparent'}`,
                  borderRadius: '8px',
                  textAlign: 'left',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  transition: 'all 0.15s ease',
                }}
              >
                <span style={{ fontSize: '10px', color: accentColor, display: 'block', fontWeight: 600, textTransform: 'uppercase' }}>
                  Balance Due
                </span>
                <span style={{ fontSize: '15px', fontWeight: 700, color: accentColor }}>
                  ${Number(paymentStrip.balance || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </button>
            </div>

            {/* Quick Upload actions (min 44px tap targets, responsive wrapping) */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <input
                ref={fileInputRef}
                type="file"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFileUpload(f);
                }}
              />
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFileUpload(f, 'photo');
                }}
              />

              <button
                type="button"
                onClick={() => cameraInputRef.current?.click()}
                disabled={isUploading}
                style={{
                  minHeight: '44px',
                  minWidth: '44px',
                  padding: '8px 14px',
                  borderRadius: '8px',
                  background: isDark ? '#1a222f' : '#2d2d33',
                  border: `1px solid ${isDark ? 'rgba(34, 211, 238, 0.3)' : '#444'}`,
                  color: '#f5f2ed',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  flexShrink: 0,
                }}
              >
                <Camera size={16} color={accentColor} />
                <span>Camera</span>
              </button>

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                style={{
                  minHeight: '44px',
                  minWidth: '44px',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  background: isDark ? '#22d3ee' : '#b8960c',
                  border: 'none',
                  color: isDark ? '#06131a' : '#121214',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  flexShrink: 0,
                }}
              >
                <Upload size={16} />
                <span>Upload PDF / File</span>
              </button>
            </div>
          </div>

          {uploadSuccess && (
            <div
              style={{
                fontSize: '11px',
                color: '#22c55e',
                background: 'rgba(34,197,94,0.15)',
                padding: '6px 10px',
                borderRadius: '6px',
                border: '1px solid #16a34a',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <Check size={14} /> {uploadSuccess}
            </div>
          )}
        </div>

        {/* Tab Navigation (Scrollable horizontally on phone, min 44px tap targets, NO text overlap) */}
        <div
          style={{
            display: 'flex',
            overflowX: 'auto',
            background: tabBg,
            borderBottom: `1px solid ${cardBorder}`,
            padding: '0 8px',
            scrollbarWidth: 'none',
            WebkitOverflowScrolling: 'touch',
            flexShrink: 0,
          }}
        >
          {TABS.map((t) => {
            const isActive = activeTab === t.key;
            return (
              <button
                key={t.key}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => setActiveTab(t.key)}
                style={{
                  minHeight: '44px',
                  padding: '10px 16px',
                  border: 'none',
                  background: 'none',
                  borderBottom: isActive
                    ? `3px solid ${accentColor}`
                    : '3px solid transparent',
                  color: isActive
                    ? (isDark ? '#22d3ee' : '#1a1a1a')
                    : (isDark ? '#8b96a3' : '#666666'),
                  fontWeight: isActive ? 700 : 500,
                  fontSize: '12px',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  transition: 'all 0.15s ease',
                }}
              >
                {t.label}
              </button>
            );
          })}
        </div>

        {/* Content Body (Scrollable, Theme aware) */}
        <div
          style={{
            padding: '20px',
            overflowY: 'auto',
            flex: 1,
            backgroundColor: modalBg,
            color: textPrimary,
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
          }}
        >
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px', color: textMuted }}>
              <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 8px' }} />
              Loading folder contents...
            </div>
          ) : error ? (
            <div style={{ padding: '20px', background: isDark ? '#3b1818' : '#fef2f2', color: isDark ? '#fca5a5' : '#dc2626', borderRadius: '8px' }}>
              {error}
            </div>
          ) : (
            <>
              {/* TAB 1: Estimates */}
              {activeTab === 'estimates' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0, color: textPrimary }}>Estimates & Quotes</h3>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      style={{
                        minHeight: '44px',
                        padding: '8px 14px',
                        background: cardBg,
                        border: `1px solid ${accentColor}`,
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: 600,
                        color: accentColor,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      <Plus size={14} /> Upload Estimate
                    </button>
                  </div>
                  {estimates.length === 0 && !job?.quoted_amount ? (
                    <div style={{ padding: '24px', background: cardBg, borderRadius: '10px', textAlign: 'center', color: textMuted, border: `1px dashed ${cardBorder}` }}>
                      No estimate documents attached yet. Click upload to attach EST-2026 PDF.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
                      {estimates.map((doc: any) => (
                        <DocumentCard
                          key={doc.id}
                          doc={doc}
                          isDark={isDark}
                          accentColor={accentColor}
                          cardBg={cardBg}
                          cardBorder={cardBorder}
                          textPrimary={textPrimary}
                          textMuted={textMuted}
                          onOpenQuote={(qId) => {
                            onClose();
                            openRecord({ type: 'quote', id: qId });
                          }}
                        />
                      ))}
                      {job?.quoted_amount > 0 && estimates.length === 0 && (
                        <div
                          onClick={() => {
                            if (job?.quote_id) {
                              onClose();
                              openRecord({ type: 'quote', id: String(job.quote_id) });
                            }
                          }}
                          style={{
                            background: cardBg,
                            border: `1px solid ${cardBorder}`,
                            borderRadius: '10px',
                            padding: '14px',
                            cursor: job?.quote_id ? 'pointer' : 'default',
                          }}
                        >
                          <div style={{ fontSize: '11px', color: textMuted }}>
                            QUOTE TOTAL {job?.quote_id ? '• Click to view' : ''}
                          </div>
                          <div style={{ fontSize: '18px', fontWeight: 700, color: accentColor }}>
                            ${Number(job.quoted_amount).toLocaleString()}
                          </div>
                          <div style={{ fontSize: '11px', color: textMuted, marginTop: 4 }}>
                            Status: {job.pipeline_stage || 'active'}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: Invoices */}
              {activeTab === 'invoices' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0, color: textPrimary }}>Invoices</h3>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      style={{
                        minHeight: '44px',
                        padding: '8px 14px',
                        background: cardBg,
                        border: `1px solid ${accentColor}`,
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: 600,
                        color: accentColor,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      <Plus size={14} /> Upload Invoice PDF
                    </button>
                  </div>
                  {invoicesList.length === 0 ? (
                    <div style={{ padding: '24px', background: cardBg, borderRadius: '10px', textAlign: 'center', color: textMuted, border: `1px dashed ${cardBorder}` }}>
                      No invoices uploaded.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
                      {invoicesList.map((doc: any) => (
                        <DocumentCard
                          key={doc.id}
                          doc={doc}
                          isDark={isDark}
                          accentColor={accentColor}
                          cardBg={cardBg}
                          cardBorder={cardBorder}
                          textPrimary={textPrimary}
                          textMuted={textMuted}
                          onOpenInvoice={(invId) => {
                            onClose();
                            openRecord({ type: 'invoice', id: invId });
                          }}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: Change Orders */}
              {activeTab === 'change_orders' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0, color: textPrimary }}>Change Orders</h3>
                    <button
                      type="button"
                      onClick={() => setShowCOForm(!showCOForm)}
                      style={{
                        minHeight: '44px',
                        padding: '8px 14px',
                        background: accentColor,
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: 700,
                        color: isDark ? '#06131a' : '#121214',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      <Plus size={14} /> New Change Order
                    </button>
                  </div>

                  {showCOForm && (
                    <form
                      onSubmit={handleCreateChangeOrder}
                      style={{
                        background: cardBg,
                        border: `1px solid ${accentColor}`,
                        borderRadius: '10px',
                        padding: '16px',
                        marginBottom: 16,
                      }}
                    >
                      <h4 style={{ fontSize: '13px', fontWeight: 700, margin: '0 0 10px 0', color: textPrimary }}>Add Change Order</h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        <input
                          type="text"
                          placeholder="Change Order Title (e.g. Added blackout lining)"
                          value={coTitle}
                          onChange={(e) => setCoTitle(e.target.value)}
                          required
                          style={{
                            minHeight: '44px',
                            padding: '8px 12px',
                            borderRadius: '6px',
                            border: `1px solid ${inputBorder}`,
                            background: inputBg,
                            color: textPrimary,
                            fontSize: '13px',
                          }}
                        />
                        <input
                          type="number"
                          step="0.01"
                          placeholder="Amount ($ e.g. 450.00)"
                          value={coAmount}
                          onChange={(e) => setCoAmount(e.target.value)}
                          style={{
                            minHeight: '44px',
                            padding: '8px 12px',
                            borderRadius: '6px',
                            border: `1px solid ${inputBorder}`,
                            background: inputBg,
                            color: textPrimary,
                            fontSize: '13px',
                          }}
                        />
                        <textarea
                          placeholder="Details / reason for change..."
                          value={coDescription}
                          onChange={(e) => setCoDescription(e.target.value)}
                          rows={3}
                          style={{
                            padding: '8px 12px',
                            borderRadius: '6px',
                            border: `1px solid ${inputBorder}`,
                            background: inputBg,
                            color: textPrimary,
                            fontSize: '13px',
                          }}
                        />
                        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                          <button
                            type="button"
                            onClick={() => setShowCOForm(false)}
                            style={{
                              minHeight: '44px',
                              padding: '8px 14px',
                              borderRadius: '6px',
                              background: isDark ? '#1a222f' : '#f0ede8',
                              color: textPrimary,
                              border: 'none',
                              cursor: 'pointer',
                              fontSize: '12px',
                            }}
                          >
                            Cancel
                          </button>
                          <button
                            type="submit"
                            disabled={coSubmitting}
                            style={{
                              minHeight: '44px',
                              padding: '8px 16px',
                              borderRadius: '6px',
                              background: accentColor,
                              color: isDark ? '#06131a' : '#fff',
                              border: 'none',
                              fontWeight: 700,
                              cursor: 'pointer',
                              fontSize: '12px',
                            }}
                          >
                            {coSubmitting ? 'Saving...' : 'Save Change Order'}
                          </button>
                        </div>
                      </div>
                    </form>
                  )}

                  {changeOrders.length === 0 ? (
                    <div style={{ padding: '24px', background: cardBg, borderRadius: '10px', textAlign: 'center', color: textMuted, border: `1px dashed ${cardBorder}` }}>
                      No change orders recorded for this job.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
                      {changeOrders.map((co: any) => (
                        <div
                          key={co.id}
                          style={{
                            background: cardBg,
                            border: `1px solid ${cardBorder}`,
                            borderRadius: '10px',
                            padding: '14px',
                            borderLeft: `4px solid ${accentColor}`,
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <div style={{ fontWeight: 700, fontSize: '13px', color: textPrimary }}>{co.title}</div>
                            {co.metadata?.amount != null && (
                              <div style={{ fontWeight: 700, color: accentColor, fontSize: '13px' }}>
                                ${Number(co.metadata.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                              </div>
                            )}
                          </div>
                          {co.description && (
                            <div style={{ fontSize: '11px', color: textMuted, marginTop: 6 }}>{co.description}</div>
                          )}
                          <div style={{ fontSize: '10px', color: textMuted, marginTop: 10, display: 'flex', justifyContent: 'space-between' }}>
                            <span>Status: {co.metadata?.status || 'approved'}</span>
                            <span>{co.created_at ? new Date(co.created_at).toLocaleDateString() : ''}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 4: Drawings / Mockups */}
              {activeTab === 'drawings' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <div>
                      <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0, color: textPrimary }}>Drawings & Mockups</h3>
                      <p style={{ fontSize: '11px', color: textMuted, margin: '2px 0 0 0' }}>
                        All measurements displayed in standard shop fractions.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      style={{
                        minHeight: '44px',
                        padding: '8px 14px',
                        background: cardBg,
                        border: `1px solid ${accentColor}`,
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: 600,
                        color: accentColor,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      <Upload size={14} /> Upload Drawing
                    </button>
                  </div>

                  {/* Measurements Summary formatted strictly in shop fractions */}
                  {job?.measurements && Object.keys(job.measurements).length > 0 && (
                    <div
                      style={{
                        background: isDark ? 'rgba(34, 211, 238, 0.08)' : '#fdf8eb',
                        border: `1px solid ${isDark ? 'rgba(34, 211, 238, 0.3)' : '#d4b84a'}`,
                        borderRadius: '8px',
                        padding: '12px 14px',
                        marginBottom: 14,
                        fontSize: '12px',
                      }}
                    >
                      <div style={{ fontWeight: 700, color: accentColor, marginBottom: 6 }}>
                        Shop Measurements (Fractions)
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
                        {Object.entries(job.measurements).map(([k, v]) => (
                          <div key={k} style={{ background: cardBg, padding: '6px 12px', borderRadius: '6px', border: `1px solid ${cardBorder}` }}>
                            <span style={{ color: textMuted, textTransform: 'capitalize' }}>{k}: </span>
                            <strong style={{ color: textPrimary }}>{formatInches(v)}</strong>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {drawingsList.length === 0 ? (
                    <div style={{ padding: '24px', background: cardBg, borderRadius: '10px', textAlign: 'center', color: textMuted, border: `1px dashed ${cardBorder}` }}>
                      No drawing files attached yet.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
                      {drawingsList.map((doc: any) => (
                        <DocumentCard
                          key={doc.id}
                          doc={doc}
                          isDark={isDark}
                          accentColor={accentColor}
                          cardBg={cardBg}
                          cardBorder={cardBorder}
                          textPrimary={textPrimary}
                          textMuted={textMuted}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 5: Photos */}
              {activeTab === 'photos' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0, color: textPrimary }}>Job Photos</h3>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button
                        type="button"
                        onClick={() => cameraInputRef.current?.click()}
                        style={{
                          minHeight: '44px',
                          padding: '8px 14px',
                          background: isDark ? '#1a222f' : '#121214',
                          border: `1px solid ${accentColor}`,
                          borderRadius: '6px',
                          fontSize: '12px',
                          fontWeight: 600,
                          color: '#fff',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                        }}
                      >
                        <Camera size={14} color={accentColor} /> Take Photo
                      </button>
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        style={{
                          minHeight: '44px',
                          padding: '8px 14px',
                          background: cardBg,
                          border: `1px solid ${accentColor}`,
                          borderRadius: '6px',
                          fontSize: '12px',
                          fontWeight: 600,
                          color: accentColor,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                        }}
                      >
                        <Upload size={14} /> Upload Image
                      </button>
                    </div>
                  </div>
                  {photosList.length === 0 && (!job?.photos || job.photos.length === 0) ? (
                    <div style={{ padding: '24px', background: cardBg, borderRadius: '10px', textAlign: 'center', color: textMuted, border: `1px dashed ${cardBorder}` }}>
                      No photos attached. Use phone camera or upload photos to record pick-up, drapery, or fabrics.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
                      {photosList.map((doc: any) => (
                        <DocumentCard
                          key={doc.id}
                          doc={doc}
                          isImage
                          isDark={isDark}
                          accentColor={accentColor}
                          cardBg={cardBg}
                          cardBorder={cardBorder}
                          textPrimary={textPrimary}
                          textMuted={textMuted}
                        />
                      ))}
                      {(job?.photos || []).map((p: string, idx: number) => (
                        <div key={idx} style={{ background: cardBg, borderRadius: '8px', overflow: 'hidden', border: `1px solid ${cardBorder}` }}>
                          <img src={p} alt="Job" style={{ width: '100%', height: '140px', objectFit: 'cover' }} />
                          <div style={{ padding: '8px', fontSize: '11px', color: textMuted }}>Photo #{idx + 1}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 6: Emails */}
              {activeTab === 'emails' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0, color: textPrimary }}>Client Emails & Logs</h3>
                    <button
                      type="button"
                      onClick={() => setShowEmailForm(!showEmailForm)}
                      style={{
                        minHeight: '44px',
                        padding: '8px 14px',
                        background: accentColor,
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: 700,
                        color: isDark ? '#06131a' : '#121214',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      <Plus size={14} /> Log Email Thread
                    </button>
                  </div>

                  {showEmailForm && (
                    <form
                      onSubmit={handleCreateEmail}
                      style={{
                        background: cardBg,
                        border: `1px solid ${accentColor}`,
                        borderRadius: '10px',
                        padding: '16px',
                        marginBottom: 16,
                      }}
                    >
                      <h4 style={{ fontSize: '13px', fontWeight: 700, margin: '0 0 10px 0', color: textPrimary }}>Log Email Record</h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        <input
                          type="text"
                          placeholder="Subject"
                          value={emailSubject}
                          onChange={(e) => setEmailSubject(e.target.value)}
                          required
                          style={{
                            minHeight: '44px',
                            padding: '8px 12px',
                            borderRadius: '6px',
                            border: `1px solid ${inputBorder}`,
                            background: inputBg,
                            color: textPrimary,
                            fontSize: '13px',
                          }}
                        />
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                          <input
                            type="text"
                            placeholder="Sender (e.g. rafael@empireworkroom.com)"
                            value={emailSender}
                            onChange={(e) => setEmailSender(e.target.value)}
                            style={{
                              minHeight: '44px',
                              padding: '8px 12px',
                              borderRadius: '6px',
                              border: `1px solid ${inputBorder}`,
                              background: inputBg,
                              color: textPrimary,
                              fontSize: '13px',
                            }}
                          />
                          <input
                            type="text"
                            placeholder="Recipient (e.g. client@example.com)"
                            value={emailRecipient}
                            onChange={(e) => setEmailRecipient(e.target.value)}
                            style={{
                              minHeight: '44px',
                              padding: '8px 12px',
                              borderRadius: '6px',
                              border: `1px solid ${inputBorder}`,
                              background: inputBg,
                              color: textPrimary,
                              fontSize: '13px',
                            }}
                          />
                        </div>
                        <textarea
                          placeholder="Email message body or notes..."
                          value={emailBody}
                          onChange={(e) => setEmailBody(e.target.value)}
                          rows={4}
                          style={{
                            padding: '8px 12px',
                            borderRadius: '6px',
                            border: `1px solid ${inputBorder}`,
                            background: inputBg,
                            color: textPrimary,
                            fontSize: '13px',
                          }}
                        />
                        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                          <button
                            type="button"
                            onClick={() => setShowEmailForm(false)}
                            style={{
                              minHeight: '44px',
                              padding: '8px 14px',
                              borderRadius: '6px',
                              background: isDark ? '#1a222f' : '#f0ede8',
                              color: textPrimary,
                              border: 'none',
                              cursor: 'pointer',
                              fontSize: '12px',
                            }}
                          >
                            Cancel
                          </button>
                          <button
                            type="submit"
                            disabled={emailSubmitting}
                            style={{
                              minHeight: '44px',
                              padding: '8px 16px',
                              borderRadius: '6px',
                              background: accentColor,
                              color: isDark ? '#06131a' : '#fff',
                              border: 'none',
                              fontWeight: 700,
                              cursor: 'pointer',
                              fontSize: '12px',
                            }}
                          >
                            {emailSubmitting ? 'Saving...' : 'Save Email Log'}
                          </button>
                        </div>
                      </div>
                    </form>
                  )}

                  {emailsList.length === 0 ? (
                    <div style={{ padding: '24px', background: cardBg, borderRadius: '10px', textAlign: 'center', color: textMuted, border: `1px dashed ${cardBorder}` }}>
                      No emails logged for this job.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {emailsList.map((em: any) => (
                        <div
                          key={em.id}
                          style={{
                            background: cardBg,
                            border: `1px solid ${cardBorder}`,
                            borderRadius: '10px',
                            padding: '14px',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div style={{ fontWeight: 700, fontSize: '13px', color: textPrimary }}>{em.title}</div>
                            <div style={{ fontSize: '11px', color: textMuted }}>
                              {em.created_at ? new Date(em.created_at).toLocaleString() : ''}
                            </div>
                          </div>
                          {em.metadata?.sender && (
                            <div style={{ fontSize: '11px', color: textMuted, marginTop: 4 }}>
                              <strong>From:</strong> {em.metadata.sender} &nbsp; <strong>To:</strong> {em.metadata.recipient}
                            </div>
                          )}
                          {em.description && (
                            <div style={{ fontSize: '12px', color: textPrimary, marginTop: 8, whiteSpace: 'pre-wrap', background: isDark ? '#161f2c' : '#faf9f7', padding: '10px', borderRadius: '6px' }}>
                              {em.description}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 7: Files */}
              {activeTab === 'files' && (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <JobHeader job={String(jobId)} quote={job?.quote_id || null} className="is-panel" />
                    <div style={{ fontSize: 10, fontWeight: 700, color: textMuted, textTransform: 'uppercase', margin: '10px 0 6px' }}>Final Docs</div>
                    <DocsTab job={String(jobId)} quote={job?.quote_id || null} />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0, color: textPrimary }}>All Job Files & Documents</h3>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      style={{
                        minHeight: '44px',
                        padding: '8px 14px',
                        background: accentColor,
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: 700,
                        color: isDark ? '#06131a' : '#121214',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      <Upload size={14} /> Upload Any File
                    </button>
                  </div>
                  {docs.length === 0 ? (
                    <div style={{ padding: '24px', background: cardBg, borderRadius: '10px', textAlign: 'center', color: textMuted, border: `1px dashed ${cardBorder}` }}>
                      No documents uploaded yet.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
                      {docs.map((doc: any) => (
                        <DocumentCard
                          key={doc.id}
                          doc={doc}
                          isDark={isDark}
                          accentColor={accentColor}
                          cardBg={cardBg}
                          cardBorder={cardBorder}
                          textPrimary={textPrimary}
                          textMuted={textMuted}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 8: Payments (QuickBooks style drill down) */}
              {activeTab === 'payments' && (
                <div>
                  <h3 style={{ fontSize: '14px', fontWeight: 700, margin: '0 0 12px 0', color: textPrimary }}>Payment Ledger</h3>
                  {payments.length === 0 ? (
                    <div style={{ padding: '24px', background: cardBg, borderRadius: '10px', textAlign: 'center', color: textMuted, border: `1px dashed ${cardBorder}` }}>
                      No recorded payments in the database. Total paid: ${Number(paymentStrip.paid || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {payments.map((p: any) => (
                        <div
                          key={p.id}
                          style={{
                            background: cardBg,
                            border: `1px solid ${cardBorder}`,
                            borderRadius: '8px',
                            padding: '12px 14px',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            flexWrap: 'wrap',
                            gap: 8,
                          }}
                        >
                          <div>
                            <div style={{ fontWeight: 600, fontSize: '13px', color: textPrimary }}>
                              Payment #{p.id} {p.payment_method ? `• ${p.payment_method}` : ''}
                            </div>
                            <div style={{ fontSize: '11px', color: textMuted }}>
                              Date: {p.payment_date || p.created_at || 'Recorded'} • Status: {p.status || 'completed'}
                            </div>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                            <div style={{ fontSize: '15px', fontWeight: 700, color: '#16a34a' }}>
                              ${Number(p.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </div>
                            {p.invoice_id && (
                              <button
                                type="button"
                                onClick={() => {
                                  onClose();
                                  openRecord({ type: 'invoice', id: String(p.invoice_id) });
                                }}
                                style={{
                                  minHeight: '36px',
                                  padding: '4px 10px',
                                  borderRadius: '6px',
                                  border: `1px solid ${accentColor}`,
                                  background: 'none',
                                  color: accentColor,
                                  fontSize: '11px',
                                  fontWeight: 600,
                                  cursor: 'pointer',
                                }}
                              >
                                Invoice #{p.invoice_id} →
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 9: Notes / Timeline */}
              {activeTab === 'notes' && (
                <div>
                  <h3 style={{ fontSize: '14px', fontWeight: 700, margin: '0 0 12px 0', color: textPrimary }}>Job Notes & Activity Timeline</h3>
                  <form onSubmit={handleAddNote} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
                    <input
                      type="text"
                      placeholder="Add a progress note, measurement detail, or call log..."
                      value={newNote}
                      onChange={(e) => setNewNote(e.target.value)}
                      style={{
                        flex: 1,
                        minHeight: '44px',
                        padding: '8px 12px',
                        borderRadius: '8px',
                        border: `1px solid ${inputBorder}`,
                        background: inputBg,
                        color: textPrimary,
                        fontSize: '13px',
                      }}
                    />
                    <button
                      type="submit"
                      disabled={noteSubmitting}
                      style={{
                        minHeight: '44px',
                        padding: '8px 18px',
                        borderRadius: '8px',
                        background: accentColor,
                        color: isDark ? '#06131a' : '#121214',
                        fontWeight: 700,
                        border: 'none',
                        cursor: 'pointer',
                        fontSize: '12px',
                        flexShrink: 0,
                      }}
                    >
                      Add Note
                    </button>
                  </form>

                  {/* Notes & Timeline List */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {job?.notes && (
                      <div style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: '8px', padding: '12px' }}>
                        <div style={{ fontSize: '11px', fontWeight: 700, color: textMuted, marginBottom: 4 }}>PRIMARY NOTE</div>
                        <div style={{ fontSize: '13px', color: textPrimary }}>{job.notes}</div>
                      </div>
                    )}
                    {timeline.length > 0 && timeline.map((t: any, i: number) => (
                      <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: '12px' }}>
                        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: accentColor, marginTop: 4, flexShrink: 0 }} />
                        <div>
                          <div style={{ color: textPrimary, fontWeight: 500 }}>{t.event || t.title}</div>
                          <div style={{ color: textMuted, fontSize: '10px' }}>{t.date || t.timestamp}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function DocumentCard({
  doc,
  isImage,
  isDark,
  accentColor = '#b8960c',
  cardBg = '#fff',
  cardBorder = '#ece8e0',
  textPrimary = '#1a1a1a',
  textMuted = '#888',
  onOpenQuote,
  onOpenInvoice,
}: {
  doc: any;
  isImage?: boolean;
  isDark?: boolean;
  accentColor?: string;
  cardBg?: string;
  cardBorder?: string;
  textPrimary?: string;
  textMuted?: string;
  onOpenQuote?: (id: string) => void;
  onOpenInvoice?: (id: string) => void;
}) {
  const fileUrl = doc.file_path ? `${API}/files/${encodeURIComponent(doc.file_path)}` : doc.url;
  return (
    <div
      style={{
        background: cardBg,
        border: `1px solid ${cardBorder}`,
        borderRadius: '10px',
        padding: '12px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: 8,
      }}
    >
      <div>
        {isImage && fileUrl ? (
          <img
            src={fileUrl}
            alt={doc.title}
            style={{ width: '100%', height: '120px', objectFit: 'cover', borderRadius: '6px', marginBottom: 8 }}
          />
        ) : null}
        <div style={{ fontWeight: 600, fontSize: '12px', color: textPrimary, wordBreak: 'break-word' }}>
          {doc.title || doc.file_name}
        </div>
        <div style={{ fontSize: '10px', color: textMuted, marginTop: 2 }}>
          {doc.type || doc.category || 'file'} • {doc.file_size ? `${Math.round(doc.file_size / 1024)} KB` : ''}
        </div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 6, borderTop: `1px solid ${cardBorder}`, paddingTop: 8, flexWrap: 'wrap' }}>
        {doc.quote_id && onOpenQuote && (
          <button
            type="button"
            onClick={() => onOpenQuote(String(doc.quote_id))}
            style={{
              minHeight: '44px',
              minWidth: '44px',
              fontSize: '11px',
              color: accentColor,
              fontWeight: 600,
              padding: '6px 12px',
              borderRadius: '6px',
              background: isDark ? 'rgba(34, 211, 238, 0.1)' : 'rgba(184, 150, 12, 0.1)',
              border: `1px solid ${accentColor}`,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <FileText size={14} /> Open Quote
          </button>
        )}
        {doc.invoice_id && onOpenInvoice && (
          <button
            type="button"
            onClick={() => onOpenInvoice(String(doc.invoice_id))}
            style={{
              minHeight: '44px',
              minWidth: '44px',
              fontSize: '11px',
              color: accentColor,
              fontWeight: 600,
              padding: '6px 12px',
              borderRadius: '6px',
              background: isDark ? 'rgba(34, 211, 238, 0.1)' : 'rgba(184, 150, 12, 0.1)',
              border: `1px solid ${accentColor}`,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <Receipt size={14} /> Open Invoice
          </button>
        )}
        {fileUrl && (
          <a
            href={fileUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              fontSize: '11px',
              color: accentColor,
              fontWeight: 600,
              textDecoration: 'none',
              padding: '8px 12px',
              borderRadius: '6px',
              background: isDark ? 'rgba(255, 255, 255, 0.05)' : '#fdf8eb',
              border: `1px solid ${isDark ? 'rgba(255, 255, 255, 0.1)' : '#f0e6c8'}`,
              minHeight: '44px',
              minWidth: '44px',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 4,
            }}
          >
            <Eye size={14} /> Open File
          </a>
        )}
      </div>
    </div>
  );
}
