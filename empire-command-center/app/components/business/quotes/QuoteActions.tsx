'use client';

import React, { useState, useCallback } from 'react';
import { CheckCircle, Mail, FileDown, FileText, Hammer, X, Loader2 } from 'lucide-react';
import { API } from '../../../lib/api';

interface QuoteActionsProps {
  quoteId: string;
  status: string;
  compact?: boolean;
  onAction?: (action: string, result: any) => void;
}

export default function QuoteActions({ quoteId, status, compact, onAction }: QuoteActionsProps) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [showEmailModal, setShowEmailModal] = useState(false);

  const showToast = useCallback((message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  const handleAction = useCallback(async (action: string, url: string, method: string = 'POST', body?: any) => {
    setLoadingAction(action);
    try {
      const res = await fetch(`${API}${url}`, {
        method,
        headers: { 'Content-Type': 'application/json' },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      if (!res.ok) throw new Error(`Failed: ${res.status}`);

      if (action === 'pdf') {
        // Backend returns binary PDF — download as blob
        const blob = await res.blob();
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = `quote-${quoteId}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);
      }

      const result = action === 'pdf' ? {} : await res.json();

      showToast(
        action === 'accept' ? 'Quote accepted' :
        action === 'send' ? 'Quote sent via email' :
        action === 'pdf' ? 'PDF downloaded' :
        action === 'invoice' ? 'Invoice created from quote' :
        action === 'job' ? 'Job created from quote' : 'Done',
        'success'
      );
      onAction?.(action, result);
    } catch {
      showToast(`Failed to ${action.replace(/_/g, ' ')}`, 'error');
    } finally {
      setLoadingAction(null);
    }
  }, [quoteId, onAction, showToast]);

  const ActionBtn = ({ id, label, icon, color, show = true, onClick }: {
    id: string; label: string; icon: React.ReactNode; color: string; show?: boolean; onClick: () => void;
  }) => {
    if (!show) return null;
    const isLoading = loadingAction === id;

    if (compact) {
      return (
        <button
          onClick={onClick}
          disabled={isLoading || loadingAction !== null}
          title={label}
          className="inline-flex items-center justify-center transition-all disabled:opacity-50 cursor-pointer"
          style={{
            width: 32, height: 32, borderRadius: 10,
            backgroundColor: '#fff', color, border: '1px solid #ece8e0',
          }}
          onMouseEnter={e => { e.currentTarget.style.backgroundColor = color; e.currentTarget.style.color = '#fff'; e.currentTarget.style.borderColor = color; }}
          onMouseLeave={e => { e.currentTarget.style.backgroundColor = '#fff'; e.currentTarget.style.color = color; e.currentTarget.style.borderColor = '#ece8e0'; }}
        >
          {isLoading ? <Loader2 size={13} className="animate-spin" /> : icon}
        </button>
      );
    }

    return (
      <button
        onClick={onClick}
        disabled={isLoading || loadingAction !== null}
        className="inline-flex items-center gap-1.5 rounded-xl transition-all disabled:opacity-50 cursor-pointer"
        style={{
          padding: '0 16px',
          height: 40,
          fontSize: 12,
          fontWeight: 700,
          backgroundColor: '#fff',
          color: color,
          border: `1.5px solid ${color}`,
          borderRadius: 14,
        }}
        onMouseEnter={e => {
          e.currentTarget.style.backgroundColor = color;
          e.currentTarget.style.color = '#fff';
        }}
        onMouseLeave={e => {
          e.currentTarget.style.backgroundColor = '#fff';
          e.currentTarget.style.color = color;
        }}
      >
        {isLoading ? <Loader2 size={14} className="animate-spin" /> : icon}
        {label}
      </button>
    );
  };

  return (
    <div className="relative">
      {/* Toast */}
      {toast && (
        <div className={`absolute -top-11 left-0 right-0 z-10 px-3.5 py-2 rounded-xl text-xs font-bold text-center ${
          toast.type === 'success' ? 'text-[#22c55e]' : 'text-red-700'
        }`} style={{ backgroundColor: toast.type === 'success' ? '#f0fdf4' : '#fef2f2' }}>
          {toast.message}
        </div>
      )}

      <div className="flex items-center gap-2 flex-wrap">
        <ActionBtn
          id="accept"
          label="Accept"
          icon={<CheckCircle size={14} />}
          color="#22c55e"
          show={status !== 'accepted'}
          onClick={() => handleAction('accept', `/quotes/${quoteId}/accept`)}
        />
        <ActionBtn
          id="send"
          label="Send Email"
          icon={<Mail size={14} />}
          color="#2563eb"
          onClick={() => setShowEmailModal(true)}
        />
        <ActionBtn
          id="pdf"
          label="Download PDF"
          icon={<FileDown size={14} />}
          color="#b8960c"
          onClick={() => handleAction('pdf', `/quotes/${quoteId}/pdf?skip_verification=true`)}
        />
        <ActionBtn
          id="invoice"
          label="Create Invoice"
          icon={<FileText size={14} />}
          color="#7c3aed"
          onClick={() => handleAction('invoice', `/finance/invoices/from-quote/${quoteId}`)}
        />
        <ActionBtn
          id="job"
          label="Create Job"
          icon={<Hammer size={14} />}
          color="#16a34a"
          onClick={() => handleAction('job', `/jobs/from-quote/${quoteId}`)}
        />
      </div>

      {/* Email Modal */}
      {showEmailModal && (
        <EmailModal
          onClose={() => setShowEmailModal(false)}
          onSend={(email) => {
            setShowEmailModal(false);
            handleAction('send', `/quotes/${quoteId}/send`, 'POST', { email });
          }}
        />
      )}
    </div>
  );
}

function EmailModal({ onClose, onSend }: { onClose: () => void; onSend: (email: string) => void }) {
  const [email, setEmail] = useState('');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onClose}>
      <div className="empire-card" style={{ padding: 0, width: '100%', maxWidth: 384, boxShadow: '0 20px 60px rgba(0,0,0,0.12)' }} onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between" style={{ padding: '14px 20px', borderBottom: '1px solid #ece8e0' }}>
          <h3 className="text-sm font-bold text-[#1a1a1a]">Send Quote via Email</h3>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-[#f0ede8] transition-colors cursor-pointer">
            <X size={16} className="text-[#999]" />
          </button>
        </div>
        <div style={{ padding: '16px 20px' }}>
          <label className="section-label" style={{ fontSize: 10 }}>Email Address</label>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && email.trim() && onSend(email)}
            className="w-full px-3.5 py-2.5 text-sm border border-[#ece8e0] rounded-[14px] bg-[#faf9f7] outline-none focus:border-[#2563eb] transition-colors"
            placeholder="customer@example.com"
            autoFocus
          />
        </div>
        <div className="flex items-center justify-end gap-2" style={{ padding: '12px 20px', borderTop: '1px solid #ece8e0' }}>
          <button onClick={onClose} className="px-3.5 py-2 text-xs font-medium text-[#999] hover:text-[#555] transition-colors cursor-pointer">
            Cancel
          </button>
          <button
            onClick={() => email.trim() && onSend(email)}
            disabled={!email.trim()}
            className="px-4 py-2.5 text-xs font-bold text-white bg-[#2563eb] rounded-xl hover:bg-[#1d4ed8] disabled:opacity-50 transition-colors cursor-pointer"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
