'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { Wallet, Copy, Check, ArrowLeft, Loader2, Send, CheckCircle, AlertCircle } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

// ============ TYPES ============

interface CryptoCheckoutProps {
  invoiceId: string;
  onBack: () => void;
}

interface CoinInfo {
  coin: string;        // btc, eth, sol, usdt_trc20, usdc_eth
  label: string;       // "Bitcoin (BTC)"
  network: string;     // "Bitcoin"
  address: string;
  usd_amount: number;
  crypto_amount?: number;
  price_usd?: number;
}

interface CheckoutData {
  invoice_id: string;
  invoice_number: string;
  customer_name: string;
  original_total: number;
  crypto_discount_pct: number;
  discounted_total: number;
  coins: CoinInfo[];
  note: string;
}

// ============ CONSTANTS ============

const COIN_COLORS: Record<string, string> = {
  btc: '#f7931a',
  eth: '#627eea',
  sol: '#9945ff',
  usdt_trc20: '#26a17b',
  usdc_eth: '#2775ca',
};

const COIN_ABBR: Record<string, string> = {
  btc: 'BTC',
  eth: 'ETH',
  sol: 'SOL',
  usdt_trc20: 'USDT',
  usdc_eth: 'USDC',
};

const API = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? 'https://api.empirebox.store/api/v1'
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1');

const ACCENT = '#16a34a';
const BORDER = '#e8e4dc';
const PAGE_BG = '#faf9f7';
const MUTED = '#6b7280';

// ============ COMPONENT ============

export default function CryptoCheckout({ invoiceId, onBack }: CryptoCheckoutProps) {
  const [data, setData] = useState<CheckoutData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCoin, setSelectedCoin] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [txHash, setTxHash] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`${API}/crypto-checkout/${invoiceId}`)
      .then(async (res) => {
        if (!res.ok) {
          const text = await res.text();
          throw new Error(text || `Error ${res.status}`);
        }
        return res.json();
      })
      .then((d) => { if (!cancelled) setData(d); })
      .catch((err) => { if (!cancelled) setError(err.message || 'Failed to load invoice'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [invoiceId]);

  const activeCoin = data?.coins.find((c) => c.coin === selectedCoin) || null;

  const formatCryptoAmount = (coin: CoinInfo): string => {
    if (!coin.crypto_amount) return coin.usd_amount.toFixed(2);
    if (coin.coin === 'btc') return coin.crypto_amount.toFixed(8);
    if (coin.coin === 'eth') return coin.crypto_amount.toFixed(6);
    if (coin.coin === 'sol') return coin.crypto_amount.toFixed(4);
    return coin.crypto_amount.toFixed(2);
  };

  const handleCopy = async () => {
    if (!activeCoin?.address) return;
    try {
      await navigator.clipboard.writeText(activeCoin.address);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* clipboard may be blocked */ }
  };

  const handleNotify = async () => {
    if (!activeCoin) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`${API}/crypto-checkout/${invoiceId}/notify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          coin: activeCoin.coin,
          amount_crypto: activeCoin.crypto_amount,
          tx_hash: txHash.trim() || undefined,
        }),
      });
      if (!res.ok) throw new Error('Failed to send notification');
      setSubmitted(true);
    } catch (e: any) {
      setError(e.message || 'Failed to send payment notification');
    } finally {
      setSubmitting(false);
    }
  };

  // ---- Loading ----
  if (loading) {
    return (
      <div style={{ background: PAGE_BG, minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Loader2 size={32} className="animate-spin" style={{ color: MUTED }} />
      </div>
    );
  }

  // ---- Error (no data) ----
  if (error && !data) {
    return (
      <div style={{ background: PAGE_BG, minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div style={{ background: '#fff', borderRadius: 12, border: `1px solid ${BORDER}`, padding: 32, maxWidth: 420, width: '100%', textAlign: 'center' }}>
          <AlertCircle size={40} style={{ color: '#dc2626', marginBottom: 12 }} />
          <p style={{ color: '#1f2937', fontSize: 16, marginBottom: 20 }}>{error}</p>
          <button onClick={onBack} style={{ ...btnStyle, background: '#f3f4f6', color: '#374151' }}>
            <ArrowLeft size={16} /> Go Back
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  // ---- Confirmation ----
  if (submitted && activeCoin) {
    return (
      <div style={{ background: PAGE_BG, minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div style={{ background: '#fff', borderRadius: 12, border: `1px solid ${BORDER}`, padding: 40, maxWidth: 480, width: '100%', textAlign: 'center' }}>
          <div style={{ width: 64, height: 64, borderRadius: '50%', background: '#dcfce7', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
            <CheckCircle size={32} style={{ color: ACCENT }} />
          </div>
          <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1f2937', marginBottom: 8 }}>Payment Notification Sent</h2>
          <p style={{ color: MUTED, fontSize: 15, lineHeight: 1.6, marginBottom: 28 }}>
            The owner will verify your transaction and mark the invoice as paid.
          </p>
          <div style={{ background: '#f9fafb', borderRadius: 8, padding: 16, marginBottom: 24, fontSize: 14, color: '#374151', textAlign: 'left' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ color: MUTED }}>Invoice</span>
              <span style={{ fontWeight: 500 }}>{data.invoice_number}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ color: MUTED }}>Coin</span>
              <span style={{ fontWeight: 500 }}>{activeCoin.label}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: MUTED }}>Amount</span>
              <span style={{ fontWeight: 500 }}>{formatCryptoAmount(activeCoin)} {COIN_ABBR[activeCoin.coin] || activeCoin.coin}</span>
            </div>
          </div>
          <button onClick={onBack} style={{ ...btnStyle, background: '#f3f4f6', color: '#374151' }}>
            <ArrowLeft size={16} /> Back to Invoice
          </button>
        </div>
      </div>
    );
  }

  // ---- Main checkout ----
  return (
    <div style={{ background: PAGE_BG, minHeight: '100vh', padding: '24px 16px' }}>
      <div style={{ maxWidth: 560, margin: '0 auto' }}>
        {/* Back button */}
        <button onClick={onBack} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', cursor: 'pointer', color: MUTED, fontSize: 14, marginBottom: 20, padding: '8px 0', minHeight: 44 }}>
          <ArrowLeft size={16} /> Back
        </button>

        {/* Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: '#dcfce7', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Wallet size={20} style={{ color: ACCENT }} />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1f2937', margin: 0 }}>Pay with Crypto</h1>
            <p style={{ fontSize: 13, color: MUTED, margin: 0 }}>Invoice {data.invoice_number}</p>
          </div>
        </div>

        {/* Invoice Summary */}
        <div style={cardStyle}>
          <h2 style={sectionTitle}>Invoice Summary</h2>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: 14, color: '#374151' }}>
            <span>Subtotal</span>
            <span>${data.original_total.toFixed(2)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: 14, color: ACCENT, fontWeight: 500 }}>
            <span>Crypto Discount ({data.crypto_discount_pct}%)</span>
            <span>-${(data.original_total - data.discounted_total).toFixed(2)}</span>
          </div>
          <div style={{ borderTop: `1px solid ${BORDER}`, marginTop: 12, paddingTop: 12, display: 'flex', justifyContent: 'space-between', fontSize: 18, fontWeight: 600, color: '#1f2937' }}>
            <span>Total</span>
            <span>${data.discounted_total.toFixed(2)}</span>
          </div>
        </div>

        {/* Coin Selector */}
        <div style={cardStyle}>
          <h2 style={sectionTitle}>Select Cryptocurrency</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10 }}>
            {data.coins.map((coin) => {
              const isSelected = selectedCoin === coin.coin;
              const color = COIN_COLORS[coin.coin] || '#666';
              const abbr = COIN_ABBR[coin.coin] || coin.coin.toUpperCase();
              return (
                <button
                  key={coin.coin}
                  onClick={() => { setSelectedCoin(coin.coin); setCopied(false); setError(null); }}
                  style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
                    padding: '16px 12px', borderRadius: 10, cursor: 'pointer',
                    minHeight: 44,
                    border: isSelected ? `2px solid ${color}` : `1px solid ${BORDER}`,
                    background: isSelected ? `${color}0D` : '#fff',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{
                    width: 40, height: 40, borderRadius: '50%', background: color,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: '#fff', fontWeight: 700, fontSize: 12,
                  }}>
                    {abbr}
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#1f2937' }}>{coin.label.split(' (')[0]}</div>
                    <div style={{ fontSize: 11, color: MUTED, marginTop: 2 }}>{coin.network}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Payment Details */}
        {activeCoin && (
          <div style={cardStyle}>
            <h2 style={sectionTitle}>Payment Details</h2>

            {/* Amount */}
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <div style={{ fontSize: 13, color: MUTED, marginBottom: 4 }}>Send exactly</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#1f2937', letterSpacing: '-0.02em' }}>
                {formatCryptoAmount(activeCoin)}{' '}
                <span style={{ color: COIN_COLORS[activeCoin.coin] || '#666' }}>{COIN_ABBR[activeCoin.coin] || activeCoin.coin}</span>
              </div>
              {activeCoin.price_usd && activeCoin.price_usd > 1 && (
                <div style={{ fontSize: 12, color: MUTED, marginTop: 4 }}>
                  1 {COIN_ABBR[activeCoin.coin]} = ${activeCoin.price_usd.toLocaleString()}
                </div>
              )}
            </div>

            {/* QR Code */}
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 24 }}>
              <div style={{ background: '#fff', padding: 16, borderRadius: 12, border: `1px solid ${BORDER}` }}>
                <QRCodeSVG value={activeCoin.address} size={180} bgColor="#ffffff" fgColor="#1f2937" level="M" />
              </div>
            </div>

            {/* Address */}
            <div style={{ marginBottom: 24 }}>
              <label style={{ display: 'block', fontSize: 13, color: MUTED, marginBottom: 6 }}>Wallet Address</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#f9fafb', borderRadius: 8, border: `1px solid ${BORDER}`, padding: '10px 12px' }}>
                <code style={{ flex: 1, fontSize: 13, color: '#374151', wordBreak: 'break-all', fontFamily: 'monospace', lineHeight: 1.5 }}>
                  {activeCoin.address}
                </code>
                <button onClick={handleCopy} style={{
                  flexShrink: 0, display: 'flex', alignItems: 'center', gap: 4,
                  padding: '8px 12px', borderRadius: 6, border: 'none', cursor: 'pointer',
                  minHeight: 44, minWidth: 44,
                  background: copied ? '#dcfce7' : '#fff', color: copied ? ACCENT : '#374151',
                  fontSize: 13, fontWeight: 500, boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                }}>
                  {copied ? <Check size={16} /> : <Copy size={16} />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
            </div>

            {/* TX Hash (optional) */}
            <div style={{ marginBottom: 24 }}>
              <label style={{ display: 'block', fontSize: 13, color: MUTED, marginBottom: 6 }}>
                Transaction Hash <span style={{ color: '#9ca3af' }}>(optional)</span>
              </label>
              <input
                type="text" value={txHash} onChange={(e) => setTxHash(e.target.value)}
                placeholder="Paste your transaction hash here"
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: `1px solid ${BORDER}`, fontSize: 14, color: '#374151', fontFamily: 'monospace', outline: 'none', boxSizing: 'border-box', minHeight: 44 }}
              />
            </div>

            {/* Error */}
            {error && (
              <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, color: '#dc2626' }}>
                <AlertCircle size={16} /> {error}
              </div>
            )}

            {/* Submit */}
            <button onClick={handleNotify} disabled={submitting} style={{
              width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              padding: '14px 20px', borderRadius: 10, border: 'none',
              cursor: submitting ? 'not-allowed' : 'pointer',
              background: submitting ? '#9ca3af' : ACCENT, color: '#fff',
              fontSize: 15, fontWeight: 600, minHeight: 48,
            }}>
              {submitting ? <><Loader2 size={18} className="animate-spin" /> Sending...</> : <><Send size={18} /> I've Sent the Payment</>}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ============ SHARED STYLES ============

const BORDER_CONST = '#e8e4dc';

const cardStyle: React.CSSProperties = {
  background: '#fff', borderRadius: 12,
  border: `1px solid ${BORDER_CONST}`, padding: 24, marginBottom: 16,
};

const sectionTitle: React.CSSProperties = {
  fontSize: 15, fontWeight: 600, color: '#1f2937', marginTop: 0, marginBottom: 16,
};

const btnStyle: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 6,
  padding: '10px 20px', borderRadius: 8, border: 'none',
  cursor: 'pointer', fontSize: 14, fontWeight: 500, minHeight: 44,
};
