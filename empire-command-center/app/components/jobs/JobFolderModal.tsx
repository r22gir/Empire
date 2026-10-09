'use client';
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { API } from '../../lib/api';
import { formatInches } from '../../lib/formatInches';
import { useJob, Job } from '../../hooks/useJob';
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
      setError(e.message || 'Failed to load job details');
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
        backgroundColor: 'rgba(18, 18, 22, 0.72)',
        backdropFilter: 'blur(4px)',
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
          maxWidth: '940px',
          maxHeight: '92vh',
          backgroundColor: '#faf9f7',
          borderRadius: '16px',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          border: '1px solid #ece8e0',
        }}
      >
        {/* Top Header - Black & Gold Bar */}
        <div
          style={{
            background: '#121214',
            color: '#fff',
            padding: '16px 20px',
            borderBottom: '2px solid #b8960c',
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <div
                style={{
                  background: 'linear-gradient(135deg, #b8960c, #d4af37)',
                  color: '#121214',
                  fontSize: '11px',
                  fontWeight: 800,
                  padding: '3px 8px',
                  borderRadius: '6px',
                  letterSpacing: '0.5px',
                }}
              >
                EMPIRE WORKROOM
              </div>
              <h2 style={{ fontSize: '18px', fontWeight: 700, margin: 0, color: '#fff' }}>
                {job?.client_name || 'Loading job...'}
              </h2>
              <span style={{ fontSize: '13px', color: '#b8960c', fontFamily: 'monospace' }}>
                {job?.job_number || (jobId ? `JOB-${jobId}` : '')}
              </span>
              {job?.title && (
                <span style={{ fontSize: '12px', color: '#aaa', borderLeft: '1px solid #333', paddingLeft: 8 }}>
                  {job.title}
                </span>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button
                type="button"
                onClick={handleSetCurrentActiveJob}
                title="Discuss this job with Max assistant"
                style={{
                  minHeight: '44px',
                  padding: '6px 14px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  background: isActiveInContext ? '#16a34a' : '#222',
                  color: '#fff',
                  border: isActiveInContext ? '1px solid #16a34a' : '1px solid #b8960c',
                  transition: 'all 0.15s ease',
                }}
              >
                <Briefcase size={14} color={isActiveInContext ? '#fff' : '#b8960c'} />
                {isActiveInContext ? 'Active with Max' : 'Discuss with Max'}
              </button>

              <button
                type="button"
                onClick={onClose}
                style={{
                  minHeight: '44px',
                  minWidth: '44px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'rgba(255,255,255,0.1)',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#fff',
                  cursor: 'pointer',
                }}
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Payment Strip Rollup */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: '#1c1c20',
              padding: '10px 14px',
              borderRadius: '10px',
              border: '1px solid #2d2d33',
              flexWrap: 'wrap',
              gap: 10,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
              <div>
                <span style={{ fontSize: '10px', color: '#888', display: 'block', fontWeight: 600, textTransform: 'uppercase' }}>
                  Total Invoiced / Est
                </span>
                <span style={{ fontSize: '15px', fontWeight: 700, color: '#f5f2ed' }}>
                  ${Number(paymentStrip.total || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
              <div style={{ width: '1px', height: '24px', background: '#333' }} />
              <div>
                <span style={{ fontSize: '10px', color: '#16a34a', display: 'block', fontWeight: 600, textTransform: 'uppercase' }}>
                  Paid
                </span>
                <span style={{ fontSize: '15px', fontWeight: 700, color: '#22c55e' }}>
                  ${Number(paymentStrip.paid || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
              <div style={{ width: '1px', height: '24px', background: '#333' }} />
              <div>
                <span style={{ fontSize: '10px', color: '#eab308', display: 'block', fontWeight: 600, textTransform: 'uppercase' }}>
                  Balance Due
                </span>
                <span style={{ fontSize: '15px', fontWeight: 700, color: '#eab308' }}>
                  ${Number(paymentStrip.balance || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
            </div>

            {/* Quick Upload actions */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
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
                  padding: '8px 12px',
                  borderRadius: '8px',
                  background: '#2d2d33',
                  border: '1px solid #444',
                  color: '#f5f2ed',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <Camera size={14} color="#b8960c" />
                <span className="hidden sm:inline">Camera</span>
              </button>

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                style={{
                  minHeight: '44px',
                  padding: '8px 14px',
                  borderRadius: '8px',
                  background: '#b8960c',
                  border: 'none',
                  color: '#121214',
                  fontSize: '11px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <Upload size={14} />
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
                padding: '4px 8px',
                borderRadius: '6px',
                border: '1px solid #16a34a',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <Check size={12} /> {uploadSuccess}
            </div>
          )}
        </div>

        {/* Tab Navigation (Scrollable horizontally on phone) */}
        <div
          style={{
            display: 'flex',
            overflowX: 'auto',
            background: '#fff',
            borderBottom: '1px solid #ece8e0',
            padding: '0 8px',
            scrollbarWidth: 'none',
          }}
        >
          {TABS.map((t) => {
            const isActive = activeTab === t.key;
            return (
              <button
                key={t.key}
                type="button"
                onClick={() => setActiveTab(t.key)}
                style={{
                  minHeight: '44px',
                  padding: '10px 16px',
                  border: 'none',
                  background: 'none',
                  borderBottom: isActive ? '3px solid #b8960c' : '3px solid transparent',
                  color: isActive ? '#1a1a1a' : '#666',
                  fontWeight: isActive ? 700 : 500,
                  fontSize: '12px',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
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

        {/* Content Body (Scrollable) */}
        <div
          style={{
            padding: '20px',
            overflowY: 'auto',
            flex: 1,
            backgroundColor: '#faf9f7',
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
          }}
        >
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#888' }}>
              <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 8px' }} />
              Loading folder contents...
            </div>
          ) : error ? (
            <div style={{ padding: '20px', background: '#fef2f2', color: '#dc2626', borderRadius: '8px' }}>
              {error}
            </div>
          ) : (
            <>
              {/* TAB 1: Estimates */}
              {activeTab === 'estimates' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0 }}>Estimates & Quotes</h3>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      style={{
                        minHeight: '44px',
                        padding: '6px 12px',
                        background: '#fff',
                        border: '1px solid #b8960c',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontWeight: 600,
                        color: '#b8960c',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                      }}
                    >
                      <Plus size={12} /> Upload Estimate
                    </button>
                  </div>
                  {estimates.length === 0 && !job?.quoted_amount ? (
                    <div style={{ padding: '24px', background: '#fff', borderRadius: '10px', textAlign: 'center', color: '#888', border: '1px dashed #d5d0c8' }}>
                      No estimate documents attached yet. Click upload to attach EST-2026 PDF.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
                      {estimates.map((doc: any) => (
                        <DocumentCard key={doc.id} doc={doc} />
                      ))}
                      {job?.quoted_amount > 0 && estimates.length === 0 && (
                        <div style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: '10px', padding: '14px' }}>
                          <div style={{ fontSize: '11px', color: '#888' }}>QUOTE TOTAL</div>
                          <div style={{ fontSize: '18px', fontWeight: 700, color: '#b8960c' }}>
                            ${Number(job.quoted_amount).toLocaleString()}
                          </div>
                          <div style={{ fontSize: '11px', color: '#555', marginTop: 4 }}>
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
                    <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0 }}>Invoices</h3>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      style={{
                        minHeight: '44px',
                        padding: '6px 12px',
                        background: '#fff',
                        border: '1px solid #b8960c',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontWeight: 600,
                        color: '#b8960c',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                      }}
                    >
                      <Plus size={12} /> Upload Invoice PDF
                    </button>
                  </div>
                  {invoicesList.length === 0 ? (
                    <div style={{ padding: '24px', background: '#fff', borderRadius: '10px', textAlign: 'center', color: '#888', border: '1px dashed #d5d0c8' }}>
                      No invoices uploaded.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
                      {invoicesList.map((doc: any) => (
                        <DocumentCard key={doc.id} doc={doc} />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: Change Orders */}
              {activeTab === 'change_orders' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0 }}>Change Orders</h3>
                    <button
                      type="button"
                      onClick={() => setShowCOForm(!showCOForm)}
                      style={{
                        minHeight: '44px',
                        padding: '6px 12px',
                        background: '#b8960c',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontWeight: 700,
                        color: '#121214',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                      }}
                    >
                      <Plus size={12} /> New Change Order
                    </button>
                  </div>

                  {showCOForm && (
                    <form
                      onSubmit={handleCreateChangeOrder}
                      style={{
                        background: '#fff',
                        border: '1px solid #b8960c',
                        borderRadius: '10px',
                        padding: '16px',
                        marginBottom: 16,
                      }}
                    >
                      <h4 style={{ fontSize: '13px', fontWeight: 700, margin: '0 0 10px 0' }}>Add Change Order</h4>
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
                            border: '1px solid #ddd',
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
                            border: '1px solid #ddd',
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
                            border: '1px solid #ddd',
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
                              background: '#f0ede8',
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
                              background: '#b8960c',
                              color: '#fff',
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
                    <div style={{ padding: '24px', background: '#fff', borderRadius: '10px', textAlign: 'center', color: '#888', border: '1px dashed #d5d0c8' }}>
                      No change orders recorded for this job.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
                      {changeOrders.map((co: any) => (
                        <div
                          key={co.id}
                          style={{
                            background: '#fff',
                            border: '1px solid #ece8e0',
                            borderRadius: '10px',
                            padding: '14px',
                            borderLeft: '4px solid #b8960c',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <div style={{ fontWeight: 700, fontSize: '13px', color: '#1a1a1a' }}>{co.title}</div>
                            {co.metadata?.amount != null && (
                              <div style={{ fontWeight: 700, color: '#b8960c', fontSize: '13px' }}>
                                ${Number(co.metadata.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                              </div>
                            )}
                          </div>
                          {co.description && (
                            <div style={{ fontSize: '11px', color: '#666', marginTop: 6 }}>{co.description}</div>
                          )}
                          <div style={{ fontSize: '10px', color: '#999', marginTop: 10, display: 'flex', justifyContent: 'space-between' }}>
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
                      <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0 }}>Drawings & Mockups</h3>
                      <p style={{ fontSize: '11px', color: '#888', margin: '2px 0 0 0' }}>
                        All measurements displayed in standard shop fractions.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      style={{
                        minHeight: '44px',
                        padding: '6px 12px',
                        background: '#fff',
                        border: '1px solid #b8960c',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontWeight: 600,
                        color: '#b8960c',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                      }}
                    >
                      <Upload size={12} /> Upload Drawing
                    </button>
                  </div>

                  {/* Measurements Summary if present */}
                  {job?.measurements && Object.keys(job.measurements).length > 0 && (
                    <div
                      style={{
                        background: '#fdf8eb',
                        border: '1px solid #d4b84a',
                        borderRadius: '8px',
                        padding: '12px 14px',
                        marginBottom: 14,
                        fontSize: '12px',
                      }}
                    >
                      <div style={{ fontWeight: 700, color: '#96750a', marginBottom: 6 }}>
                        Shop Measurements (Fractions)
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
                        {Object.entries(job.measurements).map(([k, v]) => (
                          <div key={k} style={{ background: '#fff', padding: '4px 10px', borderRadius: '6px', border: '1px solid #ece8e0' }}>
                            <span style={{ color: '#777', textTransform: 'capitalize' }}>{k}: </span>
                            <strong style={{ color: '#1a1a1a' }}>{formatInches(v)}</strong>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {drawingsList.length === 0 ? (
                    <div style={{ padding: '24px', background: '#fff', borderRadius: '10px', textAlign: 'center', color: '#888', border: '1px dashed #d5d0c8' }}>
                      No drawing files attached yet.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
                      {drawingsList.map((doc: any) => (
                        <DocumentCard key={doc.id} doc={doc} />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 5: Photos */}
              {activeTab === 'photos' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0 }}>Job Photos</h3>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button
                        type="button"
                        onClick={() => cameraInputRef.current?.click()}
                        style={{
                          minHeight: '44px',
                          padding: '6px 12px',
                          background: '#121214',
                          border: '1px solid #b8960c',
                          borderRadius: '6px',
                          fontSize: '11px',
                          fontWeight: 600,
                          color: '#fff',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 4,
                        }}
                      >
                        <Camera size={14} color="#b8960c" /> Take Photo
                      </button>
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        style={{
                          minHeight: '44px',
                          padding: '6px 12px',
                          background: '#fff',
                          border: '1px solid #b8960c',
                          borderRadius: '6px',
                          fontSize: '11px',
                          fontWeight: 600,
                          color: '#b8960c',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 4,
                        }}
                      >
                        <Upload size={14} /> Upload Image
                      </button>
                    </div>
                  </div>
                  {photosList.length === 0 && (!job?.photos || job.photos.length === 0) ? (
                    <div style={{ padding: '24px', background: '#fff', borderRadius: '10px', textAlign: 'center', color: '#888', border: '1px dashed #d5d0c8' }}>
                      No photos attached. Use phone camera or upload photos to record pick-up, drapery, or fabrics.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
                      {photosList.map((doc: any) => (
                        <DocumentCard key={doc.id} doc={doc} isImage />
                      ))}
                      {(job?.photos || []).map((p: string, idx: number) => (
                        <div key={idx} style={{ background: '#fff', borderRadius: '8px', overflow: 'hidden', border: '1px solid #ece8e0' }}>
                          <img src={p} alt="Job" style={{ width: '100%', height: '140px', objectFit: 'cover' }} />
                          <div style={{ padding: '8px', fontSize: '11px', color: '#555' }}>Photo #{idx + 1}</div>
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
                    <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0 }}>Client Emails & Logs</h3>
                    <button
                      type="button"
                      onClick={() => setShowEmailForm(!showEmailForm)}
                      style={{
                        minHeight: '44px',
                        padding: '6px 12px',
                        background: '#b8960c',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontWeight: 700,
                        color: '#121214',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                      }}
                    >
                      <Plus size={12} /> Log Email Thread
                    </button>
                  </div>

                  {showEmailForm && (
                    <form
                      onSubmit={handleCreateEmail}
                      style={{
                        background: '#fff',
                        border: '1px solid #b8960c',
                        borderRadius: '10px',
                        padding: '16px',
                        marginBottom: 16,
                      }}
                    >
                      <h4 style={{ fontSize: '13px', fontWeight: 700, margin: '0 0 10px 0' }}>Log Email Record</h4>
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
                            border: '1px solid #ddd',
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
                              border: '1px solid #ddd',
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
                              border: '1px solid #ddd',
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
                            border: '1px solid #ddd',
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
                              background: '#f0ede8',
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
                              background: '#b8960c',
                              color: '#fff',
                              border: 'none',
                              fontWeight: 700,
                              cursor: 'pointer',
                              fontSize: '12px',
                            }}
                          >
                            {emailSubmitting ? 'Saving...' : 'Save Email'}
                          </button>
                        </div>
                      </div>
                    </form>
                  )}

                  {emailsList.length === 0 ? (
                    <div style={{ padding: '24px', background: '#fff', borderRadius: '10px', textAlign: 'center', color: '#888', border: '1px dashed #d5d0c8' }}>
                      No emails logged for this job.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {emailsList.map((em: any) => (
                        <div
                          key={em.id}
                          style={{
                            background: '#fff',
                            border: '1px solid #ece8e0',
                            borderRadius: '10px',
                            padding: '14px',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div style={{ fontWeight: 700, fontSize: '13px', color: '#1a1a1a' }}>{em.title}</div>
                            <div style={{ fontSize: '11px', color: '#888' }}>
                              {em.created_at ? new Date(em.created_at).toLocaleString() : ''}
                            </div>
                          </div>
                          {em.metadata?.sender && (
                            <div style={{ fontSize: '11px', color: '#666', marginTop: 4 }}>
                              <strong>From:</strong> {em.metadata.sender} &nbsp; <strong>To:</strong> {em.metadata.recipient}
                            </div>
                          )}
                          {em.description && (
                            <div style={{ fontSize: '12px', color: '#333', marginTop: 8, whiteSpace: 'pre-wrap', background: '#faf9f7', padding: '10px', borderRadius: '6px' }}>
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
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0 }}>All Job Files & Documents</h3>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      style={{
                        minHeight: '44px',
                        padding: '6px 12px',
                        background: '#b8960c',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontWeight: 700,
                        color: '#121214',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                      }}
                    >
                      <Upload size={12} /> Upload Any File
                    </button>
                  </div>
                  {docs.length === 0 ? (
                    <div style={{ padding: '24px', background: '#fff', borderRadius: '10px', textAlign: 'center', color: '#888', border: '1px dashed #d5d0c8' }}>
                      No documents uploaded yet.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
                      {docs.map((doc: any) => (
                        <DocumentCard key={doc.id} doc={doc} />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 8: Payments */}
              {activeTab === 'payments' && (
                <div>
                  <h3 style={{ fontSize: '14px', fontWeight: 700, margin: '0 0 12px 0' }}>Payment Ledger</h3>
                  {payments.length === 0 ? (
                    <div style={{ padding: '24px', background: '#fff', borderRadius: '10px', textAlign: 'center', color: '#888', border: '1px dashed #d5d0c8' }}>
                      No recorded payments in the database. Total paid: ${Number(paymentStrip.paid || 0).toLocaleString()}
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {payments.map((p: any) => (
                        <div
                          key={p.id}
                          style={{
                            background: '#fff',
                            border: '1px solid #ece8e0',
                            borderRadius: '8px',
                            padding: '12px 14px',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                          }}
                        >
                          <div>
                            <div style={{ fontWeight: 600, fontSize: '13px', color: '#1a1a1a' }}>
                              Payment #{p.id} {p.payment_method ? `• ${p.payment_method}` : ''}
                            </div>
                            <div style={{ fontSize: '11px', color: '#888' }}>
                              Date: {p.payment_date || p.created_at || 'Recorded'} • Status: {p.status || 'completed'}
                            </div>
                          </div>
                          <div style={{ fontSize: '15px', fontWeight: 700, color: '#16a34a' }}>
                            ${Number(p.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
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
                  <h3 style={{ fontSize: '14px', fontWeight: 700, margin: '0 0 12px 0' }}>Job Notes & Activity Timeline</h3>
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
                        border: '1px solid #ddd',
                        fontSize: '13px',
                      }}
                    />
                    <button
                      type="submit"
                      disabled={noteSubmitting}
                      style={{
                        minHeight: '44px',
                        padding: '8px 16px',
                        borderRadius: '8px',
                        background: '#b8960c',
                        color: '#121214',
                        fontWeight: 700,
                        border: 'none',
                        cursor: 'pointer',
                        fontSize: '12px',
                      }}
                    >
                      Add Note
                    </button>
                  </form>

                  {/* Notes & Timeline List */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {job?.notes && (
                      <div style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: '8px', padding: '12px' }}>
                        <div style={{ fontSize: '11px', fontWeight: 700, color: '#888', marginBottom: 4 }}>PRIMARY NOTE</div>
                        <div style={{ fontSize: '13px', color: '#1a1a1a' }}>{job.notes}</div>
                      </div>
                    )}
                    {timeline.length > 0 && timeline.map((t: any, i: number) => (
                      <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: '12px' }}>
                        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#b8960c', marginTop: 4 }} />
                        <div>
                          <div style={{ color: '#1a1a1a', fontWeight: 500 }}>{t.event || t.title}</div>
                          <div style={{ color: '#999', fontSize: '10px' }}>{t.date || t.timestamp}</div>
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

function DocumentCard({ doc, isImage }: { doc: any; isImage?: boolean }) {
  const fileUrl = doc.file_path ? `${API}/files/${encodeURIComponent(doc.file_path)}` : doc.url;
  return (
    <div
      style={{
        background: '#fff',
        border: '1px solid #ece8e0',
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
        <div style={{ fontWeight: 600, fontSize: '12px', color: '#1a1a1a', wordBreak: 'break-word' }}>
          {doc.title || doc.file_name}
        </div>
        <div style={{ fontSize: '10px', color: '#888', marginTop: 2 }}>
          {doc.type || doc.category || 'file'} • {doc.file_size ? `${Math.round(doc.file_size / 1024)} KB` : ''}
        </div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 6, borderTop: '1px solid #f5f2ed', paddingTop: 8 }}>
        {fileUrl && (
          <a
            href={fileUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              fontSize: '11px',
              color: '#b8960c',
              fontWeight: 600,
              textDecoration: 'none',
              padding: '4px 8px',
              borderRadius: '4px',
              background: '#fdf8eb',
              minHeight: '32px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <Eye size={12} /> Open
          </a>
        )}
      </div>
    </div>
  );
}
