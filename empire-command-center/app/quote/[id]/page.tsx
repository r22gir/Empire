'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { CheckCircle, Clock, FileText, Phone, Mail, MapPin, AlertCircle } from 'lucide-react';

const API = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? 'https://api.empirebox.store/api/v1'
  : 'http://localhost:8000/api/v1';

interface LineItem {
  description: string;
  quantity: number;
  unit: string;
  rate: number;
  amount: number;
  category: string;
}

interface Quote {
  id: string;
  quote_number: string;
  status: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  customer_address: string;
  project_name: string;
  project_description: string;
  business_name: string | null;
  line_items: LineItem[];
  subtotal: number;
  tax_rate: number;
  tax_amount: number;
  discount_amount: number;
  total: number;
  deposit: number | null;
  terms: string;
  valid_days: number;
  notes: string | null;
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
  sent_at: string | null;
}

function formatCurrency(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  });
}

function isExpired(quote: Quote) {
  if (!quote.expires_at) return false;
  return new Date(quote.expires_at) < new Date();
}

export default function QuoteAcceptPage() {
  const params = useParams();
  const quoteId = params.id as string;

  const [quote, setQuote] = useState<Quote | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [accepting, setAccepting] = useState(false);
  const [accepted, setAccepted] = useState(false);

  useEffect(() => {
    fetch(`${API}/quotes/${quoteId}`)
      .then(r => {
        if (!r.ok) throw new Error('Quote not found');
        return r.json();
      })
      .then(data => {
        setQuote(data);
        if (data.status === 'accepted') setAccepted(true);
      })
      .catch(() => setError('Quote not found. Please check the link and try again.'))
      .finally(() => setLoading(false));
  }, [quoteId]);

  async function handleAccept() {
    if (!quote || accepting) return;
    setAccepting(true);
    try {
      const res = await fetch(`${API}/quotes/${quoteId}/accept`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to accept');
      setAccepted(true);
      setQuote(prev => prev ? { ...prev, status: 'accepted', accepted_at: new Date().toISOString() } : prev);
    } catch {
      setError('Failed to accept quote. Please try again or contact us directly.');
    } finally {
      setAccepting(false);
    }
  }

  const businessName = quote?.business_name || 'Empire Workroom';
  const depositAmount = quote?.deposit ?? (quote ? quote.total * 0.5 : 0);
  const expired = quote ? isExpired(quote) : false;

  if (loading) {
    return (
      <div style={styles.page} data-quote-page>
        <div style={styles.loadingContainer}>
          <div style={styles.spinner} />
          <p style={styles.loadingText}>Loading your quote...</p>
        </div>
      </div>
    );
  }

  if (error && !quote) {
    return (
      <div style={styles.page} data-quote-page>
        <div style={styles.errorContainer}>
          <AlertCircle size={48} color="#dc2626" />
          <h1 style={styles.errorTitle}>Quote Not Found</h1>
          <p style={styles.errorText}>{error}</p>
        </div>
      </div>
    );
  }

  if (!quote) return null;

  return (
    <div style={styles.page} data-quote-page>
      <div style={styles.container}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.headerLeft}>
            <h1 style={styles.businessName}>{businessName}</h1>
            <p style={styles.quoteNumber}>{quote.quote_number}</p>
          </div>
          <div style={styles.headerRight}>
            <StatusBadge status={accepted ? 'accepted' : expired ? 'expired' : quote.status} />
          </div>
        </div>

        {/* Accepted Banner */}
        {accepted && (
          <div style={styles.acceptedBanner}>
            <CheckCircle size={24} color="#16a34a" />
            <div>
              <strong>Quote Accepted</strong>
              <p style={{ margin: '4px 0 0', fontSize: 14, color: '#166534' }}>
                Thank you! We'll be in touch shortly to schedule your project.
                {quote.accepted_at && ` Accepted on ${formatDate(quote.accepted_at)}.`}
              </p>
            </div>
          </div>
        )}

        {/* Expired Banner */}
        {expired && !accepted && (
          <div style={styles.expiredBanner}>
            <Clock size={24} color="#b45309" />
            <div>
              <strong>Quote Expired</strong>
              <p style={{ margin: '4px 0 0', fontSize: 14, color: '#92400e' }}>
                This quote expired on {formatDate(quote.expires_at)}. Please contact us for an updated quote.
              </p>
            </div>
          </div>
        )}

        {/* Customer & Project Info */}
        <div style={styles.infoGrid} className="info-grid">
          <div style={styles.infoCard}>
            <h3 style={styles.infoTitle}>Prepared For</h3>
            <p style={styles.customerName}>{quote.customer_name}</p>
            {quote.customer_email && (
              <p style={styles.infoLine}><Mail size={14} /> {quote.customer_email}</p>
            )}
            {quote.customer_phone && (
              <p style={styles.infoLine}><Phone size={14} /> {quote.customer_phone}</p>
            )}
            {quote.customer_address && (
              <p style={styles.infoLine}><MapPin size={14} /> {quote.customer_address}</p>
            )}
          </div>
          <div style={styles.infoCard}>
            <h3 style={styles.infoTitle}>Project Details</h3>
            <p style={styles.customerName}>{quote.project_name}</p>
            {quote.project_description && (
              <p style={styles.projectDesc}>{quote.project_description}</p>
            )}
            <p style={styles.infoLine}>
              <FileText size={14} /> Created {formatDate(quote.created_at)}
            </p>
            {quote.expires_at && (
              <p style={styles.infoLine}>
                <Clock size={14} /> Valid until {formatDate(quote.expires_at)}
              </p>
            )}
          </div>
        </div>

        {/* Line Items */}
        <div style={styles.tableContainer}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={{ ...styles.th, textAlign: 'left' }}>Description</th>
                <th style={styles.th}>Qty</th>
                <th style={styles.th}>Rate</th>
                <th style={{ ...styles.th, textAlign: 'right' }}>Amount</th>
              </tr>
            </thead>
            <tbody>
              {quote.line_items?.map((item, i) => (
                <tr key={i} style={i % 2 === 0 ? styles.rowEven : styles.rowOdd}>
                  <td style={{ ...styles.td, textAlign: 'left' }}>
                    <span style={styles.itemDesc}>{item.description}</span>
                    <span style={styles.itemCategory}>{item.category}</span>
                  </td>
                  <td style={styles.td}>{item.quantity} {item.unit}</td>
                  <td style={styles.td}>{formatCurrency(item.rate)}</td>
                  <td style={{ ...styles.td, textAlign: 'right', fontWeight: 500 }}>
                    {formatCurrency(item.amount)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Totals */}
        <div style={styles.totalsContainer}>
          <div style={styles.totalsRow}>
            <span>Subtotal</span>
            <span>{formatCurrency(quote.subtotal)}</span>
          </div>
          {quote.discount_amount > 0 && (
            <div style={{ ...styles.totalsRow, color: '#16a34a' }}>
              <span>Discount</span>
              <span>-{formatCurrency(quote.discount_amount)}</span>
            </div>
          )}
          {quote.tax_amount > 0 && (
            <div style={styles.totalsRow}>
              <span>Tax ({(quote.tax_rate * 100).toFixed(1)}%)</span>
              <span>{formatCurrency(quote.tax_amount)}</span>
            </div>
          )}
          <div style={styles.totalRow}>
            <span>Total</span>
            <span>{formatCurrency(quote.total)}</span>
          </div>
          <div style={styles.depositRow}>
            <span>Deposit Required (50%)</span>
            <span>{formatCurrency(depositAmount)}</span>
          </div>
        </div>

        {/* Terms */}
        {quote.terms && (
          <div style={styles.termsContainer}>
            <h3 style={styles.termsTitle}>Terms & Conditions</h3>
            <p style={styles.termsText}>{quote.terms}</p>
          </div>
        )}

        {/* Notes */}
        {quote.notes && (
          <div style={styles.notesContainer}>
            <h3 style={styles.termsTitle}>Notes</h3>
            <p style={styles.termsText}>{quote.notes}</p>
          </div>
        )}

        {/* Accept Button */}
        {!accepted && !expired && quote.status !== 'accepted' && (
          <div style={styles.actionContainer}>
            <button
              onClick={handleAccept}
              disabled={accepting}
              style={{
                ...styles.acceptButton,
                opacity: accepting ? 0.7 : 1,
                cursor: accepting ? 'not-allowed' : 'pointer',
              }}
            >
              {accepting ? 'Accepting...' : 'Accept Quote & Proceed'}
            </button>
            <p style={styles.acceptNote}>
              By accepting, you agree to the terms above. A 50% deposit of{' '}
              <strong>{formatCurrency(depositAmount)}</strong> is required to begin work.
            </p>
          </div>
        )}

        {/* Error message */}
        {error && quote && (
          <div style={styles.inlineError}>
            <AlertCircle size={16} color="#dc2626" />
            <span>{error}</span>
          </div>
        )}

        {/* Footer */}
        <div style={styles.footer}>
          <p>{businessName} &middot; Powered by Empire</p>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, { bg: string; text: string; border: string }> = {
    draft:    { bg: '#f3f4f6', text: '#374151', border: '#d1d5db' },
    sent:     { bg: '#fdf8eb', text: '#92400e', border: '#d4b84a' },
    accepted: { bg: '#dcfce7', text: '#166534', border: '#86efac' },
    expired:  { bg: '#fef3c7', text: '#92400e', border: '#fcd34d' },
    declined: { bg: '#fef2f2', text: '#991b1b', border: '#fca5a5' },
  };
  const c = colors[status] || colors.draft;

  return (
    <span style={{
      padding: '6px 14px',
      borderRadius: 8,
      fontSize: 13,
      fontWeight: 600,
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
      backgroundColor: c.bg,
      color: c.text,
      border: `1px solid ${c.border}`,
    }}>
      {status}
    </span>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    backgroundColor: '#f5f2ed',
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
    padding: '24px 16px',
  },
  container: {
    maxWidth: 720,
    margin: '0 auto',
    backgroundColor: '#fff',
    borderRadius: 16,
    border: '1px solid #ece8e0',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: '32px 32px 24px',
    borderBottom: '1px solid #ece8e0',
  },
  headerLeft: {},
  headerRight: {},
  businessName: {
    fontSize: 24,
    fontWeight: 700,
    color: '#1a1a1a',
    margin: 0,
  },
  quoteNumber: {
    fontSize: 14,
    color: '#777',
    marginTop: 4,
  },
  acceptedBanner: {
    display: 'flex',
    gap: 12,
    alignItems: 'flex-start',
    padding: '16px 32px',
    backgroundColor: '#dcfce7',
    borderBottom: '1px solid #86efac',
  },
  expiredBanner: {
    display: 'flex',
    gap: 12,
    alignItems: 'flex-start',
    padding: '16px 32px',
    backgroundColor: '#fef3c7',
    borderBottom: '1px solid #fcd34d',
  },
  infoGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 0,
  },
  infoCard: {
    padding: '24px 32px',
    borderBottom: '1px solid #ece8e0',
  },
  infoTitle: {
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    color: '#999',
    margin: '0 0 8px',
  },
  customerName: {
    fontSize: 16,
    fontWeight: 600,
    color: '#1a1a1a',
    margin: '0 0 8px',
  },
  infoLine: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 13,
    color: '#555',
    margin: '4px 0',
  },
  projectDesc: {
    fontSize: 13,
    color: '#555',
    margin: '0 0 8px',
    lineHeight: 1.5,
  },
  tableContainer: {
    overflowX: 'auto' as const,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
  },
  th: {
    padding: '12px 32px',
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    color: '#999',
    borderBottom: '1px solid #ece8e0',
    textAlign: 'center' as const,
  },
  td: {
    padding: '14px 32px',
    fontSize: 14,
    color: '#1a1a1a',
    textAlign: 'center' as const,
    verticalAlign: 'top' as const,
  },
  rowEven: {
    backgroundColor: '#fff',
  },
  rowOdd: {
    backgroundColor: '#faf9f7',
  },
  itemDesc: {
    display: 'block',
    fontWeight: 500,
  },
  itemCategory: {
    display: 'block',
    fontSize: 11,
    color: '#999',
    marginTop: 2,
    textTransform: 'capitalize' as const,
  },
  totalsContainer: {
    padding: '20px 32px',
    borderTop: '1px solid #ece8e0',
  },
  totalsRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '6px 0',
    fontSize: 14,
    color: '#555',
  },
  totalRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '12px 0 6px',
    fontSize: 20,
    fontWeight: 700,
    color: '#1a1a1a',
    borderTop: '2px solid #1a1a1a',
    marginTop: 8,
  },
  depositRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '8px 0',
    fontSize: 14,
    fontWeight: 600,
    color: '#b8960c',
  },
  termsContainer: {
    padding: '20px 32px',
    borderTop: '1px solid #ece8e0',
  },
  notesContainer: {
    padding: '20px 32px',
    borderTop: '1px solid #ece8e0',
  },
  termsTitle: {
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    color: '#999',
    margin: '0 0 8px',
  },
  termsText: {
    fontSize: 13,
    color: '#555',
    lineHeight: 1.6,
    margin: 0,
  },
  actionContainer: {
    padding: '24px 32px 32px',
    textAlign: 'center' as const,
    borderTop: '1px solid #ece8e0',
  },
  acceptButton: {
    display: 'inline-block',
    padding: '14px 48px',
    fontSize: 16,
    fontWeight: 600,
    color: '#fff',
    backgroundColor: '#b8960c',
    border: 'none',
    borderRadius: 12,
    transition: 'all 0.2s',
  },
  acceptNote: {
    fontSize: 12,
    color: '#999',
    marginTop: 12,
    lineHeight: 1.5,
  },
  inlineError: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '12px 32px',
    fontSize: 13,
    color: '#dc2626',
    backgroundColor: '#fef2f2',
    borderTop: '1px solid #fca5a5',
  },
  footer: {
    padding: '20px 32px',
    textAlign: 'center' as const,
    fontSize: 12,
    color: '#999',
    borderTop: '1px solid #ece8e0',
  },
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '60vh',
  },
  spinner: {
    width: 32,
    height: 32,
    border: '3px solid #ece8e0',
    borderTopColor: '#b8960c',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 14,
    color: '#777',
  },
  errorContainer: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '60vh',
    textAlign: 'center' as const,
  },
  errorTitle: {
    fontSize: 24,
    fontWeight: 700,
    color: '#1a1a1a',
    marginTop: 16,
  },
  errorText: {
    fontSize: 14,
    color: '#555',
    marginTop: 8,
  },
};
