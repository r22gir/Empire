'use client';

import React, { useState, useCallback } from 'react';
import { CheckCircle, Mail, FileDown, FileText, Hammer, X, Loader2, Trash2 } from 'lucide-react';
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
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showApprovePinModal, setShowApprovePinModal] = useState(false);
  const [approvePin, setApprovePin] = useState('');
  const [approveError, setApproveError] = useState<string | null>(null);
  const [approving, setApproving] = useState(false);

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
        action === 'accept' ? 'Quote approved' :
        action === 'send' ? 'Quote sent via email' :
        action === 'pdf' ? 'PDF downloaded' :
        action === 'invoice' ? 'Invoice created from quote' :
        action === 'job' ? 'Job created from quote' :
        action === 'delete' ? 'Quote deleted' : 'Done',
        'success'
      );
      onAction?.(action, result);
    } catch {
      showToast(`Failed to ${action.replace(/_/g, ' ')}`, 'error');
    } finally {
      setLoadingAction(null);
    }
  }, [quoteId, onAction, showToast]);

  /** Founder PIN gate — same contract as QuoteReviewScreen approve_submit.
   *  POST /quotes-v2/{id}/approve with founder_pin. If still draft, submit
   *  for review first (draft → founder_review), then approve → sent.
   *  Never calls legacy /quotes/{id}/accept.
   */
  const submitApproveWithPin = useCallback(async () => {
    if (approving) return;
    const pin = approvePin.trim();
    if (!pin) {
      setApproveError('Founder PIN is required');
      return;
    }
    setApproving(true);
    setApproveError(null);
    setLoadingAction('accept');
    try {
      // Ensure quote is in founder_review before approve (state machine).
      const submitRes = await fetch(`${API}/quotes-v2/${quoteId}/submit-for-review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          changed_by: 'workroom-ui',
          reason: 'submitted ahead of founder approve from QuoteActions',
        }),
      });
      // 409 = already past draft (e.g. already founder_review) — continue
      if (!submitRes.ok && submitRes.status !== 409) {
        const err = await submitRes.json().catch(() => ({ detail: `HTTP ${submitRes.status}` }));
        throw new Error(typeof err.detail === 'string' ? err.detail : `submit-for-review failed (${submitRes.status})`);
      }

      const res = await fetch(`${API}/quotes-v2/${quoteId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          founder_pin: pin,
          changed_by: 'founder',
          reason: 'Approved from Workroom QuoteActions (PIN-gated)',
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        const detail = typeof err.detail === 'string' ? err.detail : `Approve failed (${res.status})`;
        setApproveError(detail);
        showToast(detail, 'error');
        return;
      }
      const result = await res.json();
      setShowApprovePinModal(false);
      setApprovePin('');
      showToast('Quote approved (PIN verified)', 'success');
      onAction?.('accept', result);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Approve failed';
      setApproveError(msg);
      showToast(msg, 'error');
    } finally {
      setApproving(false);
      setLoadingAction(null);
    }
  }, [approving, approvePin, quoteId, onAction, showToast]);


  const ActionBtn = ({ id, label, icon, color, show = true, onClick }: {
    id: string; label: string; icon: React.ReactNode; color: string; show?: boolean; onClick: () => void;
  }) => {
    if (!show) return null;
    const isLoading = loadingAction === id;

    if (compact) {
      return (
        <button
          onClick={(e) => { e.stopPropagation(); onClick(); }}
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
          label="Approve"
          icon={<CheckCircle size={14} />}
          color="#22c55e"
          show={!['accepted', 'sent', 'cancelled', 'in_production', 'completed'].includes(status)}
          onClick={() => {
            setApproveError(null);
            setApprovePin('');
            setShowApprovePinModal(true);
          }}
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
          onClick={() => handleAction('pdf', `/quotes-v2/${quoteId}/pdf`, 'GET')}
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
        <ActionBtn
          id="delete"
          label="Delete"
          icon={<Trash2 size={14} />}
          color="#dc2626"
          onClick={() => setShowDeleteConfirm(true)}
        />
      </div>


      {/* Founder PIN modal — quotes-v2 approve (mirrors QuoteReviewScreen) */}
      {showApprovePinModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          role="dialog"
          aria-modal="true"
          aria-labelledby="qa-approve-pin-title"
          onClick={() => {
            if (!approving) {
              setShowApprovePinModal(false);
              setApprovePin('');
              setApproveError(null);
            }
          }}
        >
          <div
            className="empire-card"
            style={{ padding: 0, width: '100%', maxWidth: 400, boxShadow: '0 20px 60px rgba(0,0,0,0.12)' }}
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between" style={{ padding: '14px 20px', borderBottom: '1px solid #ece8e0' }}>
              <h3 id="qa-approve-pin-title" className="text-sm font-bold text-[#1a1a1a]">
                Approve quote (founder PIN)
              </h3>
              <button
                onClick={() => {
                  if (!approving) {
                    setShowApprovePinModal(false);
                    setApprovePin('');
                    setApproveError(null);
                  }
                }}
                className="p-1.5 rounded-xl hover:bg-[#f0ede8] transition-colors cursor-pointer"
                aria-label="Close"
              >
                <X size={16} className="text-[#999]" />
              </button>
            </div>
            <div style={{ padding: '16px 20px' }}>
              <p className="text-xs text-[#555] mb-3" style={{ lineHeight: 1.45 }}>
                Approves via <code>POST /quotes-v2/{'{id}'}/approve</code>. PIN is
                validated server-side — this does not call legacy accept.
              </p>
              <label className="section-label" style={{ fontSize: 10 }}>Founder PIN</label>
              <input
                type="password"
                autoComplete="off"
                autoFocus
                value={approvePin}
                disabled={approving}
                onChange={e => setApprovePin(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') submitApproveWithPin(); }}
                className="w-full px-3.5 py-2.5 text-sm border border-[#ece8e0] rounded-[14px] bg-[#faf9f7] outline-none focus:border-[#16a34a] transition-colors"
                placeholder="Enter founder PIN"
                style={{ fontFamily: 'ui-monospace, monospace', letterSpacing: '0.12em' }}
              />
              {approveError && (
                <div className="mt-2 px-3 py-2 rounded-lg text-xs font-medium text-red-800" style={{ background: '#fef2f2', border: '1px solid #fecaca' }}>
                  {approveError}
                </div>
              )}
            </div>
            <div className="flex items-center justify-end gap-2" style={{ padding: '12px 20px', borderTop: '1px solid #ece8e0' }}>
              <button
                onClick={() => {
                  if (approving) return;
                  setShowApprovePinModal(false);
                  setApprovePin('');
                  setApproveError(null);
                }}
                disabled={approving}
                className="px-3.5 py-2 text-xs font-medium text-[#999] hover:text-[#555] transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={submitApproveWithPin}
                disabled={approving || !approvePin.trim()}
                className="px-4 py-2.5 text-xs font-bold text-white bg-[#16a34a] rounded-xl hover:bg-[#15803d] disabled:opacity-50 transition-colors cursor-pointer inline-flex items-center gap-1.5"
              >
                {approving ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle size={14} />}
                {approving ? 'Approving…' : 'Approve with PIN'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Email Modal */}
      {showEmailModal && (
        <EmailModal
          onClose={() => setShowEmailModal(false)}
          onSend={(email) => {
            setShowEmailModal(false);
            handleAction('send', `/quotes-v2/${quoteId}/submit-for-review`, 'POST', { changed_by: 'workroom-ui', reason: `review requested for ${email || 'no-email'}` });
          }}
        />
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setShowDeleteConfirm(false)}>
          <div className="empire-card" style={{ padding: 0, width: '100%', maxWidth: 384, boxShadow: '0 20px 60px rgba(0,0,0,0.12)' }} onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between" style={{ padding: '14px 20px', borderBottom: '1px solid #ece8e0' }}>
              <h3 className="text-sm font-bold text-[#1a1a1a]">Delete Quote</h3>
              <button onClick={() => setShowDeleteConfirm(false)} className="p-1.5 rounded-xl hover:bg-[#f0ede8] transition-colors cursor-pointer">
                <X size={16} className="text-[#999]" />
              </button>
            </div>
            <div style={{ padding: '16px 20px' }}>
              <p className="text-sm text-[#555]">Are you sure you want to delete quote {quoteId}? This cannot be undone.</p>
            </div>
            <div className="flex items-center justify-end gap-2" style={{ padding: '12px 20px', borderTop: '1px solid #ece8e0' }}>
              <button onClick={() => setShowDeleteConfirm(false)} className="px-3.5 py-2 text-xs font-medium text-[#999] hover:text-[#555] transition-colors cursor-pointer">
                Cancel
              </button>
              <button
                onClick={() => { setShowDeleteConfirm(false); handleAction('delete', `/quotes-v2/${quoteId}`, 'DELETE'); }}
                className="px-4 py-2.5 text-xs font-bold text-white bg-red-600 rounded-xl hover:bg-red-700 transition-colors cursor-pointer"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
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
