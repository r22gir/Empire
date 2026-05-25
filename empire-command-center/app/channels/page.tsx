'use client';

import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, Mail, MessageSquare, RefreshCw, Server, ShieldCheck, Wifi } from 'lucide-react';

type StrictStatus = 'verified_working' | 'partial' | 'verified_broken' | 'unverified' | 'disabled' | 'planned';

type ChannelLayer = {
  name: string;
  status: StrictStatus;
  evidence: string[];
  next_required_action: string;
  last_error_category?: string | null;
  details?: Record<string, any>;
};

type ChannelStatus = {
  key: string;
  channel_name: string;
  status: StrictStatus;
  inbound_configured: boolean;
  inbound_verified: boolean;
  outbound_configured: boolean;
  outbound_verified: boolean;
  max_processing_connected: boolean;
  reply_loop_verified: boolean;
  ledger_logging_status: StrictStatus;
  last_known_activity_timestamp?: string | null;
  last_error_category?: string | null;
  evidence: string[];
  next_required_action: string;
  safe_to_live_test: boolean;
  live_test_required: boolean;
  layers: ChannelLayer[];
};

type ChannelPayload = {
  schema_version: number;
  generated_at: string;
  channels: ChannelStatus[];
  email_layers: ChannelLayer[];
  safety: {
    secrets_included: boolean;
    token_contents_read: boolean;
    live_email_sent: boolean;
    live_telegram_sent: boolean;
    external_hermes_modified: boolean;
  };
};

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '');

const channelIcons = {
  web_chat: MessageSquare,
  telegram: Wifi,
  email: Mail,
  hermes: Server,
} as const;

const statusCopy: Record<StrictStatus, string> = {
  verified_working: 'Verified working',
  partial: 'Partial',
  verified_broken: 'Verified broken',
  unverified: 'Unverified',
  disabled: 'Disabled',
  planned: 'Planned',
};

const statusTone: Record<StrictStatus, { bg: string; fg: string; border: string }> = {
  verified_working: { bg: '#102f24', fg: '#8ff0bd', border: '#237954' },
  partial: { bg: '#302911', fg: '#f6d36d', border: '#806418' },
  verified_broken: { bg: '#351718', fg: '#ff9a9a', border: '#8a3134' },
  unverified: { bg: '#1f2834', fg: '#b9c7d9', border: '#3a4b61' },
  disabled: { bg: '#202124', fg: '#aaaeb7', border: '#3a3d44' },
  planned: { bg: '#1d2430', fg: '#9fbcff', border: '#385283' },
};

function StatusPill({ status }: { status: StrictStatus }) {
  const tone = statusTone[status] || statusTone.unverified;
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      borderRadius: 999,
      border: `1px solid ${tone.border}`,
      background: tone.bg,
      color: tone.fg,
      padding: '5px 9px',
      fontSize: 12,
      fontWeight: 800,
      whiteSpace: 'nowrap',
    }}>
      {statusCopy[status] || status}
    </span>
  );
}

function BoolMark({ value, label }: { value: boolean; label: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
      {value ? <CheckCircle2 size={15} color="#79d99f" /> : <AlertTriangle size={15} color="#f0b35b" />}
      <span style={{ color: '#d3dae6', fontSize: 13, overflowWrap: 'anywhere' }}>{label}</span>
    </div>
  );
}

function ChannelCard({ channel }: { channel: ChannelStatus }) {
  const Icon = channelIcons[channel.key as keyof typeof channelIcons] || ShieldCheck;
  const topLayers = channel.layers.slice(0, 5);
  const hermesEmailLayer = channel.key === 'hermes'
    ? channel.layers.find((layer) => layer.name === 'hermes_email')
    : undefined;
  const hermesProcessLayer = channel.key === 'hermes'
    ? channel.layers.find((layer) => layer.name === 'external_hermes_process_9119')
    : undefined;
  const hermesTelegramLayer = channel.key === 'hermes'
    ? channel.layers.find((layer) => layer.name === 'external_hermes_telegram')
    : undefined;

  return (
    <article style={{
      border: '1px solid #273142',
      borderRadius: 8,
      background: '#101722',
      padding: 18,
      display: 'flex',
      flexDirection: 'column',
      gap: 15,
      minHeight: 420,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 14, alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', gap: 12, minWidth: 0 }}>
          <div style={{
            width: 38,
            height: 38,
            borderRadius: 8,
            border: '1px solid #334155',
            display: 'grid',
            placeItems: 'center',
            background: '#151f2e',
            flex: '0 0 auto',
          }}>
            <Icon size={20} color="#d7e2f0" />
          </div>
          <div style={{ minWidth: 0 }}>
            <h2 style={{ margin: 0, color: '#f7fafc', fontSize: 18, lineHeight: 1.2 }}>{channel.channel_name}</h2>
            <p style={{ margin: '5px 0 0', color: '#8d9bad', fontSize: 12 }}>
              Last activity: {channel.last_known_activity_timestamp || 'none recorded'}
            </p>
          </div>
        </div>
        <StatusPill status={channel.status} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 9 }}>
        <BoolMark value={channel.inbound_configured} label="Inbound configured" />
        <BoolMark value={channel.inbound_verified} label="Inbound verified" />
        <BoolMark value={channel.outbound_configured} label="Outbound configured" />
        <BoolMark value={channel.outbound_verified} label="Outbound verified" />
        <BoolMark value={channel.max_processing_connected} label="MAX connected" />
        <BoolMark value={channel.reply_loop_verified} label="Reply loop verified" />
      </div>

      <div style={{ borderTop: '1px solid #243043', paddingTop: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <span style={{ color: '#9daabd', fontSize: 12, fontWeight: 800, textTransform: 'uppercase' }}>Evidence</span>
          <StatusPill status={channel.ledger_logging_status} />
        </div>
        <ul style={{ margin: '9px 0 0', paddingLeft: 18, color: '#d8dee9', fontSize: 13, lineHeight: 1.45 }}>
          {channel.evidence.slice(0, 4).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      <div style={{ borderTop: '1px solid #243043', paddingTop: 12 }}>
        <span style={{ color: '#9daabd', fontSize: 12, fontWeight: 800, textTransform: 'uppercase' }}>Layer checks</span>
        <div style={{ display: 'grid', gap: 8, marginTop: 9 }}>
          {topLayers.map((layer) => (
            <div key={layer.name} style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 10, alignItems: 'center' }}>
              <span style={{ color: '#d8dee9', fontSize: 13, overflowWrap: 'anywhere' }}>{layer.name.replaceAll('_', ' ')}</span>
              <StatusPill status={layer.status} />
            </div>
          ))}
        </div>
      </div>

      {channel.key === 'hermes' ? (
        <div style={{ borderTop: '1px solid #243043', paddingTop: 12 }}>
          <span style={{ color: '#9daabd', fontSize: 12, fontWeight: 800, textTransform: 'uppercase' }}>External Hermes Detail</span>
          <div style={{ display: 'grid', gap: 8, marginTop: 9 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 10, alignItems: 'center' }}>
              <span style={{ color: '#d8dee9', fontSize: 13 }}>External dashboard</span>
              <StatusPill status={hermesProcessLayer?.status || 'unverified'} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 10, alignItems: 'center' }}>
              <span style={{ color: '#d8dee9', fontSize: 13 }}>Gateway</span>
              <StatusPill status={hermesProcessLayer?.details?.gateway_running ? 'partial' : 'unverified'} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 10, alignItems: 'center' }}>
              <span style={{ color: '#d8dee9', fontSize: 13 }}>Telegram</span>
              <StatusPill status={hermesTelegramLayer?.status || 'unverified'} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 10, alignItems: 'center' }}>
              <span style={{ color: '#d8dee9', fontSize: 13 }}>Hermes Email</span>
              <StatusPill status={hermesEmailLayer?.details?.status === 'not_configured' ? 'planned' : (hermesEmailLayer?.status || 'planned')} />
            </div>
            <div style={{ border: '1px solid #334155', borderRadius: 8, background: '#0d1420', padding: 10 }}>
              <div style={{ color: '#f7fafc', fontSize: 13, fontWeight: 800 }}>Hermes Email: Not configured</div>
              <div style={{ color: '#aeb9c8', fontSize: 12, marginTop: 5 }}>
                Target: {hermesEmailLayer?.details?.target_address || 'hermes@empirebox.store'}
              </div>
              <div style={{ color: '#aeb9c8', fontSize: 12, marginTop: 5, lineHeight: 1.45 }}>
                External Hermes dashboard/gateway can be running while Hermes email is still not configured.
              </div>
            </div>
          </div>
        </div>
      ) : null}

      <div style={{ marginTop: 'auto', borderTop: '1px solid #243043', paddingTop: 12 }}>
        <p style={{ margin: 0, color: '#f0d58d', fontSize: 13, lineHeight: 1.45 }}>{channel.next_required_action}</p>
        {channel.last_error_category ? (
          <p style={{ margin: '8px 0 0', color: '#ff9a9a', fontSize: 12 }}>Last error: {channel.last_error_category}</p>
        ) : null}
      </div>
    </article>
  );
}

export default function ChannelVerificationPage() {
  const [payload, setPayload] = useState<ChannelPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadStatus() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/channels/status`, { cache: 'no-store' });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      setPayload(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Channel status fetch failed');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStatus();
  }, []);

  const emailLayers = useMemo(() => payload?.email_layers || [], [payload]);

  return (
    <main data-channel-page style={{ minHeight: '100vh', background: '#0b1018', color: '#f7fafc', fontFamily: 'Inter, system-ui, sans-serif' }}>
      <header style={{ borderBottom: '1px solid #202b3b', background: '#0f1622', padding: '18px 24px' }}>
        <div style={{ maxWidth: 1240, margin: '0 auto', display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'center' }}>
          <div>
            <p style={{ margin: '0 0 6px', color: '#89a4c7', fontSize: 12, fontWeight: 800, textTransform: 'uppercase' }}>MAX operations</p>
            <h1 style={{ margin: 0, fontSize: 24, letterSpacing: 0 }}>Channel Verification Center</h1>
            <p style={{ margin: '6px 0 0', color: '#9daabd', fontSize: 13 }}>
              Layered readiness for Web Chat, Telegram, Email, and Hermes. No live sends are performed here.
            </p>
          </div>
          <button
            type="button"
            onClick={loadStatus}
            disabled={loading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              border: '1px solid #37506f',
              background: '#182436',
              color: '#f7fafc',
              borderRadius: 8,
              padding: '10px 13px',
              fontWeight: 800,
              cursor: loading ? 'wait' : 'pointer',
            }}
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </header>

      <section style={{ maxWidth: 1320, margin: '0 auto', padding: '24px 24px 56px' }}>
        {error ? (
          <div style={{ border: '1px solid #8a3134', background: '#351718', borderRadius: 8, padding: 14, color: '#ffb4b4', marginBottom: 16 }}>
            Channel status unavailable: {error}
          </div>
        ) : null}

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 18 }}>
          <div style={{ color: '#9daabd', fontSize: 13 }}>
            Generated: {payload?.generated_at || (loading ? 'loading' : 'unavailable')}
          </div>
          {payload?.safety ? (
            <div style={{ color: '#8fd4ac', fontSize: 13 }}>
              Secrets included: {String(payload.safety.secrets_included)} | Live email sent: {String(payload.safety.live_email_sent)} | Live Telegram sent: {String(payload.safety.live_telegram_sent)}
            </div>
          ) : null}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 360px), 1fr))', gap: 14 }}>
          {(payload?.channels || []).map((channel) => (
            <ChannelCard key={channel.key} channel={channel} />
          ))}
        </div>

        <section style={{ marginTop: 18, border: '1px solid #273142', borderRadius: 8, background: '#101722', padding: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Mail size={19} color="#d7e2f0" />
            <h2 style={{ margin: 0, fontSize: 18 }}>Email Layer Breakdown</h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 12, marginTop: 14 }}>
            {emailLayers.map((layer) => (
              <div key={layer.name} style={{ borderTop: '1px solid #243043', paddingTop: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
                  <h3 style={{ margin: 0, fontSize: 14, color: '#f7fafc' }}>{layer.name.replaceAll('_', ' ')}</h3>
                  <StatusPill status={layer.status} />
                </div>
                <p style={{ margin: '8px 0 0', color: '#aeb9c8', fontSize: 13, lineHeight: 1.45 }}>{layer.next_required_action}</p>
                {layer.evidence.length ? (
                  <ul style={{ margin: '8px 0 0', paddingLeft: 18, color: '#d8dee9', fontSize: 12, lineHeight: 1.45 }}>
                    {layer.evidence.slice(0, 3).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}
