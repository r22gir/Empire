'use client';
import React, { useState } from 'react';
import {
  Wallet, ArrowUpDown, Link2, Coins, Settings, LayoutDashboard,
  TrendingUp, TrendingDown, ArrowUpRight, ArrowDownLeft, Copy,
  CheckCircle, Clock, XCircle, Plus, QrCode, Trash2, ToggleLeft,
  ToggleRight, RefreshCw, ExternalLink, Shield, Zap, Eye, BookOpen, CreditCard
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';

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

// ============ MOCK DATA ============

const MOCK_WALLETS = [
  { id: 'w1', name: 'Main Treasury', address: '0x7a16fF8270133F063aAb6C9977183D9e72835428', chain: 'Ethereum', balance: 12.4521, balanceUsd: 43582.35, token: 'ETH', lastActivity: '2026-03-09 08:14' },
  { id: 'w2', name: 'Solana Hot Wallet', address: '7nYBs13hWLyqnQZgRb2vE4vKpBMf8HmgXS3KaGrfhanL', chain: 'Solana', balance: 342.88, balanceUsd: 48003.20, token: 'SOL', lastActivity: '2026-03-09 07:52' },
  { id: 'w3', name: 'BTC Cold Storage', address: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', chain: 'Bitcoin', balance: 1.08432, balanceUsd: 72891.44, token: 'BTC', lastActivity: '2026-03-08 22:30' },
  { id: 'w4', name: 'USDC Operations', address: '0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC', chain: 'Ethereum', balance: 25000.00, balanceUsd: 25000.00, token: 'USDC', lastActivity: '2026-03-09 09:01' },
  { id: 'w5', name: 'EMPIRE Vault', address: '0xdAC17F958D2ee523a2206206994597C13D831ec7', chain: 'Ethereum', balance: 1500000, balanceUsd: 15000.00, token: 'EMPIRE', lastActivity: '2026-03-09 06:33' },
];

const MOCK_TRANSACTIONS = [
  { id: 'TX-0091', type: 'payment', amount: 0.25, token: 'ETH', from: '0x1234...abcd', to: '0x7a16...5428', status: 'confirmed', timestamp: '2026-03-09 09:12', usdValue: 875.50 },
  { id: 'TX-0090', type: 'transfer', amount: 50.0, token: 'SOL', from: '7nYB...hanL', to: '4kNp...9xQm', status: 'confirmed', timestamp: '2026-03-09 08:44', usdValue: 7005.00 },
  { id: 'TX-0089', type: 'payment', amount: 500.0, token: 'USDC', from: '0x9876...efgh', to: '0x3C44...93BC', status: 'confirmed', timestamp: '2026-03-09 07:30', usdValue: 500.00 },
  { id: 'TX-0088', type: 'mint', amount: 100000, token: 'EMPIRE', from: 'Contract', to: '0xdAC1...1ec7', status: 'confirmed', timestamp: '2026-03-09 06:33', usdValue: 1000.00 },
  { id: 'TX-0087', type: 'payment', amount: 0.015, token: 'BTC', from: 'bc1q...8wlh', to: 'bc1q...4m2k', status: 'pending', timestamp: '2026-03-09 05:15', usdValue: 1009.12 },
  { id: 'TX-0086', type: 'transfer', amount: 2.5, token: 'ETH', from: '0x7a16...5428', to: '0xABCD...1234', status: 'confirmed', timestamp: '2026-03-08 22:01', usdValue: 8755.00 },
  { id: 'TX-0085', type: 'payment', amount: 1250.0, token: 'USDC', from: '0x5555...6666', to: '0x3C44...93BC', status: 'confirmed', timestamp: '2026-03-08 19:44', usdValue: 1250.00 },
  { id: 'TX-0084', type: 'payment', amount: 12.5, token: 'SOL', from: '3Fgh...kLmN', to: '7nYB...hanL', status: 'failed', timestamp: '2026-03-08 18:22', usdValue: 1751.25 },
  { id: 'TX-0083', type: 'mint', amount: 50000, token: 'EMPIRE', from: 'Contract', to: '0xdAC1...1ec7', status: 'confirmed', timestamp: '2026-03-08 14:00', usdValue: 500.00 },
  { id: 'TX-0082', type: 'payment', amount: 0.05, token: 'BTC', from: 'bc1q...7pqr', to: 'bc1q...8wlh', status: 'confirmed', timestamp: '2026-03-08 11:30', usdValue: 3363.04 },
];

const MOCK_PAYMENT_LINKS = [
  { id: 'PL-001', amount: 100.00, description: 'Website Design Deposit', tokens: ['ETH', 'USDC', 'SOL'], expiry: '2026-03-16', status: 'active', created: '2026-03-09', clicks: 12, payments: 2 },
  { id: 'PL-002', amount: 500.00, description: 'LLC Formation Package', tokens: ['USDC', 'BTC'], expiry: '2026-03-23', status: 'active', created: '2026-03-08', clicks: 8, payments: 1 },
  { id: 'PL-003', amount: 25.00, description: 'Consultation Fee', tokens: ['ETH', 'SOL', 'USDC', 'EMPIRE'], expiry: '2026-03-12', status: 'active', created: '2026-03-07', clicks: 34, payments: 5 },
  { id: 'PL-004', amount: 1000.00, description: 'Premium Service Retainer', tokens: ['BTC', 'ETH'], expiry: '2026-03-05', status: 'expired', created: '2026-03-01', clicks: 3, payments: 0 },
];

const EMPIRE_TOKEN_INFO = {
  name: 'EMPIRE',
  symbol: 'EMPIRE',
  chain: 'Ethereum (ERC-20)',
  contractAddress: '0xdAC17F958D2ee523a2206206994597C13D831ec7',
  totalSupply: 100000000,
  circulatingSupply: 8500000,
  holders: 1247,
  price: 0.01,
  marketCap: 85000,
  change24h: 4.2,
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
  pending: { bg: '#fef9c3', color: '#a16207', icon: Clock },
  failed: { bg: '#fee2e2', color: '#dc2626', icon: XCircle },
};

const ACCENT = '#16a34a';
const ACCENT_BG = '#dcfce7';
const ACCENT_BORDER = '#bbf7d0';

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

// ============ DASHBOARD SECTION ============

function DashboardSection() {
  const totalUsd = MOCK_WALLETS.reduce((s, w) => s + w.balanceUsd, 0);
  const recentTxns = MOCK_TRANSACTIONS.slice(0, 5);
  const paymentsProcessed = MOCK_TRANSACTIONS.filter(t => t.type === 'payment').length;
  const totalPaymentUsd = MOCK_TRANSACTIONS.filter(t => t.type === 'payment').reduce((s, t) => s + t.usdValue, 0);

  return (
    <div style={{ padding: 24 }}>
      <div style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>EmpirePay Dashboard</div>
      <div style={{ fontSize: 12, color: '#999', marginBottom: 20 }}>Crypto payments, wallets, and EMPIRE token management</div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPI icon={<Wallet size={16} />} iconBg={ACCENT_BG} iconColor={ACCENT} label="Total Balance" value={`$${totalUsd.toLocaleString('en-US', { minimumFractionDigits: 2 })}`} sub={`${MOCK_WALLETS.length} wallets`} />
        <KPI icon={<ArrowUpDown size={16} />} iconBg="#dbeafe" iconColor="#2563eb" label="Transactions" value={String(MOCK_TRANSACTIONS.length)} sub="Last 7 days" />
        <KPI icon={<Coins size={16} />} iconBg="#fef9c3" iconColor="#a16207" label="EMPIRE Price" value={`$${EMPIRE_TOKEN_INFO.price.toFixed(4)}`} sub={`${EMPIRE_TOKEN_INFO.change24h > 0 ? '+' : ''}${EMPIRE_TOKEN_INFO.change24h}% (24h)`} />
        <KPI icon={<Zap size={16} />} iconBg="#ede9fe" iconColor="#7c3aed" label="Payments Processed" value={`$${totalPaymentUsd.toLocaleString('en-US', { minimumFractionDigits: 2 })}`} sub={`${paymentsProcessed} payments`} />
      </div>

      {/* Recent Transactions */}
      <div className="empire-card" style={{ padding: 0, marginBottom: 20 }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid #ece8e0' }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Recent Transactions</span>
        </div>
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #ece8e0', color: '#999', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              <th style={{ padding: '10px 18px', textAlign: 'left' }}>ID</th>
              <th style={{ padding: '10px 12px', textAlign: 'left' }}>Type</th>
              <th style={{ padding: '10px 12px', textAlign: 'right' }}>Amount</th>
              <th style={{ padding: '10px 12px', textAlign: 'left' }}>Token</th>
              <th style={{ padding: '10px 12px', textAlign: 'left' }}>Status</th>
              <th style={{ padding: '10px 18px', textAlign: 'right' }}>Time</th>
            </tr>
          </thead>
          <tbody>
            {recentTxns.map(tx => {
              const st = STATUS_MAP[tx.status] || STATUS_MAP.pending;
              const StIcon = st.icon;
              return (
                <tr key={tx.id} style={{ borderBottom: '1px solid #f5f3ef' }}>
                  <td style={{ padding: '10px 18px', fontWeight: 600, color: '#1a1a1a' }}>{tx.id}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{ padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600, background: tx.type === 'payment' ? ACCENT_BG : tx.type === 'mint' ? '#ede9fe' : '#dbeafe', color: tx.type === 'payment' ? ACCENT : tx.type === 'mint' ? '#7c3aed' : '#2563eb' }}>
                      {tx.type}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', color: '#1a1a1a' }}>{tx.amount.toLocaleString()}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{ color: TOKEN_COLORS[tx.token] || '#666', fontWeight: 600 }}>{tx.token}</span>
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <span className="flex items-center gap-1" style={{ color: st.color }}><StIcon size={13} />{tx.status}</span>
                  </td>
                  <td style={{ padding: '10px 18px', textAlign: 'right', color: '#999', fontSize: 11 }}>{tx.timestamp}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Wallet Summary */}
      <div className="empire-card" style={{ padding: 0 }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid #ece8e0' }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Wallet Balances</span>
        </div>
        <div className="grid grid-cols-5 gap-0">
          {MOCK_WALLETS.map(w => (
            <div key={w.id} style={{ padding: '16px 18px', borderRight: '1px solid #f5f3ef' }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#999', marginBottom: 4 }}>{w.name}</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a' }}>{w.balance.toLocaleString()} <span style={{ fontSize: 11, color: TOKEN_COLORS[w.token] || '#666' }}>{w.token}</span></div>
              <div style={{ fontSize: 11, color: '#999' }}>${w.balanceUsd.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============ WALLETS SECTION ============

function WalletsSection() {
  const [copied, setCopied] = useState<string | null>(null);

  const handleCopy = (addr: string, id: string) => {
    navigator.clipboard.writeText(addr).catch(() => {});
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div style={{ padding: 24 }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a' }}>Wallets</div>
          <div style={{ fontSize: 12, color: '#999' }}>Manage connected wallets across all chains</div>
        </div>
        <button className="flex items-center gap-2 cursor-pointer" style={{ padding: '8px 16px', borderRadius: 10, background: ACCENT, color: '#fff', fontSize: 13, fontWeight: 600, border: 'none' }}>
          <Plus size={15} /> Add Wallet
        </button>
      </div>

      <div className="empire-card" style={{ padding: 0 }}>
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #ece8e0', color: '#999', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              <th style={{ padding: '12px 18px', textAlign: 'left' }}>Wallet Name</th>
              <th style={{ padding: '12px 12px', textAlign: 'left' }}>Address</th>
              <th style={{ padding: '12px 12px', textAlign: 'left' }}>Chain</th>
              <th style={{ padding: '12px 12px', textAlign: 'right' }}>Balance</th>
              <th style={{ padding: '12px 12px', textAlign: 'right' }}>USD Value</th>
              <th style={{ padding: '12px 12px', textAlign: 'right' }}>Last Activity</th>
              <th style={{ padding: '12px 18px', textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_WALLETS.map(w => (
              <tr key={w.id} style={{ borderBottom: '1px solid #f5f3ef' }}>
                <td style={{ padding: '12px 18px', fontWeight: 600, color: '#1a1a1a' }}>
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: `${TOKEN_COLORS[w.token]}18`, color: TOKEN_COLORS[w.token] }}>
                      <Wallet size={14} />
                    </div>
                    {w.name}
                  </div>
                </td>
                <td style={{ padding: '12px 12px', fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>
                  <span className="flex items-center gap-1.5" style={{ color: '#666' }}>
                    {truncAddr(w.address)}
                    <button onClick={() => handleCopy(w.address, w.id)} className="cursor-pointer" style={{ background: 'none', border: 'none', color: copied === w.id ? ACCENT : '#999', padding: 2 }}>
                      {copied === w.id ? <CheckCircle size={13} /> : <Copy size={13} />}
                    </button>
                  </span>
                </td>
                <td style={{ padding: '12px 12px' }}>
                  <span style={{ padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600, background: `${CHAIN_COLORS[w.chain] || '#666'}18`, color: CHAIN_COLORS[w.chain] || '#666' }}>
                    {w.chain}
                  </span>
                </td>
                <td style={{ padding: '12px 12px', textAlign: 'right', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', color: '#1a1a1a' }}>
                  {w.balance.toLocaleString()} <span style={{ color: TOKEN_COLORS[w.token], fontSize: 10 }}>{w.token}</span>
                </td>
                <td style={{ padding: '12px 12px', textAlign: 'right', fontWeight: 600, color: '#1a1a1a' }}>
                  ${w.balanceUsd.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </td>
                <td style={{ padding: '12px 12px', textAlign: 'right', color: '#999', fontSize: 11 }}>{w.lastActivity}</td>
                <td style={{ padding: '12px 18px', textAlign: 'center' }}>
                  <button className="cursor-pointer" style={{ background: 'none', border: 'none', color: '#999', padding: 4 }} title="View on explorer"><ExternalLink size={14} /></button>
                  <button className="cursor-pointer" style={{ background: 'none', border: 'none', color: '#999', padding: 4 }} title="Refresh"><RefreshCw size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============ TRANSACTIONS SECTION ============

function TransactionsSection() {
  const [filter, setFilter] = useState<'all' | 'payment' | 'transfer' | 'mint'>('all');
  const filtered = filter === 'all' ? MOCK_TRANSACTIONS : MOCK_TRANSACTIONS.filter(t => t.type === filter);

  return (
    <div style={{ padding: 24 }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a' }}>Transactions</div>
          <div style={{ fontSize: 12, color: '#999' }}>All payments, transfers, and token operations</div>
        </div>
        <div className="flex gap-2">
          {(['all', 'payment', 'transfer', 'mint'] as const).map(f => (
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

      <div className="empire-card" style={{ padding: 0 }}>
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #ece8e0', color: '#999', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              <th style={{ padding: '12px 18px', textAlign: 'left' }}>ID</th>
              <th style={{ padding: '12px 12px', textAlign: 'left' }}>Type</th>
              <th style={{ padding: '12px 12px', textAlign: 'right' }}>Amount</th>
              <th style={{ padding: '12px 12px', textAlign: 'left' }}>Token</th>
              <th style={{ padding: '12px 12px', textAlign: 'left' }}>From</th>
              <th style={{ padding: '12px 12px', textAlign: 'left' }}>To</th>
              <th style={{ padding: '12px 12px', textAlign: 'left' }}>Status</th>
              <th style={{ padding: '12px 12px', textAlign: 'right' }}>USD Value</th>
              <th style={{ padding: '12px 18px', textAlign: 'right' }}>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(tx => {
              const st = STATUS_MAP[tx.status] || STATUS_MAP.pending;
              const StIcon = st.icon;
              return (
                <tr key={tx.id} style={{ borderBottom: '1px solid #f5f3ef' }}>
                  <td style={{ padding: '10px 18px', fontWeight: 600, color: '#1a1a1a', fontFamily: 'JetBrains Mono, monospace' }}>{tx.id}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span className="flex items-center gap-1.5" style={{
                      padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600, display: 'inline-flex',
                      background: tx.type === 'payment' ? ACCENT_BG : tx.type === 'mint' ? '#ede9fe' : '#dbeafe',
                      color: tx.type === 'payment' ? ACCENT : tx.type === 'mint' ? '#7c3aed' : '#2563eb',
                    }}>
                      {tx.type === 'payment' ? <ArrowDownLeft size={11} /> : tx.type === 'transfer' ? <ArrowUpRight size={11} /> : <Coins size={11} />}
                      {tx.type}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', color: '#1a1a1a' }}>{tx.amount.toLocaleString()}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{ color: TOKEN_COLORS[tx.token] || '#666', fontWeight: 600 }}>{tx.token}</span>
                  </td>
                  <td style={{ padding: '10px 12px', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#666' }}>{tx.from}</td>
                  <td style={{ padding: '10px 12px', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#666' }}>{tx.to}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span className="flex items-center gap-1" style={{ color: st.color, fontWeight: 600, fontSize: 11 }}>
                      <StIcon size={13} />{tx.status}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', textAlign: 'right', color: '#1a1a1a', fontWeight: 500 }}>${tx.usdValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                  <td style={{ padding: '10px 18px', textAlign: 'right', color: '#999', fontSize: 11 }}>{tx.timestamp}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============ PAYMENT LINKS SECTION ============

function PaymentLinksSection() {
  const [showCreate, setShowCreate] = useState(false);
  const [newLink, setNewLink] = useState({ amount: '', description: '', tokens: ['ETH', 'USDC'] as string[], expiryDays: '7' });

  const toggleToken = (token: string) => {
    setNewLink(prev => ({
      ...prev,
      tokens: prev.tokens.includes(token) ? prev.tokens.filter(t => t !== token) : [...prev.tokens, token],
    }));
  };

  return (
    <div style={{ padding: 24 }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a' }}>Payment Links</div>
          <div style={{ fontSize: 12, color: '#999' }}>Create and manage crypto payment links</div>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="flex items-center gap-2 cursor-pointer" style={{ padding: '8px 16px', borderRadius: 10, background: ACCENT, color: '#fff', fontSize: 13, fontWeight: 600, border: 'none' }}>
          <Plus size={15} /> Create Link
        </button>
      </div>

      {showCreate && (
        <div className="empire-card" style={{ padding: 20, marginBottom: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 14 }}>New Payment Link</div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#999', display: 'block', marginBottom: 4 }}>Amount (USD)</label>
              <input type="number" value={newLink.amount} onChange={e => setNewLink(p => ({ ...p, amount: e.target.value }))}
                placeholder="0.00"
                style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1.5px solid #ece8e0', fontSize: 13, outline: 'none' }} />
            </div>
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#999', display: 'block', marginBottom: 4 }}>Description</label>
              <input type="text" value={newLink.description} onChange={e => setNewLink(p => ({ ...p, description: e.target.value }))}
                placeholder="What is this payment for?"
                style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1.5px solid #ece8e0', fontSize: 13, outline: 'none' }} />
            </div>
          </div>
          <div className="mb-4">
            <label style={{ fontSize: 11, fontWeight: 600, color: '#999', display: 'block', marginBottom: 6 }}>Accepted Tokens</label>
            <div className="flex gap-2">
              {['ETH', 'SOL', 'BTC', 'USDC', 'EMPIRE'].map(t => (
                <button key={t} onClick={() => toggleToken(t)} className="cursor-pointer"
                  style={{
                    padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, border: '1.5px solid',
                    background: newLink.tokens.includes(t) ? `${TOKEN_COLORS[t]}18` : '#fff',
                    color: newLink.tokens.includes(t) ? TOKEN_COLORS[t] : '#999',
                    borderColor: newLink.tokens.includes(t) ? TOKEN_COLORS[t] : '#ece8e0',
                  }}>
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-end gap-4">
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#999', display: 'block', marginBottom: 4 }}>Expires In</label>
              <select value={newLink.expiryDays} onChange={e => setNewLink(p => ({ ...p, expiryDays: e.target.value }))}
                style={{ padding: '8px 12px', borderRadius: 8, border: '1.5px solid #ece8e0', fontSize: 13, outline: 'none' }}>
                <option value="1">1 day</option>
                <option value="3">3 days</option>
                <option value="7">7 days</option>
                <option value="14">14 days</option>
                <option value="30">30 days</option>
                <option value="0">Never</option>
              </select>
            </div>
            <div className="flex-1" />
            <div style={{ width: 80, height: 80, borderRadius: 12, background: '#f5f3ef', border: '2px dashed #ddd', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ccc' }}>
              <QrCode size={32} />
            </div>
            <button className="cursor-pointer" style={{ padding: '8px 20px', borderRadius: 10, background: ACCENT, color: '#fff', fontSize: 13, fontWeight: 600, border: 'none', height: 38 }}>
              Generate Link
            </button>
          </div>
        </div>
      )}

      <div className="empire-card" style={{ padding: 0 }}>
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #ece8e0', color: '#999', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              <th style={{ padding: '12px 18px', textAlign: 'left' }}>ID</th>
              <th style={{ padding: '12px 12px', textAlign: 'left' }}>Description</th>
              <th style={{ padding: '12px 12px', textAlign: 'right' }}>Amount</th>
              <th style={{ padding: '12px 12px', textAlign: 'left' }}>Tokens</th>
              <th style={{ padding: '12px 12px', textAlign: 'left' }}>Status</th>
              <th style={{ padding: '12px 12px', textAlign: 'center' }}>Clicks</th>
              <th style={{ padding: '12px 12px', textAlign: 'center' }}>Payments</th>
              <th style={{ padding: '12px 12px', textAlign: 'right' }}>Expires</th>
              <th style={{ padding: '12px 18px', textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_PAYMENT_LINKS.map(pl => (
              <tr key={pl.id} style={{ borderBottom: '1px solid #f5f3ef' }}>
                <td style={{ padding: '10px 18px', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', color: '#1a1a1a' }}>{pl.id}</td>
                <td style={{ padding: '10px 12px', color: '#1a1a1a', fontWeight: 500 }}>{pl.description}</td>
                <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', color: '#1a1a1a' }}>${pl.amount.toFixed(2)}</td>
                <td style={{ padding: '10px 12px' }}>
                  <div className="flex gap-1">
                    {pl.tokens.map(t => (
                      <span key={t} style={{ padding: '1px 6px', borderRadius: 4, fontSize: 10, fontWeight: 600, background: `${TOKEN_COLORS[t]}18`, color: TOKEN_COLORS[t] }}>{t}</span>
                    ))}
                  </div>
                </td>
                <td style={{ padding: '10px 12px' }}>
                  <span style={{
                    padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                    background: pl.status === 'active' ? ACCENT_BG : '#fee2e2',
                    color: pl.status === 'active' ? ACCENT : '#dc2626',
                  }}>{pl.status}</span>
                </td>
                <td style={{ padding: '10px 12px', textAlign: 'center', color: '#666' }}>{pl.clicks}</td>
                <td style={{ padding: '10px 12px', textAlign: 'center', fontWeight: 600, color: ACCENT }}>{pl.payments}</td>
                <td style={{ padding: '10px 12px', textAlign: 'right', color: '#999', fontSize: 11 }}>{pl.expiry}</td>
                <td style={{ padding: '10px 18px', textAlign: 'center' }}>
                  <button className="cursor-pointer" style={{ background: 'none', border: 'none', color: '#999', padding: 4 }} title="Copy link"><Copy size={14} /></button>
                  <button className="cursor-pointer" style={{ background: 'none', border: 'none', color: '#999', padding: 4 }} title="QR Code"><QrCode size={14} /></button>
                  <button className="cursor-pointer" style={{ background: 'none', border: 'none', color: '#dc2626', padding: 4 }} title="Delete"><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
      <div style={{ fontSize: 12, color: '#999', marginBottom: 20 }}>Token metrics, distribution, and management</div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPI icon={<Coins size={16} />} iconBg={ACCENT_BG} iconColor={ACCENT} label="Price" value={`$${t.price.toFixed(4)}`} sub={`${t.change24h > 0 ? '+' : ''}${t.change24h}% (24h)`} />
        <KPI icon={<TrendingUp size={16} />} iconBg="#dbeafe" iconColor="#2563eb" label="Market Cap" value={`$${t.marketCap.toLocaleString()}`} sub={`${t.circulatingSupply.toLocaleString()} circulating`} />
        <KPI icon={<Eye size={16} />} iconBg="#ede9fe" iconColor="#7c3aed" label="Holders" value={t.holders.toLocaleString()} sub="Unique addresses" />
        <KPI icon={<Shield size={16} />} iconBg="#fef9c3" iconColor="#a16207" label="Total Supply" value={`${(t.totalSupply / 1e6).toFixed(0)}M`} sub="100,000,000 EMPIRE" />
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
              ['Contract', truncAddr(t.contractAddress)],
              ['Total Supply', t.totalSupply.toLocaleString()],
              ['Circulating Supply', t.circulatingSupply.toLocaleString()],
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
          <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 14 }}>Distribution Breakdown</div>
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
  const [accepted, setAccepted] = useState<Record<string, boolean>>({ ETH: true, SOL: true, BTC: true, USDC: true, EMPIRE: true });
  const [confirmations, setConfirmations] = useState<Record<string, number>>({ ETH: 12, SOL: 1, BTC: 3 });
  const [autoConvert, setAutoConvert] = useState(true);

  const toggleCrypto = (token: string) => {
    setAccepted(prev => ({ ...prev, [token]: !prev[token] }));
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>Settings</div>
      <div style={{ fontSize: 12, color: '#999', marginBottom: 20 }}>Configure payment acceptance and processing</div>

      {/* Accepted Cryptocurrencies */}
      <div className="empire-card" style={{ padding: 20, marginBottom: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 14 }}>Accepted Cryptocurrencies</div>
        <div className="flex flex-col gap-3">
          {[
            { token: 'ETH', name: 'Ethereum', chain: 'ERC-20' },
            { token: 'SOL', name: 'Solana', chain: 'SPL' },
            { token: 'BTC', name: 'Bitcoin', chain: 'Native' },
            { token: 'USDC', name: 'USD Coin', chain: 'ERC-20 / SPL' },
            { token: 'EMPIRE', name: 'EMPIRE Token', chain: 'ERC-20' },
          ].map(c => (
            <div key={c.token} className="flex items-center justify-between" style={{ padding: '10px 14px', borderRadius: 10, border: '1.5px solid #ece8e0', background: '#fff' }}>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${TOKEN_COLORS[c.token]}18`, color: TOKEN_COLORS[c.token] }}>
                  <Coins size={16} />
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{c.name} <span style={{ color: TOKEN_COLORS[c.token], fontSize: 11 }}>({c.token})</span></div>
                  <div style={{ fontSize: 11, color: '#999' }}>{c.chain}</div>
                </div>
              </div>
              <button onClick={() => toggleCrypto(c.token)} className="cursor-pointer" style={{ background: 'none', border: 'none', color: accepted[c.token] ? ACCENT : '#ccc' }}>
                {accepted[c.token] ? <ToggleRight size={28} /> : <ToggleLeft size={28} />}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Confirmation Requirements */}
      <div className="empire-card" style={{ padding: 20, marginBottom: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 14 }}>Confirmation Requirements</div>
        <div style={{ fontSize: 12, color: '#999', marginBottom: 14 }}>Set the number of block confirmations required before a payment is accepted</div>
        <div className="flex flex-col gap-3">
          {Object.entries(confirmations).map(([chain, count]) => (
            <div key={chain} className="flex items-center justify-between" style={{ padding: '10px 14px', borderRadius: 10, border: '1.5px solid #ece8e0', background: '#fff' }}>
              <div className="flex items-center gap-2">
                <span style={{ fontSize: 13, fontWeight: 600, color: CHAIN_COLORS[chain === 'ETH' ? 'Ethereum' : chain === 'SOL' ? 'Solana' : 'Bitcoin'] }}>{chain}</span>
                <span style={{ fontSize: 12, color: '#999' }}>confirmations</span>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => setConfirmations(p => ({ ...p, [chain]: Math.max(1, (p[chain] || 1) - 1) }))}
                  className="cursor-pointer" style={{ width: 28, height: 28, borderRadius: 6, border: '1.5px solid #ece8e0', background: '#fff', fontSize: 14, fontWeight: 700, color: '#666', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>-</button>
                <span style={{ width: 32, textAlign: 'center', fontSize: 14, fontWeight: 700, color: '#1a1a1a', fontFamily: 'JetBrains Mono, monospace' }}>{count}</span>
                <button onClick={() => setConfirmations(p => ({ ...p, [chain]: (p[chain] || 1) + 1 }))}
                  className="cursor-pointer" style={{ width: 28, height: 28, borderRadius: 6, border: '1.5px solid #ece8e0', background: '#fff', fontSize: 14, fontWeight: 700, color: '#666', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>+</button>
              </div>
            </div>
          ))}
        </div>
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
