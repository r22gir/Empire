'use client';
import React, { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import {
  CheckCircle, Clock, AlertTriangle, ExternalLink, Copy, RefreshCw,
  Facebook, Globe, Camera, Link, Shield
} from 'lucide-react';

const PLATFORM_ICONS: Record<string, React.ReactNode> = {
  facebook: <Facebook size={16} />,
  instagram: <Camera size={16} />,
  tiktok: <Globe size={16} />,
  linkedin: <Link size={16} />,
  pinterest: <Globe size={16} />,
  google_business: <Globe size={16} />,
};

const STATUS_CONFIG: Record<string, { emoji: string; color: string; bg: string; label: string }> = {
  active: { emoji: '✅', color: '#16a34a', bg: '#f0fdf4', label: 'Connected' },
  pending_setup: { emoji: '⏳', color: '#d97706', bg: '#fef3c7', label: 'Pending Setup' },
  not_configured: { emoji: '⚪', color: '#6b7280', bg: '#f3f4f6', label: 'Not Configured' },
  not_started: { emoji: '⚪', color: '#6b7280', bg: '#f3f4f6', label: 'Not Started' },
  expired: { emoji: '❌', color: '#dc2626', bg: '#fef2f2', label: 'Expired' },
  api_failed_needs_manual: { emoji: '⚠️', color: '#d97706', bg: '#fef3c7', label: 'Needs Manual Setup' },
};

interface WizardStep {
  platform: string;
  status: string;
  setup_progress: string;
  signup_url: string;
  prefill_data: Record<string, string>;
  requires_manual: boolean;
  can_verify_via_api: boolean;
  next_owner_action: string | null;
  last_error: string | null;
}

export default function AccountSetupWizard() {
  const [business, setBusiness] = useState('workroom');
  const [wizard, setWizard] = useState<{ business: any; steps: WizardStep[]; completed: number; total: number } | null>(null);
  const [expandedPlatform, setExpandedPlatform] = useState<string | null>(null);
  const [verifying, setVerifying] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/socialforge/setup-wizard/${business}`).then(r => r.json()).then(setWizard).catch(() => setWizard(null));
  }, [business]);

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 2000);
  };

  const verifyConnection = async (platform: string) => {
    setVerifying(platform);
    try {
      const res = await fetch(`${API}/socialforge/verify-connection/${business}/${platform}`, { method: 'POST' });
      const data = await res.json();
      // Refresh wizard data
      const updated = await fetch(`${API}/socialforge/setup-wizard/${business}`).then(r => r.json());
      setWizard(updated);
      if (data.connected) {
        alert(`${platform} connected successfully!`);
      } else {
        alert(`Not connected: ${data.reason}`);
      }
    } catch {
      alert('Verification failed — check backend');
    }
    setVerifying(null);
  };

  return (
    <div style={{ padding: '20px 24px', maxWidth: 800 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Account Setup Wizard</h2>
          <p style={{ fontSize: 12, color: '#888', marginTop: 2 }}>Connect your social media accounts</p>
        </div>
        <select value={business} onChange={e => setBusiness(e.target.value)}
          style={{ fontSize: 12, padding: '6px 12px', border: '1px solid #e5e2dc', borderRadius: 6 }}>
          <option value="workroom">Empire Workroom</option>
          <option value="woodcraft">Empire WoodCraft</option>
        </select>
      </div>

      {/* Progress bar */}
      {wizard && (
        <div style={{ background: '#f5f3ef', borderRadius: 8, padding: 12, marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6 }}>
            <span style={{ fontWeight: 600 }}>{wizard.business?.name}</span>
            <span>{wizard.completed}/{wizard.total} connected</span>
          </div>
          <div style={{ height: 6, background: '#e5e2dc', borderRadius: 3 }}>
            <div style={{ height: 6, background: '#16a34a', borderRadius: 3, width: `${wizard.total > 0 ? (wizard.completed / wizard.total) * 100 : 0}%`, transition: 'width 0.3s' }} />
          </div>
        </div>
      )}

      {/* Platform cards */}
      <div style={{ display: 'grid', gap: 10 }}>
        {wizard?.steps?.map((step) => {
          const sc = STATUS_CONFIG[step.status] || STATUS_CONFIG.not_configured;
          const isExpanded = expandedPlatform === step.platform;

          return (
            <div key={step.platform} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, overflow: 'hidden' }}>
              {/* Header */}
              <div onClick={() => setExpandedPlatform(isExpanded ? null : step.platform)}
                style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                <span style={{ color: sc.color }}>{PLATFORM_ICONS[step.platform] || <Globe size={16} />}</span>
                <span style={{ fontWeight: 600, fontSize: 13, flex: 1, textTransform: 'capitalize' }}>{step.platform.replace('_', ' ')}</span>
                <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 8, background: sc.bg, color: sc.color }}>{sc.label}</span>
                {step.can_verify_via_api && step.status !== 'active' && (
                  <button onClick={e => { e.stopPropagation(); verifyConnection(step.platform); }}
                    disabled={verifying === step.platform}
                    style={{ fontSize: 10, padding: '4px 10px', background: '#f5f3ef', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <RefreshCw size={10} className={verifying === step.platform ? 'animate-spin' : ''} /> Verify
                  </button>
                )}
              </div>

              {/* Expanded setup panel */}
              {isExpanded && step.status !== 'active' && (
                <div style={{ padding: '0 16px 16px', borderTop: '1px solid #f0ede6' }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: '#b8960c', marginTop: 10, marginBottom: 8 }}>Copy these values:</div>
                  <div style={{ display: 'grid', gap: 4 }}>
                    {Object.entries(step.prefill_data).filter(([, v]) => v).map(([key, value]) => (
                      <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 8px', background: '#faf9f7', borderRadius: 4, fontSize: 11 }}>
                        <span style={{ color: '#888', minWidth: 80 }}>{key}:</span>
                        <span style={{ flex: 1, fontWeight: 500 }}>{value}</span>
                        <button onClick={() => copyToClipboard(value, key)}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, color: copied === key ? '#16a34a' : '#999' }}>
                          {copied === key ? <CheckCircle size={12} /> : <Copy size={12} />}
                        </button>
                      </div>
                    ))}
                  </div>
                  {step.signup_url && (
                    <a href={step.signup_url} target="_blank" rel="noopener noreferrer"
                      style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 10, padding: '8px 14px', background: '#b8960c', color: '#fff', borderRadius: 6, textDecoration: 'none', fontSize: 12, fontWeight: 600 }}>
                      <ExternalLink size={12} /> Open {step.platform.replace('_', ' ')} Signup
                    </a>
                  )}
                  {step.next_owner_action && (
                    <div style={{ marginTop: 8, fontSize: 11, color: '#d97706', fontStyle: 'italic' }}>
                      <AlertTriangle size={10} style={{ verticalAlign: 'text-bottom' }} /> {step.next_owner_action}
                    </div>
                  )}
                </div>
              )}

              {/* Active confirmation */}
              {isExpanded && step.status === 'active' && (
                <div style={{ padding: '8px 16px 16px', borderTop: '1px solid #f0ede6', fontSize: 12, color: '#16a34a' }}>
                  <CheckCircle size={14} style={{ verticalAlign: 'text-bottom' }} /> Connected and ready to publish
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
