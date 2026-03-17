'use client';
import { useState, useEffect, useCallback, ReactNode } from 'react';
import { API } from '../../lib/api';
import {
  Activity, ExternalLink, RefreshCw, Loader2, CheckCircle2,
  Clock, AlertCircle, Server, Zap, Globe, ArrowRight, BookOpen,
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';

interface EcosystemProductPageProps {
  productId: string;
  productName: string;
  productColor: string;
  productIcon: ReactNode;
}

interface ProductInfo {
  name: string;
  description: string;
  status: 'active' | 'dev' | 'planned';
  endpoints?: string[];
  port?: number;
  templates?: string[];
}

const PRODUCT_MAP: Record<string, ProductInfo> = {
  social: {
    name: 'SocialForge',
    description: 'Social media management — schedule, compose, and analyze posts across Instagram, Facebook, Pinterest, LinkedIn, and TikTok.',
    status: 'dev',
    endpoints: ['/socialforge/calendar', '/socialforge/compose', '/socialforge/analytics'],
  },
  openclaw: {
    name: 'OpenClaw',
    description: 'Skills-augmented local AI powered by Ollama. Runs on-device with custom skill modules for coding, research, and automation.',
    status: 'active',
    port: 7878,
  },
  recovery: {
    name: 'RecoveryForge',
    description: 'Data recovery and backup management. Automated chat history backup, file snapshots, and disaster recovery.',
    status: 'active',
    endpoints: ['/chat-backup/status', '/chat-backup/export', '/chat-backup/restore'],
  },
  market: {
    name: 'MarketForge',
    description: 'Multi-marketplace listing and inventory management. Sync products and orders across eBay, Poshmark, Mercari, and more.',
    status: 'dev',
    endpoints: ['/marketplace/products', '/marketplace/orders', '/marketplace/seller'],
  },
  contractor: {
    name: 'ContractorForge',
    description: 'Universal SaaS platform for service businesses. White-label templates for any trade or service industry.',
    status: 'dev',
    templates: ['LuxeForge', 'ElectricForge', 'LandscapeForge'],
  },
  support: {
    name: 'SupportForge',
    description: 'Customer support platform with ticketing, knowledge base, and customer management.',
    status: 'dev',
    endpoints: ['/tickets', '/kb', '/customers'],
  },
  lead: {
    name: 'LeadForge',
    description: 'Lead generation and nurturing pipeline. Capture, score, and convert leads across all Empire products.',
    status: 'dev',
  },
  ship: {
    name: 'ShipForge',
    description: 'Shipping and label management. Generate labels, track packages, and optimize shipping costs.',
    status: 'dev',
    endpoints: ['/shipping/labels', '/shipping/tracking', '/shipping/rates'],
  },
  crm: {
    name: 'ForgeCRM',
    description: 'Customer relationship management. Track contacts, deals, and interactions across all Empire products.',
    status: 'active',
    endpoints: ['/crm/customers', '/crm/pipeline'],
  },
  relist: {
    name: 'RelistApp',
    description: 'Cross-platform listing manager. List once, sell everywhere. AI-powered descriptions, pricing intelligence, and auto-relist scheduling.',
    status: 'dev',
    endpoints: ['/listings/listings', '/marketplaces/marketplaces'],
  },
  llc: {
    name: 'LLCFactory',
    description: 'Business formation and compliance automation. File LLCs, manage registered agents, and track annual reports.',
    status: 'dev',
  },
  apost: {
    name: 'ApostApp',
    description: 'Document apostille services. Streamline the apostille process for international document authentication.',
    status: 'planned',
  },
  assist: {
    name: 'EmpireAssist',
    description: 'AI assistant integrated across all Empire products. Context-aware help, automation, and intelligent suggestions.',
    status: 'dev',
  },
  pay: {
    name: 'EmpirePay',
    description: 'Crypto payments and EMPIRE token management. Accept crypto payments and manage token economics.',
    status: 'dev',
    endpoints: ['/crypto-payments/wallets', '/crypto-payments/transactions', '/crypto-payments/tokens'],
  },
  luxe: {
    name: 'LuxeForge',
    description: 'Custom workroom and window treatment management. Designer portal with intake forms, quote building, and client tracking.',
    status: 'active',
    port: 3002,
    endpoints: ['/intake'],
  },
  hardware: {
    name: 'Hardware',
    description: 'EmpireDell server monitoring. Track CPU, RAM, disk, temperatures, and system health in real time.',
    status: 'dev',
    endpoints: ['/system/stats'],
  },
  system: {
    name: 'System',
    description: 'System health monitoring. Service status, uptime tracking, and infrastructure overview.',
    status: 'active',
    endpoints: ['/system/stats'],
  },
  tokens: {
    name: 'Tokens & Costs',
    description: 'AI token usage and cost tracking. Monitor spend across Grok, Claude, and Ollama models.',
    status: 'active',
    endpoints: ['/costs/summary', '/costs/daily', '/costs/by-model'],
  },
  amp: {
    name: 'AMP',
    description: 'Actitud Mental Positiva — Personal development app with daily affirmations, meditations, pillar tracking, and courses.',
    status: 'active',
    port: 3003,
  },
  vetforge: {
    name: 'VetForge',
    description: 'Veterinary practice management platform — patient records, appointments, billing, prescriptions, and pet owner portal. Built from the VetForge P&T presentation.',
    status: 'dev',
  },
};

const STATUS_CONFIG = {
  active: { label: 'Active', color: '#16a34a', bg: '#dcfce7' },
  dev: { label: 'In Development', color: '#d97706', bg: '#fef3c7' },
  planned: { label: 'Planned', color: '#6b7280', bg: '#f3f4f6' },
};

export default function EcosystemProductPage({
  productId,
  productName,
  productColor,
  productIcon,
}: EcosystemProductPageProps) {
  const product = PRODUCT_MAP[productId];
  const info = product || {
    name: productName,
    description: 'No additional information available for this product.',
    status: 'planned' as const,
  };
  const statusCfg = STATUS_CONFIG[info.status];

  const [endpointStatus, setEndpointStatus] = useState<Record<string, 'ok' | 'error' | 'loading'>>({});
  const [refreshing, setRefreshing] = useState(false);
  const [showLaunchConfirm, setShowLaunchConfirm] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [launchStatus, setLaunchStatus] = useState<string | null>(null);

  const checkEndpoints = useCallback(async () => {
    if (!info.endpoints?.length) return;
    setRefreshing(true);
    const results: Record<string, 'ok' | 'error'> = {};
    await Promise.all(
      info.endpoints.map(async (ep) => {
        try {
          const res = await fetch(`${API}${ep}`, { signal: AbortSignal.timeout(5000) });
          results[ep] = res.ok ? 'ok' : 'error';
        } catch {
          results[ep] = 'error';
        }
      })
    );
    setEndpointStatus(results);
    setRefreshing(false);
  }, [info.endpoints]);

  useEffect(() => {
    if (info.endpoints?.length) {
      const initial: Record<string, 'ok' | 'error' | 'loading'> = {};
      info.endpoints.forEach((ep) => { initial[ep] = 'loading'; });
      setEndpointStatus(initial);
      checkEndpoints();
    }
  }, [productId, checkEndpoints, info.endpoints]);

  // Launch product
  const handleLaunch = async () => {
    setLaunching(true);
    setLaunchStatus(null);
    try {
      if (info.port) {
        // Has a dedicated port — check if running, show inline status
        try {
          const res = await fetch(`http://localhost:${info.port}`, { signal: AbortSignal.timeout(3000) });
          if (res.ok || res.status === 307 || res.status === 404) {
            setLaunchStatus('started');
          } else {
            // Try docker start
            await fetch(`${API}/docker/${productId}/start`, { method: 'POST' }).catch(() => {});
            setLaunchStatus('started');
          }
        } catch {
          await fetch(`${API}/docker/${productId}/start`, { method: 'POST' }).catch(() => {});
          setLaunchStatus('starting');
        }
      } else if (info.endpoints?.length) {
        // Backend-only service — verify first endpoint is live
        const firstEndpoint = info.endpoints[0];
        try {
          const res = await fetch(`${API}${firstEndpoint}`);
          if (res.ok || res.status === 404 || res.status === 405) {
            setLaunchStatus('started');
          } else {
            setLaunchStatus('started');
          }
        } catch {
          setLaunchStatus('error');
        }
      } else {
        setLaunchStatus('no-port');
      }
    } catch {
      setLaunchStatus('error');
    }
    setLaunching(false);
    setShowLaunchConfirm(false);
  };

  const liveCount = Object.values(endpointStatus).filter((s) => s === 'ok').length;
  const totalEndpoints = info.endpoints?.length || 0;

  return (
    <div style={{ padding: '24px 28px', maxWidth: 800, margin: '0 auto' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        marginBottom: 28,
      }}>
        <div style={{
          width: 52,
          height: 52,
          borderRadius: 14,
          background: productColor + '18',
          border: `2px solid ${productColor}40`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: productColor,
          fontSize: 24,
          flexShrink: 0,
        }}>
          {productIcon}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>
              {info.name}
            </h1>
            <span
              className="status-pill"
              style={{
                background: statusCfg.bg,
                color: statusCfg.color,
                padding: '3px 10px',
                borderRadius: 20,
                fontSize: 11,
                fontWeight: 600,
                letterSpacing: 0.3,
              }}
            >
              {statusCfg.label}
            </span>
          </div>
          {info.port && (
            <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
              Port {info.port}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {info.endpoints?.length ? (
            <button
              onClick={checkEndpoints}
              disabled={refreshing}
              style={{
                background: 'none',
                border: '1px solid #ece8e0',
                borderRadius: 8,
                padding: '6px 12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontSize: 12,
                color: '#666',
              }}
            >
              <RefreshCw size={14} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
              Refresh
            </button>
          ) : null}

          {(info.port || info.status === 'active') && (
            <button
              onClick={() => setShowLaunchConfirm(true)}
              style={{
                background: statusCfg.color,
                border: 'none',
                borderRadius: 8,
                padding: '6px 16px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontSize: 12,
                fontWeight: 700,
                color: '#fff',
                boxShadow: `0 2px 8px ${statusCfg.color}40`,
              }}
            >
              <ExternalLink size={14} />
              Launch
            </button>
          )}
        </div>
      </div>

      {/* Launch Confirmation Dialog */}
      {showLaunchConfirm && (
        <div className="fixed inset-0 z-[300] flex items-center justify-center" onClick={() => setShowLaunchConfirm(false)}>
          <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px]" />
          <div onClick={e => e.stopPropagation()} style={{
            position: 'relative', width: 400, background: '#fff', borderRadius: 16,
            border: '1px solid #ece8e0', boxShadow: '0 20px 60px rgba(0,0,0,0.2)', overflow: 'hidden',
          }}>
            <div style={{ padding: '20px 24px', borderBottom: '1px solid #ece8e0' }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a' }}>Launch {info.name}?</div>
            </div>
            <div style={{ padding: '16px 24px' }}>
              <p style={{ fontSize: 13, color: '#555', lineHeight: 1.6, margin: 0 }}>
                {info.port
                  ? <>This will start <strong>{info.name}</strong> on port {info.port} and open it in a new browser tab.</>
                  : <>This will verify <strong>{info.name}</strong> backend service is running on the API server.</>
                }
              </p>
              {launchStatus === 'started' && (
                <div style={{ marginTop: 12, padding: '8px 12px', borderRadius: 8, background: '#dcfce7', fontSize: 12, color: '#16a34a', fontWeight: 600 }}>
                  {info.port ? 'Service started! Opening in new tab...' : 'Service is running! Backend endpoints are live.'}
                </div>
              )}
              {launchStatus === 'opened' && (
                <div style={{ marginTop: 12, padding: '8px 12px', borderRadius: 8, background: '#dbeafe', fontSize: 12, color: '#2563eb', fontWeight: 600 }}>
                  Opened in new tab.
                </div>
              )}
              {launchStatus === 'error' && (
                <div style={{ marginTop: 12, padding: '8px 12px', borderRadius: 8, background: '#fef2f2', fontSize: 12, color: '#dc2626', fontWeight: 600 }}>
                  Could not reach service. The backend may need to be started manually.
                </div>
              )}
              {launchStatus === 'no-port' && (
                <div style={{ marginTop: 12, padding: '8px 12px', borderRadius: 8, background: '#fefce8', fontSize: 12, color: '#ca8a04', fontWeight: 600 }}>
                  This product runs as part of the backend API. No separate launch needed.
                </div>
              )}
            </div>
            <div style={{ padding: '12px 24px', borderTop: '1px solid #ece8e0', display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button onClick={() => setShowLaunchConfirm(false)} style={{
                padding: '8px 16px', fontSize: 12, fontWeight: 600, borderRadius: 8,
                border: '1px solid #ece8e0', background: '#faf9f7', color: '#777', cursor: 'pointer',
              }}>
                Cancel
              </button>
              <button onClick={handleLaunch} disabled={launching} style={{
                padding: '8px 20px', fontSize: 12, fontWeight: 700, borderRadius: 8,
                border: 'none', background: statusCfg.color, color: '#fff', cursor: 'pointer',
                opacity: launching ? 0.6 : 1,
              }}>
                {launching ? 'Launching...' : 'Confirm Launch'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Description Card */}
      <div className="empire-card" style={{
        background: '#faf9f7',
        border: '1px solid #ece8e0',
        borderRadius: 14,
        padding: '18px 20px',
        marginBottom: 20,
      }}>
        <div className="section-label" style={{ marginBottom: 8, fontSize: 11, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5 }}>
          About
        </div>
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: '#444' }}>
          {info.description}
        </p>
      </div>

      {/* Quick Stats */}
      {totalEndpoints > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 12,
          marginBottom: 20,
        }}>
          <div className="empire-card" style={{
            background: '#faf9f7',
            border: '1px solid #ece8e0',
            borderRadius: 12,
            padding: '16px 18px',
            textAlign: 'center',
          }}>
            <div className="kpi-value" style={{ fontSize: 24, fontWeight: 700, color: productColor }}>
              {totalEndpoints}
            </div>
            <div className="kpi-label" style={{ fontSize: 11, color: '#888', marginTop: 2 }}>
              Endpoints
            </div>
          </div>
          <div className="empire-card" style={{
            background: '#faf9f7',
            border: '1px solid #ece8e0',
            borderRadius: 12,
            padding: '16px 18px',
            textAlign: 'center',
          }}>
            <div className="kpi-value" style={{ fontSize: 24, fontWeight: 700, color: liveCount > 0 ? '#16a34a' : '#d97706' }}>
              {refreshing ? '...' : liveCount}
            </div>
            <div className="kpi-label" style={{ fontSize: 11, color: '#888', marginTop: 2 }}>
              Live
            </div>
          </div>
          <div className="empire-card" style={{
            background: '#faf9f7',
            border: '1px solid #ece8e0',
            borderRadius: 12,
            padding: '16px 18px',
            textAlign: 'center',
          }}>
            <div className="kpi-value" style={{ fontSize: 24, fontWeight: 700, color: statusCfg.color }}>
              {info.status === 'active' ? '●' : info.status === 'dev' ? '◐' : '○'}
            </div>
            <div className="kpi-label" style={{ fontSize: 11, color: '#888', marginTop: 2 }}>
              Status
            </div>
          </div>
        </div>
      )}

      {/* Endpoints */}
      {info.endpoints && info.endpoints.length > 0 && (
        <div className="empire-card" style={{
          background: '#faf9f7',
          border: '1px solid #ece8e0',
          borderRadius: 14,
          padding: '18px 20px',
          marginBottom: 20,
        }}>
          <div className="section-label" style={{ marginBottom: 12, fontSize: 11, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            API Endpoints
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {info.endpoints.map((ep) => {
              const status = endpointStatus[ep];
              return (
                <div
                  key={ep}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '10px 14px',
                    background: '#f5f2ed',
                    borderRadius: 10,
                    fontSize: 13,
                  }}
                >
                  <Server size={14} style={{ color: '#999', flexShrink: 0 }} />
                  <code style={{
                    flex: 1,
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 12,
                    color: '#555',
                  }}>
                    {ep}
                  </code>
                  {status === 'loading' && <Loader2 size={14} style={{ color: '#d97706', animation: 'spin 1s linear infinite' }} />}
                  {status === 'ok' && <CheckCircle2 size={14} style={{ color: '#16a34a' }} />}
                  {status === 'error' && <AlertCircle size={14} style={{ color: '#dc2626' }} />}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Templates */}
      {info.templates && info.templates.length > 0 && (
        <div className="empire-card" style={{
          background: '#faf9f7',
          border: '1px solid #ece8e0',
          borderRadius: 14,
          padding: '18px 20px',
          marginBottom: 20,
        }}>
          <div className="section-label" style={{ marginBottom: 12, fontSize: 11, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            Available Templates
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {info.templates.map((tpl) => (
              <div
                key={tpl}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 14px',
                  background: '#f5f2ed',
                  borderRadius: 10,
                  fontSize: 13,
                  color: '#555',
                }}
              >
                <Zap size={14} style={{ color: productColor }} />
                {tpl}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* External Link */}
      {info.port && (
        <div className="empire-card" style={{
          background: '#faf9f7',
          border: '1px solid #ece8e0',
          borderRadius: 14,
          padding: '18px 20px',
          marginBottom: 20,
        }}>
          <div className="section-label" style={{ marginBottom: 12, fontSize: 11, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            Quick Access
          </div>
          <a
            href={`http://localhost:${info.port}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '12px 16px',
              background: productColor + '10',
              border: `1px solid ${productColor}30`,
              borderRadius: 10,
              textDecoration: 'none',
              color: productColor,
              fontSize: 13,
              fontWeight: 600,
              transition: 'background 0.15s',
            }}
          >
            <Globe size={16} />
            Open {info.name} in new tab
            <ArrowRight size={14} style={{ marginLeft: 'auto' }} />
            <ExternalLink size={14} />
          </a>
        </div>
      )}

      {/* Documentation */}
      <div className="empire-card" style={{
        background: '#faf9f7',
        border: '1px solid #ece8e0',
        borderRadius: 14,
        padding: '18px 20px',
        marginBottom: 20,
      }}>
        <ProductDocs product={productId} />
      </div>

      {/* Status Footer */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '12px 0',
        fontSize: 11,
        color: '#aaa',
      }}>
        <Activity size={12} />
        Product ID: <code style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>{productId}</code>
        <span style={{ margin: '0 4px' }}>·</span>
        Status: {statusCfg.label}
        {totalEndpoints > 0 && (
          <>
            <span style={{ margin: '0 4px' }}>·</span>
            {liveCount}/{totalEndpoints} endpoints responding
          </>
        )}
      </div>

      <style jsx>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
