'use client';

import React, { useState } from 'react';
import { CreditCard, Copy, Check, Loader2 } from 'lucide-react';
import { API } from '../../../lib/api';

export interface DepositCustomer {
  name?: string;
  email?: string;
  phone?: string;
  address?: string;
}

export interface DepositPayLinkResult {
  invoice?: {
    id?: string;
    invoice_number?: string;
    total?: number;
    balance_due?: number;
    client_name?: string;
    client_email?: string;
    client_phone?: string;
    client_address?: string;
  };
  invoice_created?: boolean;
  payment_status?: string;
  customer?: DepositCustomer;
  copied_from_quote?: boolean;
  business?: string;
  return_host_note?: string;
  pay_link?: {
    checkout_url?: string | null;
    session_id?: string | null;
    amount?: number;
    reused?: boolean;
    stripe_configured?: boolean;
    payment_status?: string;
    error?: string | null;
    return_host_note?: string;
  };
}

function statusLabel(status?: string | null): string {
  switch (status) {
    case 'paid':
      return 'Paid';
    case 'partial':
      return 'Partial';
    case 'link_ready':
      return 'Link ready — not paid';
    case 'awaiting_confirmation':
      return 'Awaiting Stripe confirmation';
    case 'expired':
      return 'Link expired';
    case 'failed':
      return 'Payment failed';
    case 'link_pending':
      return 'Creating link';
    default:
      return 'Unpaid';
  }
}

function money(n?: number | null): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n || 0);
}

export default function DepositPayLinkButton({
  quoteId,
  compact = false,
  customer,
}: {
  quoteId: string;
  compact?: boolean;
  customer?: DepositCustomer;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DepositPayLinkResult | null>(null);
  const [copied, setCopied] = useState(false);

  const requestLink = async () => {
    setOpen(true);
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/finance/quotes/${quoteId}/deposit-pay-link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail;
        throw new Error(typeof detail === 'string' ? detail : detail?.message || `Deposit link failed (${res.status})`);
      }
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Deposit link failed');
    } finally {
      setLoading(false);
    }
  };

  const checkoutUrl = result?.pay_link?.checkout_url || '';
  const paymentStatus = result?.payment_status || result?.pay_link?.payment_status;
  const shownCustomer = result?.customer || customer;

  const copyLink = async () => {
    if (!checkoutUrl) return;
    try {
      await navigator.clipboard.writeText(checkoutUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError('Could not copy the link');
    }
  };

  return (
    <>
      {compact ? (
        <button
          onClick={(e) => { e.stopPropagation(); requestLink(); }}
          disabled={loading}
          title="Deposit pay link"
          className="inline-flex items-center justify-center transition-all disabled:opacity-50 cursor-pointer"
          style={{ width: 32, height: 32, borderRadius: 10, backgroundColor: '#fff', color: '#0f766e', border: '1px solid #ece8e0' }}
        >
          {loading ? <Loader2 size={13} className="animate-spin" /> : <CreditCard size={13} />}
        </button>
      ) : (
        <button
          onClick={requestLink}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-xl transition-all disabled:opacity-50 cursor-pointer"
          style={{
            padding: '0 16px',
            height: 40,
            fontSize: 12,
            fontWeight: 700,
            backgroundColor: '#fff',
            color: '#0f766e',
            border: '1.5px solid #0f766e',
            borderRadius: 14,
          }}
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <CreditCard size={14} />}
          Deposit link
        </button>
      )}

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" onClick={() => setOpen(false)}>
          <div className="empire-card" style={{ padding: 0, width: '100%', maxWidth: 480, boxShadow: '0 20px 60px rgba(0,0,0,0.12)' }} onClick={e => e.stopPropagation()}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid #ece8e0' }}>
              <h3 className="text-sm font-bold text-[#1a1a1a]">Deposit pay link</h3>
              <p className="text-[11px] text-[#888] mt-1">Client details come from the quote. Nothing is marked paid until Stripe says so.</p>
            </div>
            <div style={{ padding: '16px 20px' }} className="space-y-3">
              {shownCustomer && (
                <div className="text-xs text-[#555] space-y-1">
                  <div><span className="text-[#999]">Client </span>{shownCustomer.name || '—'}</div>
                  <div><span className="text-[#999]">Email </span>{shownCustomer.email || '—'}</div>
                  <div><span className="text-[#999]">Phone </span>{shownCustomer.phone || '—'}</div>
                  <div><span className="text-[#999]">Address </span>{shownCustomer.address || '—'}</div>
                </div>
              )}
              {loading && <p className="text-xs text-[#777]">Creating the deposit invoice and pay link…</p>}
              {error && <p className="text-xs text-red-700">{error}</p>}
              {result && (
                <div className="text-xs text-[#333] space-y-2">
                  <div>Invoice {result.invoice?.invoice_number || result.invoice?.id} · {money(result.pay_link?.amount ?? result.invoice?.balance_due ?? result.invoice?.total)}</div>
                  <div>Payment status: <strong>{statusLabel(paymentStatus)}</strong>{result.pay_link?.reused ? ' · existing link' : ''}</div>
                  {result.pay_link?.error && <p className="text-red-700">{result.pay_link.error}</p>}
                  {checkoutUrl ? (
                    <div>
                      <a href={checkoutUrl} target="_blank" rel="noreferrer" className="break-all text-[#0f766e] underline">{checkoutUrl}</a>
                      <button onClick={copyLink} className="mt-2 inline-flex items-center gap-1 px-3 py-1.5 text-[11px] font-bold text-white bg-[#0f766e] rounded-lg cursor-pointer">
                        {copied ? <Check size={12} /> : <Copy size={12} />} {copied ? 'Copied' : 'Copy pay link'}
                      </button>
                    </div>
                  ) : (
                    <p className="text-[#777]">No pay link yet. The invoice is saved with the quote’s client.</p>
                  )}
                  {result.return_host_note && <p className="text-[10px] text-[#999] leading-snug">{result.return_host_note}</p>}
                </div>
              )}
            </div>
            <div className="flex justify-end" style={{ padding: '12px 20px', borderTop: '1px solid #ece8e0' }}>
              <button onClick={() => setOpen(false)} className="px-3 py-2 text-xs font-medium text-[#555] cursor-pointer">Close</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
