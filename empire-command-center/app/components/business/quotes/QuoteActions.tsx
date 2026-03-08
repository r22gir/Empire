'use client';

import React, { useState, useCallback } from 'react';
import { CheckCircle, Mail, FileDown, FileText, Hammer, X, Loader2 } from 'lucide-react';
import { API } from '../../../lib/api';

interface QuoteActionsProps {
  quoteId: string;
  status: string;
  onAction?: (action: string, result: any) => void;
}

export default function QuoteActions({ quoteId, status, onAction }: QuoteActionsProps) {
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
      const result = await res.json();

      if (action === 'pdf' && result.url) {
        window.open(result.url, '_blank');
      }

      showToast(
        action === 'accept' ? 'Quote accepted' :
        action === 'send' ? 'Quote sent via email' :
        action === 'pdf' ? 'PDF generated' :
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

  const ActionBtn = ({ id, label, icon, color, bgColor, hoverColor, show = true, onClick }: {
    id: string; label: string; icon: React.ReactNode; color: string; bgColor: string; hoverColor: string; show?: boolean; onClick: () => void;
  }) => {
    if (!show) return null;
    const isLoading = loadingAction === id;
    return (
      <button
        onClick={onClick}
        disabled={isLoading || loadingAction !== null}
        className={`inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg transition-colors disabled:opacity-50 ${bgColor} ${color} ${hoverColor}`}
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
        <div className={`absolute -top-10 left-0 right-0 z-10 px-3 py-1.5 rounded-lg text-xs font-medium text-center ${
          toast.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        }`}>
          {toast.message}
        </div>
      )}

      <div className="flex items-center gap-2 flex-wrap">
        <ActionBtn
          id="accept"
          label="Accept"
          icon={<CheckCircle size={14} />}
          color="text-white"
          bgColor="bg-[#16a34a]"
          hoverColor="hover:bg-[#15803d]"
          show={status !== 'accepted'}
          onClick={() => handleAction('accept', `/quotes/${quoteId}/accept`)}
        />
        <ActionBtn
          id="send"
          label="Send Email"
          icon={<Mail size={14} />}
          color="text-white"
          bgColor="bg-blue-600"
          hoverColor="hover:bg-blue-700"
          onClick={() => setShowEmailModal(true)}
        />
        <ActionBtn
          id="pdf"
          label="Download PDF"
          icon={<FileDown size={14} />}
          color="text-white"
          bgColor="bg-[#b8960c]"
          hoverColor="hover:bg-[#a68500]"
          onClick={() => handleAction('pdf', `/quotes/${quoteId}/pdf`)}
        />
        <ActionBtn
          id="invoice"
          label="Create Invoice"
          icon={<FileText size={14} />}
          color="text-white"
          bgColor="bg-[#7c3aed]"
          hoverColor="hover:bg-[#6d28d9]"
          onClick={() => handleAction('invoice', `/finance/invoices/from-quote/${quoteId}`)}
        />
        <ActionBtn
          id="job"
          label="Create Job"
          icon={<Hammer size={14} />}
          color="text-white"
          bgColor="bg-[#16a34a]"
          hoverColor="hover:bg-[#15803d]"
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
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-[#ece8e1]">
          <h3 className="text-sm font-bold text-[#1a1a1a]">Send Quote via Email</h3>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 transition-colors">
            <X size={16} className="text-gray-400" />
          </button>
        </div>
        <div className="px-5 py-4">
          <label className="text-[10px] font-bold text-gray-400 uppercase block mb-1">Email Address</label>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && email.trim() && onSend(email)}
            className="w-full px-3 py-2 text-sm border border-[#ece8e1] rounded-lg bg-white outline-none focus:border-blue-500"
            placeholder="customer@example.com"
            autoFocus
          />
        </div>
        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-[#ece8e1]">
          <button onClick={onClose} className="px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors">
            Cancel
          </button>
          <button
            onClick={() => email.trim() && onSend(email)}
            disabled={!email.trim()}
            className="px-4 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
