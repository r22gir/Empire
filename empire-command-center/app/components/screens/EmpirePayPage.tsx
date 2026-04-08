'use client';
import React, { useState, useEffect, useCallback } from 'react';
import {
  Wallet, ArrowUpDown, Link2, Coins, Settings, LayoutDashboard,
  TrendingUp, TrendingDown, ArrowUpRight, ArrowDownLeft, Copy,
  CheckCircle, Clock, XCircle, Plus, QrCode, Trash2, ToggleLeft,
  ToggleRight, RefreshCw, ExternalLink, Shield, Zap, Eye, BookOpen, CreditCard,
  Loader2, AlertTriangle, Inbox
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';

import { API } from '../../lib/api';

// ============ NAV SECTIONS ============

const NAV_SECTIONS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'wallets', label: 'Wallets', icon: Wallet },
  { id: 'transactions', label: 'Transactions', icon: ArrowUpDown },
  { id: 'payment-links', label: 'Payment Links', icon: Link2 },
  { id: 'empire-token', label: 'EMPIRE Token', icon: Coins },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'payments', label: 'Payments', icon: CreditCard },
  { id: 'docs', label: 'Docs', icon: BookOpen },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

// ============ TYPES ============

interface ChainInfo {
  id: string;
  name: string;
  chain: string;
  token: string;
}

interface Invoice {
  id: string;
  type?: string;
  amount: number;
  token?: string;
  currency?: string;
  from?: string;
  to?: string;
  status: string;
  created_at?: string;
  timestamp?: string;
  total?: number;
  description?: string;
}

// ============ STATIC INFO ============

const EMPIRE_TOKEN_INFO = {
  name: 'EMPIRE',
  symbol: 'EMPIRE',
  chain: 'Ethereum (ERC-20)',
  contractAddress: 'TBD — Token not yet deployed',
  totalSupply: 100000000,
  circulatingSupply: 0,
  holders: 0,
  price: 0,
  change24h: 0,
  distribution: [
    { label: 'Treasury', pct: 40, amount: 40000000, color: '#16a34a' },
    { label: 'Team & Founders', pct: 20, amount: 20000000, color: '#2563eb' },
    { label: 'Community Rewards', pct: 15, amount: 15000000, color: '#7c3aed' },
    { label: 'Liquidity Pool', pct: 10, amount: 10000000, color: '#f59e0b' },
    { label: 'Ecosystem Fund', pct: 8.5, amount: 8500000, color: '#ec4899' },
    { label: 'Circulating', pct: 6.5, amount: 6500000, color: '#06b6d4' },
  ],
};

const CHAIN_COLORS: Record<string, string> = {
  Ethereum: '#627eea',
  Solana: '#9945ff',
  Bitcoin: '#f7931a',
  ethereum: '#627eea',
  solana: '#9945ff',
  bitcoin: '#f7931a',
  ETH: '#627eea',
  SOL: '#9945ff',
  BTC: '#f7931a',
};

const TOKEN_COLORS: Record<string, string> = {
  ETH: '#627eea',
  SOL: '#9945ff',
  BTC: '#f7931a',
  USDC: '#2775ca',
  EMPIRE: '#16a34a',
};

const STATUS_MAP: Record<string, { bg: string; color: string; icon: React.ElementType }> = {
  confirmed: { bg: '#dcfce7', color: '#16a34a', icon: CheckCircle },
  paid: { bg: '#dcfce7', color: '#16a34a', icon: CheckCircle },
  completed: { bg: '#dcfce7', color: '#16a34a', icon: CheckCircle },
  pending: { bg: '#fef9c3', color: '#a16207', icon: Clock },
  unpaid: { bg: '#fef9c3', color: '#a16207', icon: Clock },
  failed: { bg: '#fee2e2', color: '#dc2626', icon: XCircle },
  cancelled: { bg: '#fee2e2', color: '#dc2626', icon: XCircle },
};

const ACCENT = '#16a34a';
const ACCENT_BG = '#dcfce7';
const ACCENT_BORDER = '#bbf7d0';

// ============ SHARED UI COMPONENTS ============

function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center" style={{ padding: 60, color: '#999' }}>
      <Loader2 size={28} className="animate-spin" style={{ marginBottom: 10, color: ACCENT }} />
      <span style={{ fontSize: 13 }}>{label || 'Loading...'}</span>
    </div>
  );
}

function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-center gap-3" style={{ padding: '14px 18px', margin: '20px 24px', borderRadius: 12, background: '#fee2e2', border: '1.5px solid #fca5a5' }}>
      <AlertTriangle size={18} style={{ color: '#dc2626', flexShrink: 0 }} />
      <span style={{ fontSize: 13, color: '#dc2626', flex: 1 }}>{message}</span>
      {onRetry && (
        <button onClick={onRetry} className="cursor-pointer flex items-center gap-1" style={{ padding: '4px 12px', borderRadius: 8, background: '#fff', border: '1px solid #fca5a5', fontSize: 12, fontWeight: 600, color: '#dc2626' }}>
          <RefreshCw size={12} /> Retry
        </button>
      )}
    </div>
  );
}

function EmptyState({ icon, title, subtitle }: { icon: React.ReactNode; title: string; subtitle: string }) {
  return (
    <div className="flex flex-col items-center justify-center" style={{ padding: 60, color: '#999' }}>
      <div style={{ marginBottom: 12, color: '#ccc' }}>{icon}</div>
      <div style={{ fontSize: 15, fontWeight: 600, color: '#666', marginBottom: 4 }}>{title}</div>
      <div style={{ fontSize: 12, color: '#999' }}>{subtitle}</div>
    </div>
  );
}

// ============ KPI CARD ============

function KPI({ icon, iconBg, iconColor, label, value, sub }: {
  icon: React.ReactNode; iconBg: string; iconColor: string; label: string; value: string; sub: string;
}) {
  return (
    <div className="empire-card" style={{ padding: '16px 18px' }}>
      <div className="flex items-center gap-3 mb-2">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: iconBg, color: iconColor }}>{icon}</div>
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: '#999' }}>{label}</span>
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>{value}</div>
      <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>{sub}</div>
    </div>
  );
}

// ============ TRUNCATE ADDRESS ============

function truncAddr(addr: string) {
  if (addr.length <= 14) return addr;
  return addr.slice(0, 6) + '...' + addr.slice(-4);
}

// ============ CUSTOM HOOKS ============

function useChains() {
  const [chains, setChains] = useState<ChainInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchChains = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/crypto-payments/chains`);
      if (!res.ok) throw new Error(`Failed to load chains (${res.status})`);
      const data = await res.json();
      const items = Array.isArray(data) ? data : (data.chains || data.data || []);
      setChains(items.map((c: Record<string, string>, i: number) => ({
        id: c.id || c.chain_id || `chain-${i}`,
        name: c.name || c.chain || 'Unknown',
        chain: c.chain || c.network || c.name || 'Unknown',
        token: c.token || c.symbol || c.native_token || c.name || '',
      })));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chains');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchChains(); }, [fetchChains]);
  return { chains, loading, error, refetch: fetchChains };
}

function useInvoices() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInvoices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/finance/invoices`);
      if (!res.ok) throw new Error(`Failed to load invoices (${res.status})`);
      const data = await res.json();
      const items = Array.isArray(data) ? data : (data.invoices || data.data || data.items || []);
      setInvoices(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load invoices');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]);
  return { invoices, loading, error, refetch: fetchInvoices };
}

// ============ DASHBOARD SECTION ============

function DashboardSection() {
  const { chains, loading: chainsLoading, error: chainsError, refetch: refetchChains } = useChains();
  const { invoices, loading: invoicesLoading, error: invoicesError, refetch: refetchInvoices } = useInvoices();

  const loading = chainsLoading || invoicesLoading;
  const error = chainsError || invoicesError;

  const recentTxns = invoices.slice(0, 5);
  const totalPaymentUsd = invoices.reduce((s, t) => s + (t.total || t.amount || 0), 0);

  if (loading) return <Spinner label="Loading dashboard..." />;

  return (
    <div style={{ padding: 24 }}>
      <div style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>EmpirePay Dashboard</div>
      <div style={{ fontSize: 12, color: '#999', marginBottom: 20 }}>Crypto payments, wallets, and EMPIRE token management</div>

      {error && <ErrorBanner message={error} onRetry={() => { refetchChains(); refetchInvoices(); }} />}

      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPI icon={<Wallet size={16} />} iconBg={ACCENT_BG} iconColor={ACCENT} label="Supported Chains" value={String(chains.length)} sub={`${chains.length} chain${chains.length !== 1 ? 's' : ''} available`} />
        <KPI icon={<ArrowUpDown size={16} />} iconBg="#dbeafe" iconColor="#2563eb" label="Invoices" value={String(invoices.length)} sub="Total records" />
        <KPI icon={<Coins size={16} />} iconBg="#fef9c3" iconColor="#a16207" label="EMPIRE Price" value="N/A" sub="Token not yet live" />
        <KPI icon={<Zap size={16} />} iconBg="#ede9fe" iconColor="#7c3aed" label="Total Invoiced" value={`$${totalPaymentUsd.toLocaleString('en-US', { minimumFractionDigits: 2 })}`} sub={`${invoices.length} invoice${invoices.length !== 1 ? 's' : ''}`} />
      </div>

      {/* Recent Transactions */}
      <div className="empire-card" style={{ padding: 0, marginBottom: 20 }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid #ece8e0' }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Recent Invoices</span>
        </div>
        {recentTxns.length === 0 ? (
          <EmptyState icon={<Inbox size={32} />} title="No invoices yet" subtitle="Invoice history will appear here" />
        ) : (
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #ece8e0', color: '#999', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                <th style={{ padding: '10px 18px', textAlign: 'left' }}>ID</th>
                <th style={{ padding: '10px 12px', textAlign: 'left' }}>Description</th>
                <th style={{ padding: '10px 12px', textAlign: 'right' }}>Amount</th>
                <th style={{ padding: '10px 12px', textAlign: 'left' }}>Status</th>
                <th style={{ padding: '10px 18px', textAlign: 'right' }}>Date</th>
              </tr>
            </thead>
            <tbody>
              {recentTxns.map(tx => {
                const statusKey = (tx.status || 'pending').toLowerCase();
                const st = STATUS_MAP[statusKey] || STATUS_MAP.pending;
                const StIcon = st.icon;
                return (
                  <tr key={tx.id} style={{ borderBottom: '1px solid #f5f3ef' }}>
                    <td style={{ padding: '10px 18px', fontWeight: 600, color: '#1a1a1a' }}>{tx.id}</td>
                    <td style={{ padding: '10px 12px', color: '#666' }}>{tx.description || '-'}</td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', color: '#1a1a1a' }}>
                      ${(tx.total || tx.amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span className="flex items-center gap-1" style={{ color: st.color }}><StIcon size={13} />{tx.status}</span>
                    </td>
                    <td style={{ padding: '10px 18px', textAlign: 'right', color: '#999', fontSize: 11 }}>{tx.created_at || tx.timestamp || '-'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Supported Chains Summary */}
      <div className="empire-card" style={{ padding: 0 }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid #ece8e0' }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Supported Chains</span>
        </div>
        {chains.length === 0 ? (
          <EmptyState icon={<Wallet size={32} />} title="No chains configured" subtitle="Connect to the backend to see supported chains" />
        ) : (
          <div className="grid grid-cols-5 gap-0">
            {chains.map(w => (
              <div key={w.id} style={{ padding: '16px 18px', borderRight: '1px solid #f5f3ef' }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#999', marginBottom: 4 }}>{w.name}</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a' }}>
                  <span style={{ fontSize: 11, color: CHAIN_COLORS[w.chain] || CHAIN_COLORS[w.token] || '#666' }}>{w.token || w.chain}</span>
                </div>
                <div style={{ fontSize: 11, color: '#999' }}>{w.chain}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ============ WALLETS SECTION ============

function WalletsSection() {
  const { chains, loading, error, refetch } = useChains();

  if (loading) return <Spinner label="Loading supported chains..." />;

  return (
    <div style={{ padding: 24 }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a' }}>Wallets</div>
          <div style={{ fontSize: 12, color: '#999' }}>Supported chains for crypto payments</div>
        </div>
        <button onClick={refetch} className="flex items-center gap-2 cursor-pointer" style={{ padding: '8px 16px', borderRadius: 10, background: '#fff', color: '#666', fontSize: 13, fontWeight: 600, border: '1.5px solid #ece8e0' }}>
          <RefreshCw size={15} /> Refresh
        </button>
      </div>

      {error && <ErrorBanner message={error} onRetry={refetch} />}

      <div className="empire-card" style={{ padding: 0 }}>
        {chains.length === 0 && !error ? (
          <EmptyState icon={<Wallet size={32} />} title="No chains available" subtitle="No supported blockchain networks found from the backend" />
        ) : (
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #ece8e0', color: '#999', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                <th style={{ padding: '12px 18px', textAlign: 'left' }}>Chain Name</th>
                <th style={{ padding: '12px 12px', textAlign: 'left' }}>Network</th>
                <th style={{ padding: '12px 12px', textAlign: 'left' }}>Native Token</th>
                <th style={{ padding: '12px 18px', textAlign: 'center' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {chains.map(c => (
                <tr key={c.id} style={{ borderBottom: '1px solid #f5f3ef' }}>
                  <td style={{ padding: '12px 18px', fontWeight: 600, color: '#1a1a1a' }}>
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: `${CHAIN_COLORS[c.chain] || CHAIN_COLORS[c.token] || '#666'}18`, color: CHAIN_COLORS[c.chain] || CHAIN_COLORS[c.token] || '#666' }}>
                        <Wallet size={14} />
                      </div>
                      {c.name}
                    </div>
                  </td>
                  <td style={{ padding: '12px 12px' }}>
                    <span style={{ padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600, background: `${CHAIN_COLORS[c.chain] || '#666'}18`, color: CHAIN_COLORS[c.chain] || '#666' }}>
                      {c.chain}
                    </span>
                  </td>
                  <td style={{ padding: '12px 12px', fontWeight: 600, color: TOKEN_COLORS[c.token] || '#1a1a1a' }}>
                    {c.token}
                  </td>
                  <td style={{ padding: '12px 18px', textAlign: 'center' }}>
                    <span className="flex items-center justify-center gap-1" style={{ color: ACCENT, fontWeight: 600, fontSize: 11 }}>
                      <CheckCircle size={13} /> Supported
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ============ TRANSACTIONS SECTION ============

function TransactionsSection() {
  const { invoices, loading, error, refetch } = useInvoices();
  const [filter, setFilter] = useState<string>('all');

  const filtered = filter === 'all'
    ? invoices
    : invoices.filter(t => (t.status || '').toLowerCase() === filter || (t.type || '').toLowerCase() === filter);

  if (loading) return <Spinner label="Loading transactions..." />;

  const statusOptions = ['all', ...Array.from(new Set(invoices.map(i => (i.status || 'unknown').toLowerCase())))];

  return (
    <div style={{ padding: 24 }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a' }}>Transactions</div>
          <div style={{ fontSize: 12, color: '#999' }}>Payment history from invoices</div>
        </div>
        <div className="flex gap-2">
          {statusOptions.map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className="cursor-pointer"
              style={{
                padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, border: '1.5px solid',
                background: filter === f ? ACCENT_BG : '#fff',
                color: filter === f ? ACCENT : '#666',
                borderColor: filter === f ? ACCENT_BORDER : '#ece8e0',
                textTransform: 'capitalize',
              }}>
              {f}
            </button>
          ))}
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={refetch} />}

      <div className="empire-card" style={{ padding: 0 }}>
        {filtered.length === 0 ? (
          <EmptyState icon={<ArrowUpDown size={32} />} title="No transactions found" subtitle={filter === 'all' ? 'Transaction history will appear here when invoices are created' : `No transactions with status "${filter}"`} />
        ) : (
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #ece8e0', color: '#999', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                <th style={{ padding: '12px 18px', textAlign: 'left' }}>ID</th>
                <th style={{ padding: '12px 12px', textAlign: 'left' }}>Description</th>
                <th style={{ padding: '12px 12px', textAlign: 'right' }}>Amount</th>
                <th style={{ padding: '12px 12px', textAlign: 'left' }}>Currency</th>
                <th style={{ padding: '12px 12px', textAlign: 'left' }}>Status</th>
                <th style={{ padding: '12px 18px', textAlign: 'right' }}>Date</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(tx => {
                const statusKey = (tx.status || 'pending').toLowerCase();
                const st = STATUS_MAP[statusKey] || STATUS_MAP.pending;
                const StIcon = st.icon;
                return (
                  <tr key={tx.id} style={{ borderBottom: '1px solid #f5f3ef' }}>
                    <td style={{ padding: '10px 18px', fontWeight: 600, color: '#1a1a1a', fontFamily: 'JetBrains Mono, monospace' }}>{tx.id}</td>
                    <td style={{ padding: '10px 12px', color: '#666' }}>{tx.description || '-'}</td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', color: '#1a1a1a' }}>
                      ${(tx.total || tx.amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ color: TOKEN_COLORS[tx.currency || tx.token || ''] || '#666', fontWeight: 600 }}>{tx.currency || tx.token || 'USD'}</span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span className="flex items-center gap-1" style={{ color: st.color, fontWeight: 600, fontSize: 11 }}>
                        <StIcon size={13} />{tx.status}
                      </span>
                    </td>
                    <td style={{ padding: '10px 18px', textAlign: 'right', color: '#999', fontSize: 11 }}>{tx.created_at || tx.timestamp || '-'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ============ PAYMENT LINKS SECTION ============

function PaymentLinksSection() {
  return (
    <div style={{ padding: 24 }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a' }}>Payment Links</div>
          <div style={{ fontSize: 12, color: '#999' }}>Create and manage crypto payment links</div>
        </div>
      </div>

      <div className="empire-card" style={{ padding: 0 }}>
        <EmptyState
          icon={<Link2 size={32} />}
          title="Create your first payment link"
          subtitle="Generate shareable crypto payment links for your customers"
        />
      </div>
    </div>
  );
}

// ============ EMPIRE TOKEN SECTION ============

function EmpireTokenSection() {
  const t = EMPIRE_TOKEN_INFO;
  return (
    <div style={{ padding: 24 }}>
      <div style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>EMPIRE Token</div>
      <div style={{ fontSize: 12, color: '#999', marginBottom: 20 }}>Token metrics, distribution, and management (planned)</div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPI icon={<Coins size={16} />} iconBg={ACCENT_BG} iconColor={ACCENT} label="Price" value="N/A" sub="Token not yet deployed" />
        <KPI icon={<TrendingUp size={16} />} iconBg="#dbeafe" iconColor="#2563eb" label="Market Cap" value="N/A" sub="Pre-launch" />
        <KPI icon={<Eye size={16} />} iconBg="#ede9fe" iconColor="#7c3aed" label="Holders" value="0" sub="Pre-launch" />
        <KPI icon={<Shield size={16} />} iconBg="#fef9c3" iconColor="#a16207" label="Total Supply" value={`${(t.totalSupply / 1e6).toFixed(0)}M`} sub="100,000,000 EMPIRE (planned)" />
      </div>

      {/* Token Info Card */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="empire-card" style={{ padding: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 14 }}>Token Details</div>
          <div className="flex flex-col gap-3">
            {[
              ['Name', t.name],
              ['Symbol', t.symbol],
              ['Chain', t.chain],
              ['Contract', t.contractAddress],
              ['Total Supply', `${t.totalSupply.toLocaleString()} (planned)`],
              ['Status', 'Pre-launch'],
            ].map(([label, val]) => (
              <div key={label} className="flex items-center justify-between" style={{ fontSize: 12 }}>
                <span style={{ color: '#999', fontWeight: 500 }}>{label}</span>
                <span style={{ fontWeight: 600, color: '#1a1a1a', fontFamily: label === 'Contract' ? 'JetBrains Mono, monospace' : 'inherit' }}>{val}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Distribution */}
        <div className="empire-card" style={{ padding: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 14 }}>Planned Distribution</div>
          <div className="flex flex-col gap-2.5">
            {t.distribution.map(d => (
              <div key={d.label}>
                <div className="flex items-center justify-between" style={{ fontSize: 12, marginBottom: 3 }}>
                  <span style={{ color: '#666', fontWeight: 500 }}>{d.label}</span>
                  <span style={{ fontWeight: 600, color: '#1a1a1a' }}>{d.pct}% <span style={{ color: '#999', fontWeight: 400, fontSize: 11 }}>({(d.amount / 1e6).toFixed(1)}M)</span></span>
                </div>
                <div style={{ height: 6, borderRadius: 3, background: '#f5f3ef', overflow: 'hidden' }}>
                  <div style={{ height: '100%', borderRadius: 3, width: `${d.pct}%`, background: d.color, transition: 'width 0.3s' }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============ SETTINGS SECTION ============

function SettingsSection() {
  const { chains, loading, error, refetch } = useChains();
  const [accepted, setAccepted] = useState<Record<string, boolean>>({});
  const [autoConvert, setAutoConvert] = useState(true);

  useEffect(() => {
    if (chains.length > 0 && Object.keys(accepted).length === 0) {
      const initial: Record<string, boolean> = {};
      chains.forEach(c => { initial[c.token || c.name] = true; });
      setAccepted(initial);
    }
  }, [chains, accepted]);

  const toggleCrypto = (token: string) => {
    setAccepted(prev => ({ ...prev, [token]: !prev[token] }));
  };

  if (loading) return <Spinner label="Loading settings..." />;

  return (
    <div style={{ padding: 24 }}>
      <div style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>Settings</div>
      <div style={{ fontSize: 12, color: '#999', marginBottom: 20 }}>Configure payment acceptance and processing</div>

      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {/* Accepted Cryptocurrencies */}
      <div className="empire-card" style={{ padding: 20, marginBottom: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 14 }}>Supported Chains</div>
        {chains.length === 0 ? (
          <EmptyState icon={<Settings size={28} />} title="No chains configured" subtitle="No supported chains returned from backend" />
        ) : (
          <div className="flex flex-col gap-3">
            {chains.map(c => {
              const tokenKey = c.token || c.name;
              return (
                <div key={c.id} className="flex items-center justify-between" style={{ padding: '10px 14px', borderRadius: 10, border: '1.5px solid #ece8e0', background: '#fff' }}>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${CHAIN_COLORS[c.chain] || CHAIN_COLORS[c.token] || '#666'}18`, color: CHAIN_COLORS[c.chain] || CHAIN_COLORS[c.token] || '#666' }}>
                      <Coins size={16} />
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{c.name} <span style={{ color: CHAIN_COLORS[c.token] || '#666', fontSize: 11 }}>({c.token})</span></div>
                      <div style={{ fontSize: 11, color: '#999' }}>{c.chain}</div>
                    </div>
                  </div>
                  <button onClick={() => toggleCrypto(tokenKey)} className="cursor-pointer" style={{ background: 'none', border: 'none', color: accepted[tokenKey] ? ACCENT : '#ccc' }}>
                    {accepted[tokenKey] ? <ToggleRight size={28} /> : <ToggleLeft size={28} />}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Auto-Convert */}
      <div className="empire-card" style={{ padding: 20 }}>
        <div className="flex items-center justify-between">
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 2 }}>Auto-Convert to USDC</div>
            <div style={{ fontSize: 12, color: '#999' }}>Automatically convert received crypto payments to USDC for stability</div>
          </div>
          <button onClick={() => setAutoConvert(!autoConvert)} className="cursor-pointer" style={{ background: 'none', border: 'none', color: autoConvert ? ACCENT : '#ccc' }}>
            {autoConvert ? <ToggleRight size={32} /> : <ToggleLeft size={32} />}
          </button>
        </div>
      </div>
    </div>
  );
}

// ============ MAIN COMPONENT ============

export default function EmpirePayPage() {
  const [section, setSection] = useState<Section>('dashboard');

  const renderContent = () => {
    switch (section) {
      case 'dashboard': return <DashboardSection />;
      case 'wallets': return <WalletsSection />;
      case 'transactions': return <TransactionsSection />;
      case 'payment-links': return <PaymentLinksSection />;
      case 'empire-token': return <EmpireTokenSection />;
      case 'settings': return <SettingsSection />;
      case 'payments': return <PaymentModule product="pay" />;
      case 'docs': return <div style={{ padding: 24 }}><ProductDocs product="pay" /></div>;
      default: return <DashboardSection />;
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      <nav style={{ width: 200, background: '#fff', borderRight: '1px solid #ece8e0', flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '18px 16px', borderBottom: '1px solid #ece8e0' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#dcfce7] flex items-center justify-center">
              <Wallet size={18} className="text-[#16a34a]" />
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>EmpirePay</div>
              <div style={{ fontSize: 10, color: '#999' }}>Crypto Payments</div>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto" style={{ padding: '10px 10px' }}>
          <div className="flex flex-col gap-1.5">
            {NAV_SECTIONS.map(nav => {
              const Icon = nav.icon;
              const isActive = section === nav.id;
              return (
                <button key={nav.id}
                  onClick={() => setSection(nav.id)}
                  className="w-full flex items-center gap-3 text-left cursor-pointer transition-all"
                  style={{
                    padding: '10px 14px', borderRadius: 12, fontSize: 13,
                    fontWeight: isActive ? 700 : 500,
                    background: isActive ? '#dcfce7' : 'transparent',
                    color: isActive ? '#16a34a' : '#666',
                    border: isActive ? '1.5px solid #bbf7d0' : '1.5px solid transparent',
                  }}
                  onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = '#f5f3ef'; e.currentTarget.style.borderColor = '#ece8e0'; } }}
                  onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'transparent'; } }}
                >
                  <Icon size={17} />
                  {nav.label}
                </button>
              );
            })}
          </div>
        </div>
      </nav>
      <div className="flex-1 overflow-y-auto" style={{ background: '#f5f2ed' }}>
        {renderContent()}
      </div>
    </div>
  );
}
