'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck, ShieldAlert, ShieldX, ChevronDown, ChevronRight,
  RefreshCw, AlertTriangle, CheckCircle2, Info, XCircle, Loader2,
  FileText, Zap,
} from 'lucide-react';
import { API } from '../../../lib/api';

interface VerificationCheck {
  name: string;
  passed: boolean;
  severity: 'error' | 'warning' | 'info';
  message: string;
  details?: Record<string, any>;
}

interface VerificationResult {
  passed: boolean;
  score: number;
  grade: string;
  checks: VerificationCheck[];
  errors: VerificationCheck[];
  warnings: VerificationCheck[];
  suggestions: VerificationCheck[];
  verified_at: string;
  summary: string;
  stats: {
    total_checks: number;
    passed: number;
    errors: number;
    warnings: number;
    suggestions: number;
  };
}

interface Props {
  quoteId: string;
  onVerified?: (result: VerificationResult) => void;
  compact?: boolean;
}

const CHECK_LABELS: Record<string, string> = {
  tier_pricing: 'Tier Pricing',
  yardage_sanity: 'Yardage Sanity',
  line_items: 'Line Items',
  measurements: 'Measurements',
  all_items_priced: 'All Items Priced',
  mockup_match: 'Mockup Match',
  market_range: 'Market Range',
  math: 'Math Verification',
  completeness: 'Completeness',
  customer_info: 'Customer Info',
};

const GRADE_COLORS: Record<string, { bg: string; color: string; border: string }> = {
  A: { bg: '#f0fdf4', color: '#16a34a', border: '#86efac' },
  B: { bg: '#fdf8eb', color: '#b8960c', border: '#f5ecd0' },
  C: { bg: '#fff7ed', color: '#d97706', border: '#fcd34d' },
  F: { bg: '#fef2f2', color: '#dc2626', border: '#fca5a5' },
};

export default function QuoteVerificationPanel({ quoteId, onVerified, compact = false }: Props) {
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(!compact);
  const [expandedChecks, setExpandedChecks] = useState<Set<string>>(new Set());

  const runVerification = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/quotes/verify/${quoteId}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setResult(data);
        onVerified?.(data);
      }
    } catch (e) {
      console.error('Verification failed:', e);
    }
    setLoading(false);
  }, [quoteId, onVerified]);

  // Load existing verification on mount
  useEffect(() => {
    const loadExisting = async () => {
      try {
        const res = await fetch(`${API}/quotes/verify/${quoteId}`);
        if (res.ok) setResult(await res.json());
      } catch { /* no existing verification */ }
    };
    loadExisting();
  }, [quoteId]);

  const toggleCheck = (name: string) => {
    const next = new Set(expandedChecks);
    if (next.has(name)) next.delete(name); else next.add(name);
    setExpandedChecks(next);
  };

  const severityIcon = (severity: string, passed: boolean) => {
    if (passed) return <CheckCircle2 size={14} style={{ color: '#16a34a' }} />;
    if (severity === 'error') return <XCircle size={14} style={{ color: '#dc2626' }} />;
    if (severity === 'warning') return <AlertTriangle size={14} style={{ color: '#d97706' }} />;
    return <Info size={14} style={{ color: '#2563eb' }} />;
  };

  // Traffic light display
  const TrafficLight = ({ result: r }: { result: VerificationResult }) => {
    const gradeStyle = GRADE_COLORS[r.grade] || GRADE_COLORS.F;
    const ShieldIcon = r.passed ? ShieldCheck : r.grade === 'F' ? ShieldX : ShieldAlert;
    return (
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl"
          style={{ background: gradeStyle.bg, border: `1.5px solid ${gradeStyle.border}` }}>
          <ShieldIcon size={20} style={{ color: gradeStyle.color }} />
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: gradeStyle.color }}>
              {r.passed ? 'VERIFIED' : r.errors.length > 0 ? 'FAILED' : 'WARNINGS'}
            </div>
            <div style={{ fontSize: 18, fontWeight: 800, color: gradeStyle.color, lineHeight: 1 }}>
              {r.score}/100
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-full" style={{
            background: r.errors.length === 0 ? '#16a34a' : '#e5e7eb',
            boxShadow: r.errors.length === 0 ? '0 0 8px rgba(22,163,74,0.4)' : 'none',
          }} />
          <div className="w-3 h-3 rounded-full" style={{
            background: r.warnings.length > 0 ? '#d97706' : '#e5e7eb',
            boxShadow: r.warnings.length > 0 ? '0 0 8px rgba(217,119,6,0.4)' : 'none',
          }} />
          <div className="w-3 h-3 rounded-full" style={{
            background: r.errors.length > 0 ? '#dc2626' : '#e5e7eb',
            boxShadow: r.errors.length > 0 ? '0 0 8px rgba(220,38,38,0.4)' : 'none',
          }} />
        </div>
      </div>
    );
  };

  if (compact && !result) {
    return (
      <button onClick={runVerification} disabled={loading}
        className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all"
        style={{ background: '#f9fafb', border: '1px solid #e5e7eb', cursor: loading ? 'wait' : 'pointer' }}>
        {loading ? <Loader2 size={13} className="animate-spin" /> : <ShieldCheck size={13} />}
        Verify Quote
      </button>
    );
  }

  return (
    <div className="empire-card flat" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
        style={{ borderBottom: expanded ? '1px solid #ece8e0' : 'none' }}>
        <div className="flex items-center gap-3">
          <ShieldCheck size={16} style={{ color: result?.passed ? '#16a34a' : result ? '#dc2626' : '#999' }} />
          <div>
            <div style={{ fontSize: 13, fontWeight: 700 }}>Quote Quality Verification</div>
            {result && (
              <div style={{ fontSize: 11, color: '#999' }}>
                {result.stats.passed}/{result.stats.total_checks} checks passed
                {result.errors.length > 0 && ` • ${result.errors.length} errors`}
                {result.warnings.length > 0 && ` • ${result.warnings.length} warnings`}
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {result && <TrafficLight result={result} />}
          <button onClick={(e) => { e.stopPropagation(); runVerification(); }} disabled={loading}
            className="flex items-center gap-1 px-2 py-1 rounded-md text-xs"
            style={{ background: '#f0f0f0', border: 'none', cursor: loading ? 'wait' : 'pointer' }}>
            {loading ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />}
            {result ? 'Re-verify' : 'Run'}
          </button>
          {expanded ? <ChevronDown size={14} style={{ color: '#999' }} /> : <ChevronRight size={14} style={{ color: '#999' }} />}
        </div>
      </div>

      {/* Expanded content */}
      {expanded && result && (
        <div style={{ padding: '12px 16px' }}>
          {/* Summary bar */}
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg mb-3"
            style={{
              background: result.passed ? '#f0fdf4' : '#fef2f2',
              border: `1px solid ${result.passed ? '#86efac' : '#fca5a5'}`,
            }}>
            {result.passed ? <CheckCircle2 size={14} style={{ color: '#16a34a' }} /> : <XCircle size={14} style={{ color: '#dc2626' }} />}
            <span style={{ fontSize: 12, fontWeight: 600, color: result.passed ? '#16a34a' : '#dc2626' }}>
              {result.summary}
            </span>
          </div>

          {/* Errors first */}
          {result.errors.length > 0 && (
            <div className="mb-3">
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#dc2626', marginBottom: 6 }}>
                Errors — Must Fix
              </div>
              {result.errors.map(check => (
                <div key={check.name} className="mb-1.5">
                  <button onClick={() => toggleCheck(check.name)}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left"
                    style={{ background: '#fef2f2', border: '1px solid #fecaca' }}>
                    <XCircle size={13} style={{ color: '#dc2626', flexShrink: 0 }} />
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#dc2626', flex: 1 }}>
                      {CHECK_LABELS[check.name] || check.name}
                    </span>
                    {expandedChecks.has(check.name) ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  </button>
                  {expandedChecks.has(check.name) && (
                    <div style={{ padding: '8px 12px', fontSize: 12, color: '#555', background: '#fff5f5', borderRadius: '0 0 8px 8px', marginTop: -2 }}>
                      {check.message}
                      {check.details?.issues && (
                        <ul style={{ margin: '6px 0 0 16px', fontSize: 11 }}>
                          {(check.details.issues as string[]).map((issue, i) => (
                            <li key={i} style={{ marginBottom: 2 }}>{issue}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Warnings */}
          {result.warnings.length > 0 && (
            <div className="mb-3">
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#d97706', marginBottom: 6 }}>
                Warnings — Should Review
              </div>
              {result.warnings.map(check => (
                <div key={check.name} className="mb-1.5">
                  <button onClick={() => toggleCheck(check.name)}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left"
                    style={{ background: '#fffbeb', border: '1px solid #fde68a' }}>
                    <AlertTriangle size={13} style={{ color: '#d97706', flexShrink: 0 }} />
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#d97706', flex: 1 }}>
                      {CHECK_LABELS[check.name] || check.name}
                    </span>
                    {expandedChecks.has(check.name) ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  </button>
                  {expandedChecks.has(check.name) && (
                    <div style={{ padding: '8px 12px', fontSize: 12, color: '#555', background: '#fffef5', borderRadius: '0 0 8px 8px', marginTop: -2 }}>
                      {check.message}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Passed checks */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#16a34a', marginBottom: 6 }}>
              Passed Checks
            </div>
            <div className="space-y-1">
              {result.checks.filter(c => c.passed).map(check => (
                <div key={check.name} className="flex items-center gap-2 px-3 py-1.5 rounded-md"
                  style={{ background: '#f9fafb' }}>
                  <CheckCircle2 size={12} style={{ color: '#16a34a' }} />
                  <span style={{ fontSize: 11, fontWeight: 500, color: '#555' }}>
                    {CHECK_LABELS[check.name] || check.name}
                  </span>
                  <span style={{ fontSize: 10, color: '#999', marginLeft: 'auto' }}>
                    {check.message.slice(0, 60)}{check.message.length > 60 ? '...' : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Verified timestamp */}
          <div style={{ marginTop: 12, fontSize: 10, color: '#999', textAlign: 'right' }}>
            Verified: {new Date(result.verified_at).toLocaleString()}
          </div>
        </div>
      )}

      {/* Not yet verified */}
      {expanded && !result && !loading && (
        <div style={{ padding: '24px 16px', textAlign: 'center' }}>
          <ShieldCheck size={28} style={{ color: '#ccc', margin: '0 auto 8px' }} />
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Quote Not Verified</div>
          <div style={{ fontSize: 12, color: '#999', marginBottom: 12 }}>
            Run 10 quality checks before sending to customer
          </div>
          <button onClick={runVerification}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '8px 20px', background: '#b8960c', color: '#fff',
              border: 'none', borderRadius: 10, fontSize: 13, fontWeight: 600, cursor: 'pointer',
            }}>
            <Zap size={14} /> Run Verification
          </button>
        </div>
      )}

      {loading && !result && (
        <div style={{ padding: '24px 16px', textAlign: 'center' }}>
          <Loader2 size={24} className="animate-spin" style={{ color: '#b8960c', margin: '0 auto 8px' }} />
          <div style={{ fontSize: 12, color: '#999' }}>Running 10 quality checks...</div>
        </div>
      )}
    </div>
  );
}
