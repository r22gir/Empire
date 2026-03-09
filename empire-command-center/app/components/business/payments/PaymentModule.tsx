'use client';
import React, { useState, useEffect, useCallback } from 'react';
import {
  CreditCard, DollarSign, FileText, Send, Copy, Check, Loader2,
  Clock, Download, ExternalLink, X, ChevronDown, AlertTriangle,
  CheckCircle, Link2, Mail, QrCode, Wallet, Timer, RefreshCw,
} from 'lucide-react';

// ============ TYPES ============

export interface PaymentRecord {
  id: string;
  product: string;
  orderId?: string;
  method: PaymentMethod;
  amount: number;
  currency: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'refunded';
  customerName?: string;
  customerEmail?: string;
  description?: string;
  reference?: string;
  createdAt: string;
}

type PaymentMethod = 'card' | 'paypal' | 'crypto' | 'invoice' | 'zelle';

export interface PaymentModuleProps {
  product: string; // 'llc' | 'apost' | 'workroom' | 'craft' | etc
  orderId?: string;
  amount?: number;
  customerName?: string;
  customerEmail?: string;
  description?: string;
  onPaymentComplete?: (payment: PaymentRecord) => void;
}

// ============ HELPERS ============

const GOLD = '#b8960c';
const GOLD_BG = '#fdf8eb';
const CARD_BG = '#fff';
const PAGE_BG = '#faf9f7';
const BORDER = '#ece8e0';
const MUTED = '#6b7280';

const STATUS_COLORS: Record<string, { bg: string; color: string; label: string }> = {
  pending:    { bg: '#fef3c7', color: '#92400e', label: 'Pending' },
  processing: { bg: '#dbeafe', color: '#2563eb', label: 'Processing' },
  completed:  { bg: '#dcfce7', color: '#16a34a', label: 'Completed' },
  failed:     { bg: '#fee2e2', color: '#dc2626', label: 'Failed' },
  refunded:   { bg: '#f3e8ff', color: '#7c3aed', label: 'Refunded' },
};

const PAYMENT_METHODS: { id: PaymentMethod; label: string; icon: React.ElementType; sub: string }[] = [
  { id: 'card', label: 'Credit/Debit Card', icon: CreditCard, sub: 'Visa, MC, Amex' },
  { id: 'paypal', label: 'PayPal', icon: DollarSign, sub: 'PayPal checkout' },
  { id: 'crypto', label: 'Crypto', icon: Wallet, sub: '10% discount' },
  { id: 'invoice', label: 'Invoice', icon: FileText, sub: 'Pay Later / Net 30' },
  { id: 'zelle', label: 'Zelle / Wire', icon: Send, sub: 'Business transfers' },
];

const CRYPTO_TOKENS = ['USDC', 'SOL', 'ETH', 'EMPIRE'];
const CRYPTO_RATES: Record<string, number> = { USDC: 1, SOL: 0.0067, ETH: 0.00028, EMPIRE: 100 };
const MOCK_WALLETS: Record<string, string> = {
  USDC: '0x7a3B...eF92',
  SOL: 'Emp1r...x4Bz',
  ETH: '0x7a3B...eF92',
  EMPIRE: 'empire1...q8kz',
};

function genId() {
  return 'PAY-' + Math.random().toString(36).substring(2, 10).toUpperCase();
}

function formatCard(v: string) {
  return v.replace(/\D/g, '').replace(/(.{4})/g, '$1 ').trim().slice(0, 19);
}

function formatExpiry(v: string) {
  const d = v.replace(/\D/g, '').slice(0, 4);
  if (d.length >= 3) return d.slice(0, 2) + '/' + d.slice(2);
  return d;
}

// ============ MAIN COMPONENT ============

export default function PaymentModule({
  product, orderId, amount, customerName, customerEmail, description, onPaymentComplete,
}: PaymentModuleProps) {
  const [method, setMethod] = useState<PaymentMethod>('card');
  const [payments, setPayments] = useState<PaymentRecord[]>([]);

  // Card state
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [cvc, setCvc] = useState('');
  const [cardName, setCardName] = useState(customerName || '');
  const [zip, setZip] = useState('');
  const [cardProcessing, setCardProcessing] = useState(false);
  const [cardSuccess, setCardSuccess] = useState(false);

  // Crypto state
  const [cryptoToken, setCryptoToken] = useState('USDC');
  const [cryptoTimer, setCryptoTimer] = useState(1800);

  // Invoice state
  const [invoiceTerms, setInvoiceTerms] = useState<'net15' | 'net30' | 'net60'>('net30');
  const [invoiceSent, setInvoiceSent] = useState(false);

  // Zelle state
  const [zelleRef, setZelleRef] = useState('');
  const [zelleConfirmed, setZelleConfirmed] = useState(false);

  // Payment link state
  const [linkExpiry, setLinkExpiry] = useState<'24h' | '7d' | '30d'>('7d');
  const [generatedLink, setGeneratedLink] = useState('');
  const [linkCopied, setLinkCopied] = useState(false);

  // Crypto countdown timer
  useEffect(() => {
    if (method !== 'crypto') return;
    const iv = setInterval(() => setCryptoTimer(t => (t > 0 ? t - 1 : 0)), 1000);
    return () => clearInterval(iv);
  }, [method]);

  const addPayment = useCallback((rec: PaymentRecord) => {
    setPayments(prev => [rec, ...prev]);
    onPaymentComplete?.(rec);
  }, [onPaymentComplete]);

  const displayAmount = (amount ?? 0) > 0 ? (amount ?? 0) : 0;
  const cryptoDiscount = displayAmount * 0.9;

  // ---- Card submit ----
  const handleCardPay = () => {
    if (!cardNumber || !expiry || !cvc || !cardName) return;
    setCardProcessing(true);
    setTimeout(() => {
      setCardProcessing(false);
      setCardSuccess(true);
      const rec: PaymentRecord = {
        id: genId(), product, orderId, method: 'card', amount: displayAmount,
        currency: 'USD', status: 'completed', customerName: cardName,
        customerEmail, description, reference: 'Stripe-' + genId(), createdAt: new Date().toISOString(),
      };
      addPayment(rec);
      setTimeout(() => setCardSuccess(false), 3000);
    }, 2200);
  };

  // ---- Zelle confirm ----
  const handleZelleConfirm = () => {
    if (!zelleRef) return;
    setZelleConfirmed(true);
    const rec: PaymentRecord = {
      id: genId(), product, orderId, method: 'zelle', amount: displayAmount,
      currency: 'USD', status: 'pending', customerName, customerEmail,
      description, reference: zelleRef, createdAt: new Date().toISOString(),
    };
    addPayment(rec);
  };

  // ---- Invoice send ----
  const handleInvoiceSend = () => {
    setInvoiceSent(true);
    const daysMap = { net15: 15, net30: 30, net60: 60 };
    const rec: PaymentRecord = {
      id: genId(), product, orderId, method: 'invoice', amount: displayAmount,
      currency: 'USD', status: 'pending', customerName, customerEmail,
      description: `Invoice — ${invoiceTerms.toUpperCase()} — Due ${new Date(Date.now() + daysMap[invoiceTerms] * 86400000).toLocaleDateString()}`,
      reference: 'INV-' + genId(), createdAt: new Date().toISOString(),
    };
    addPayment(rec);
  };

  // ---- Generate link ----
  const handleGenerateLink = () => {
    const link = `https://pay.empirebox.store/${product}/${orderId || 'checkout'}?amt=${displayAmount}&exp=${linkExpiry}`;
    setGeneratedLink(link);
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(generatedLink).catch(() => {});
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 2000);
  };

  // ============ SUB-RENDERS ============

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '10px 12px', borderRadius: 8, border: `1px solid ${BORDER}`,
    fontSize: 14, background: PAGE_BG, outline: 'none', transition: 'border 0.15s',
  };

  const btnGold: React.CSSProperties = {
    padding: '12px 24px', borderRadius: 10, border: 'none', cursor: 'pointer',
    background: GOLD, color: '#fff', fontWeight: 600, fontSize: 14, display: 'flex',
    alignItems: 'center', gap: 8, justifyContent: 'center', transition: 'opacity 0.15s',
  };

  const sectionCard: React.CSSProperties = {
    background: CARD_BG, borderRadius: 12, border: `1px solid ${BORDER}`, padding: 24,
  };

  // ---- Card Form ----
  const renderCardForm = () => (
    <div style={sectionCard}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
        <CreditCard size={18} style={{ color: GOLD }} />
        <span style={{ fontWeight: 600, fontSize: 15 }}>Credit / Debit Card</span>
        <span style={{ marginLeft: 'auto', fontSize: 12, color: MUTED }}>Powered by Stripe</span>
      </div>

      {/* Card Number */}
      <div style={{ marginBottom: 14 }}>
        <label style={{ fontSize: 12, fontWeight: 500, color: MUTED, display: 'block', marginBottom: 4 }}>Card Number</label>
        <input placeholder="4242 4242 4242 4242" value={cardNumber}
          onChange={e => setCardNumber(formatCard(e.target.value))} style={inputStyle} maxLength={19} />
      </div>

      {/* Expiry + CVC */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 12, fontWeight: 500, color: MUTED, display: 'block', marginBottom: 4 }}>Expiry</label>
          <input placeholder="MM/YY" value={expiry}
            onChange={e => setExpiry(formatExpiry(e.target.value))} style={inputStyle} maxLength={5} />
        </div>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 12, fontWeight: 500, color: MUTED, display: 'block', marginBottom: 4 }}>CVC</label>
          <input placeholder="123" value={cvc}
            onChange={e => setCvc(e.target.value.replace(/\D/g, '').slice(0, 4))} style={inputStyle} maxLength={4} />
        </div>
      </div>

      {/* Name + ZIP */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <div style={{ flex: 2 }}>
          <label style={{ fontSize: 12, fontWeight: 500, color: MUTED, display: 'block', marginBottom: 4 }}>Cardholder Name</label>
          <input placeholder="Jane Doe" value={cardName}
            onChange={e => setCardName(e.target.value)} style={inputStyle} />
        </div>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 12, fontWeight: 500, color: MUTED, display: 'block', marginBottom: 4 }}>Billing ZIP</label>
          <input placeholder="20001" value={zip}
            onChange={e => setZip(e.target.value.replace(/\D/g, '').slice(0, 5))} style={inputStyle} maxLength={5} />
        </div>
      </div>

      {/* Pay button */}
      <button onClick={handleCardPay}
        disabled={cardProcessing || cardSuccess || !cardNumber || !expiry || !cvc || !cardName}
        style={{
          ...btnGold, width: '100%',
          opacity: (cardProcessing || !cardNumber || !expiry || !cvc || !cardName) ? 0.6 : 1,
          background: cardSuccess ? '#16a34a' : GOLD,
        }}>
        {cardProcessing ? <><Loader2 size={16} className="animate-spin" /> Processing...</> :
         cardSuccess ? <><Check size={16} /> Payment Successful!</> :
         <>Pay ${displayAmount.toFixed(2)}</>}
      </button>
    </div>
  );

  // ---- PayPal ----
  const renderPayPal = () => (
    <div style={sectionCard}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
        <DollarSign size={18} style={{ color: '#003087' }} />
        <span style={{ fontWeight: 600, fontSize: 15 }}>PayPal</span>
      </div>

      <button style={{ ...btnGold, width: '100%', background: '#003087', marginBottom: 16 }}>
        Pay with PayPal &mdash; ${displayAmount.toFixed(2)}
      </button>

      <div style={{ background: '#f0f4ff', borderRadius: 10, padding: 16, border: '1px solid #c7d2fe' }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: '#4338ca', marginBottom: 8 }}>
          PayPal integration coming soon. Use the payment link below:
        </div>
        <div style={{ fontSize: 13, color: '#374151', fontFamily: 'monospace', background: '#fff', padding: '8px 12px', borderRadius: 6, border: `1px solid ${BORDER}`, wordBreak: 'break-all' }}>
          https://paypal.me/empirebox/${displayAmount.toFixed(2)}
        </div>
      </div>

      {/* QR placeholder */}
      <div style={{ marginTop: 16, display: 'flex', justifyContent: 'center' }}>
        <div style={{
          width: 140, height: 140, borderRadius: 10, border: `2px dashed ${BORDER}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 6, color: MUTED,
        }}>
          <QrCode size={28} />
          <span style={{ fontSize: 11 }}>PayPal QR Code</span>
        </div>
      </div>
    </div>
  );

  // ---- Crypto ----
  const renderCrypto = () => {
    const tokenAmt = cryptoDiscount * (CRYPTO_RATES[cryptoToken] || 1);
    const mins = Math.floor(cryptoTimer / 60);
    const secs = cryptoTimer % 60;

    return (
      <div style={sectionCard}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <Wallet size={18} style={{ color: GOLD }} />
          <span style={{ fontWeight: 600, fontSize: 15 }}>Crypto Payment</span>
        </div>

        {/* Discount badge */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6, background: '#dcfce7',
          color: '#16a34a', fontSize: 12, fontWeight: 600, padding: '4px 10px', borderRadius: 20, marginBottom: 16,
        }}>
          <CheckCircle size={13} /> 10% crypto discount applied &mdash; ${cryptoDiscount.toFixed(2)}
        </div>

        {/* Token selector */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 12, fontWeight: 500, color: MUTED, display: 'block', marginBottom: 6 }}>Select Token</label>
          <div style={{ display: 'flex', gap: 8 }}>
            {CRYPTO_TOKENS.map(t => (
              <button key={t} onClick={() => setCryptoToken(t)} style={{
                padding: '8px 16px', borderRadius: 8, border: `1.5px solid ${cryptoToken === t ? GOLD : BORDER}`,
                background: cryptoToken === t ? GOLD_BG : '#fff', fontWeight: cryptoToken === t ? 600 : 400,
                fontSize: 13, cursor: 'pointer', color: cryptoToken === t ? GOLD : '#374151', transition: 'all 0.15s',
              }}>
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Wallet address */}
        <div style={{ marginBottom: 14 }}>
          <label style={{ fontSize: 12, fontWeight: 500, color: MUTED, display: 'block', marginBottom: 4 }}>Send to Wallet Address</label>
          <div style={{ fontFamily: 'monospace', fontSize: 14, background: PAGE_BG, padding: '10px 12px', borderRadius: 8, border: `1px solid ${BORDER}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>{MOCK_WALLETS[cryptoToken]}</span>
            <button onClick={() => { navigator.clipboard.writeText(MOCK_WALLETS[cryptoToken] || '').catch(() => {}); }}
              style={{ border: 'none', background: 'none', cursor: 'pointer', color: MUTED }}><Copy size={14} /></button>
          </div>
        </div>

        {/* Amount */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 12, fontWeight: 500, color: MUTED, display: 'block', marginBottom: 4 }}>Amount</label>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#111' }}>
            {tokenAmt.toFixed(cryptoToken === 'EMPIRE' ? 0 : 6)} {cryptoToken}
          </div>
          <div style={{ fontSize: 12, color: MUTED }}>${cryptoDiscount.toFixed(2)} USD (10% off)</div>
        </div>

        {/* QR + Timer row */}
        <div style={{ display: 'flex', gap: 20, alignItems: 'center', marginBottom: 16 }}>
          <div style={{
            width: 120, height: 120, borderRadius: 10, border: `2px dashed ${BORDER}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 4, color: MUTED, flexShrink: 0,
          }}>
            <QrCode size={24} />
            <span style={{ fontSize: 10 }}>{cryptoToken} QR</span>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <Timer size={14} style={{ color: cryptoTimer < 300 ? '#dc2626' : GOLD }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: cryptoTimer < 300 ? '#dc2626' : '#374151' }}>
                Payment expires in {String(mins).padStart(2, '0')}:{String(secs).padStart(2, '0')}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Loader2 size={14} className="animate-spin" style={{ color: GOLD }} />
              <span style={{ fontSize: 13, color: MUTED }}>Waiting for payment...</span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ---- Invoice ----
  const renderInvoice = () => {
    const daysMap = { net15: 15, net30: 30, net60: 60 };
    const dueDate = new Date(Date.now() + daysMap[invoiceTerms] * 86400000);

    return (
      <div style={sectionCard}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
          <FileText size={18} style={{ color: GOLD }} />
          <span style={{ fontWeight: 600, fontSize: 15 }}>Invoice</span>
        </div>

        {/* Invoice preview */}
        <div style={{ background: PAGE_BG, borderRadius: 10, border: `1px solid ${BORDER}`, padding: 20, marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 11, color: MUTED, textTransform: 'uppercase', letterSpacing: 1 }}>Invoice From</div>
              <div style={{ fontWeight: 600, fontSize: 14 }}>EmpireBox LLC</div>
              <div style={{ fontSize: 12, color: MUTED }}>Washington, DC</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 11, color: MUTED, textTransform: 'uppercase', letterSpacing: 1 }}>Invoice To</div>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{customerName || 'Customer'}</div>
              <div style={{ fontSize: 12, color: MUTED }}>{customerEmail || 'email@example.com'}</div>
            </div>
          </div>
          <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: 12, display: 'flex', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 12, color: MUTED }}>Product</div>
              <div style={{ fontWeight: 500, fontSize: 14 }}>{product.toUpperCase()} &mdash; {description || 'Service'}</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 12, color: MUTED }}>Amount Due</div>
              <div style={{ fontWeight: 700, fontSize: 18, color: GOLD }}>${displayAmount.toFixed(2)}</div>
            </div>
          </div>
          <div style={{ borderTop: `1px solid ${BORDER}`, marginTop: 12, paddingTop: 12, display: 'flex', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 12, color: MUTED }}>Order</div>
              <div style={{ fontSize: 13 }}>{orderId || 'N/A'}</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 12, color: MUTED }}>Due Date</div>
              <div style={{ fontSize: 13, fontWeight: 500 }}>{dueDate.toLocaleDateString()}</div>
            </div>
          </div>
        </div>

        {/* Terms selector */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 12, fontWeight: 500, color: MUTED, display: 'block', marginBottom: 6 }}>Payment Terms</label>
          <div style={{ display: 'flex', gap: 8 }}>
            {(['net15', 'net30', 'net60'] as const).map(t => (
              <button key={t} onClick={() => setInvoiceTerms(t)} style={{
                padding: '8px 16px', borderRadius: 8, border: `1.5px solid ${invoiceTerms === t ? GOLD : BORDER}`,
                background: invoiceTerms === t ? GOLD_BG : '#fff', fontWeight: invoiceTerms === t ? 600 : 400,
                fontSize: 13, cursor: 'pointer', color: invoiceTerms === t ? GOLD : '#374151',
              }}>
                {t === 'net15' ? 'Net 15' : t === 'net30' ? 'Net 30' : 'Net 60'}
              </button>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={handleInvoiceSend} disabled={invoiceSent}
            style={{ ...btnGold, flex: 1, opacity: invoiceSent ? 0.6 : 1, background: invoiceSent ? '#16a34a' : GOLD }}>
            {invoiceSent ? <><Check size={15} /> Invoice Sent</> : <><Mail size={15} /> Send Invoice to Email</>}
          </button>
          <button style={{ ...btnGold, flex: 1, background: '#374151' }}>
            <Download size={15} /> Download Invoice PDF
          </button>
        </div>
      </div>
    );
  };

  // ---- Zelle / Wire ----
  const renderZelle = () => (
    <div style={sectionCard}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
        <Send size={18} style={{ color: GOLD }} />
        <span style={{ fontWeight: 600, fontSize: 15 }}>Zelle / Wire Transfer</span>
      </div>

      {/* Business details */}
      <div style={{ background: PAGE_BG, borderRadius: 10, border: `1px solid ${BORDER}`, padding: 20, marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: MUTED, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
          Business Account Details
        </div>
        {[
          ['Bank', 'Chase Business'],
          ['Account Name', 'EmpireBox LLC'],
          ['Zelle', 'pay@empirebox.store'],
          ['Wire Routing', 'XXXXXXXX'],
          ['Amount', `$${displayAmount.toFixed(2)}`],
        ].map(([label, value]) => (
          <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: `1px solid ${BORDER}` }}>
            <span style={{ fontSize: 13, color: MUTED }}>{label}</span>
            <span style={{ fontSize: 13, fontWeight: 500, fontFamily: label === 'Wire Routing' ? 'monospace' : 'inherit' }}>{value}</span>
          </div>
        ))}
      </div>

      {/* Reference input */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 12, fontWeight: 500, color: MUTED, display: 'block', marginBottom: 4 }}>
          Reference / Confirmation Number
        </label>
        <input placeholder="Enter your Zelle or wire reference number" value={zelleRef}
          onChange={e => setZelleRef(e.target.value)} style={inputStyle} />
      </div>

      <button onClick={handleZelleConfirm} disabled={zelleConfirmed || !zelleRef}
        style={{ ...btnGold, width: '100%', opacity: (zelleConfirmed || !zelleRef) ? 0.6 : 1, background: zelleConfirmed ? '#16a34a' : GOLD }}>
        {zelleConfirmed ? <><Check size={15} /> Payment Confirmation Sent</> : <><CheckCircle size={15} /> I&apos;ve Sent the Payment</>}
      </button>
    </div>
  );

  // ---- Payment History ----
  const renderHistory = () => (
    <div style={{ ...sectionCard, marginTop: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <Clock size={18} style={{ color: GOLD }} />
        <span style={{ fontWeight: 600, fontSize: 15 }}>Payment History</span>
        {payments.length > 0 && (
          <span style={{ marginLeft: 'auto', fontSize: 12, color: MUTED }}>{payments.length} record{payments.length > 1 ? 's' : ''}</span>
        )}
      </div>

      {payments.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '20px 0', color: MUTED, fontSize: 13 }}>
          No payments recorded for this order yet.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {payments.map(p => {
            const sc = STATUS_COLORS[p.status] || STATUS_COLORS.pending;
            return (
              <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', borderRadius: 8, border: `1px solid ${BORDER}`, background: PAGE_BG }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{p.id}</div>
                  <div style={{ fontSize: 12, color: MUTED }}>
                    {p.method.toUpperCase()} &bull; {new Date(p.createdAt).toLocaleString()}
                  </div>
                </div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>${p.amount.toFixed(2)}</div>
                <span style={{ padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600, background: sc.bg, color: sc.color }}>
                  {sc.label}
                </span>
                <button style={{ border: 'none', background: 'none', cursor: 'pointer', color: MUTED }} title="Download receipt">
                  <Download size={14} />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );

  // ---- Payment Link Generator ----
  const renderLinkGenerator = () => (
    <div style={{ ...sectionCard, marginTop: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <Link2 size={18} style={{ color: GOLD }} />
        <span style={{ fontWeight: 600, fontSize: 15 }}>Payment Link Generator</span>
      </div>

      <div style={{ display: 'flex', gap: 10, alignItems: 'end', marginBottom: 14 }}>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 12, fontWeight: 500, color: MUTED, display: 'block', marginBottom: 4 }}>Link Expiry</label>
          <div style={{ display: 'flex', gap: 6 }}>
            {([['24h', '24 Hours'], ['7d', '7 Days'], ['30d', '30 Days']] as const).map(([val, label]) => (
              <button key={val} onClick={() => setLinkExpiry(val as typeof linkExpiry)} style={{
                padding: '6px 12px', borderRadius: 6, border: `1.5px solid ${linkExpiry === val ? GOLD : BORDER}`,
                background: linkExpiry === val ? GOLD_BG : '#fff', fontSize: 12, cursor: 'pointer',
                fontWeight: linkExpiry === val ? 600 : 400, color: linkExpiry === val ? GOLD : '#374151',
              }}>
                {label}
              </button>
            ))}
          </div>
        </div>
        <button onClick={handleGenerateLink} style={{ ...btnGold, whiteSpace: 'nowrap' }}>
          <Link2 size={14} /> Generate Link
        </button>
      </div>

      {generatedLink && (
        <div style={{ background: PAGE_BG, borderRadius: 8, border: `1px solid ${BORDER}`, padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <input value={generatedLink} readOnly style={{ ...inputStyle, flex: 1, background: 'transparent', border: 'none', fontSize: 12, fontFamily: 'monospace' }} />
          <button onClick={handleCopyLink} style={{ border: 'none', background: linkCopied ? '#dcfce7' : GOLD_BG, cursor: 'pointer', borderRadius: 6, padding: '6px 10px', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: linkCopied ? '#16a34a' : GOLD, fontWeight: 500 }}>
            {linkCopied ? <><Check size={12} /> Copied</> : <><Copy size={12} /> Copy</>}
          </button>
          <button style={{ border: 'none', background: GOLD_BG, cursor: 'pointer', borderRadius: 6, padding: '6px 10px', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: GOLD, fontWeight: 500 }}>
            <Mail size={12} /> Email
          </button>
        </div>
      )}
    </div>
  );

  // ============ MAIN RENDER ============
  return (
    <div style={{ maxWidth: 680, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: '#111' }}>Payment</h2>
        {displayAmount > 0 && (
          <div style={{ fontSize: 13, color: MUTED, marginTop: 2 }}>
            {description || product.toUpperCase()} {orderId && <>&bull; Order {orderId}</>} &bull; <span style={{ fontWeight: 600, color: GOLD }}>${displayAmount.toFixed(2)}</span>
          </div>
        )}
      </div>

      {/* Method selector tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, overflowX: 'auto', paddingBottom: 4 }}>
        {PAYMENT_METHODS.map(pm => {
          const Icon = pm.icon;
          const active = method === pm.id;
          return (
            <button key={pm.id} onClick={() => setMethod(pm.id)} style={{
              flex: '1 1 0', minWidth: 100, padding: '12px 10px', borderRadius: 10,
              border: `1.5px solid ${active ? GOLD : BORDER}`, background: active ? GOLD_BG : CARD_BG,
              cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
              transition: 'all 0.15s',
            }}>
              <Icon size={18} style={{ color: active ? GOLD : MUTED }} />
              <span style={{ fontSize: 12, fontWeight: active ? 600 : 500, color: active ? GOLD : '#374151' }}>{pm.label}</span>
              <span style={{ fontSize: 10, color: active ? GOLD : MUTED }}>{pm.sub}</span>
            </button>
          );
        })}
      </div>

      {/* Active method */}
      {method === 'card' && renderCardForm()}
      {method === 'paypal' && renderPayPal()}
      {method === 'crypto' && renderCrypto()}
      {method === 'invoice' && renderInvoice()}
      {method === 'zelle' && renderZelle()}

      {/* Payment History */}
      {renderHistory()}

      {/* Payment Link Generator */}
      {renderLinkGenerator()}
    </div>
  );
}
