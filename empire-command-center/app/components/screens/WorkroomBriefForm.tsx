'use client';

import { useState, type CSSProperties } from 'react';
import { API } from '../../lib/api';
import { Send, Ruler, Image as ImageIcon, CheckCircle2, FileText } from 'lucide-react';

const JOB_TYPES = [
  { value: 'drapery_romans', label: 'Drapery & Romans' },
  { value: 'banquette', label: 'Banquette' },
  { value: 'soft_seating', label: 'Soft seating' },
  { value: 'headboard', label: 'Headboard' },
  { value: 'mixed', label: 'Mixed' },
  { value: 'other', label: 'Other' },
];

const SOURCES = [
  { value: 'web', label: 'Web / designer portal' },
  { value: 'houzz', label: 'Houzz' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'referral', label: 'Referral' },
  { value: 'outreach', label: 'Outreach' },
  { value: 'meta_ad', label: 'Meta ad' },
  { value: 'other', label: 'Other' },
];

const WORKROOM_CONTACT = 'workroom@empirebox.store';

interface QuotePrefill {
  customer_name?: string;
  customer_email?: string;
  customer_phone?: string;
  notes?: string;
  photos?: { url: string }[];
  project_name?: string;
}

interface SubmitResult {
  lead_id: number;
  customer_id: string;
  prospect_id: number;
  crm_outcome: string;
  lead_outcome: string;
  quote_prefill?: QuotePrefill;
}

interface WorkroomBriefFormProps {
  onNavigate?: (product: string, screen: string, section?: string) => void;
}

const fieldStyle: CSSProperties = {
  width: '100%',
  border: '1px solid #e4dfd6',
  borderRadius: 8,
  padding: '10px 12px',
  fontSize: 13,
  color: '#1a1a1a',
  background: '#fff',
  boxSizing: 'border-box',
};

const labelStyle: CSSProperties = {
  display: 'block',
  fontSize: 11,
  fontWeight: 700,
  color: '#666',
  marginBottom: 6,
  letterSpacing: 0.3,
  textTransform: 'uppercase',
};

export default function WorkroomBriefForm({ onNavigate }: WorkroomBriefFormProps) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [firmName, setFirmName] = useState('');
  const [cityRegion, setCityRegion] = useState('');
  const [jobType, setJobType] = useState('drapery_romans');
  const [message, setMessage] = useState('');
  const [measureNotes, setMeasureNotes] = useState('');
  const [photoLinks, setPhotoLinks] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [source, setSource] = useState('web');
  const [utmCampaign, setUtmCampaign] = useState('');
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [quoting, setQuoting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [photoWarning, setPhotoWarning] = useState<string | null>(null);
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [quote, setQuote] = useState<{ quote_number?: string; quote_id?: string; prefill?: QuotePrefill; status?: string } | null>(null);

  const uploadPhotos = async (selected: File[]): Promise<string[]> => {
    if (!selected.length) return [];
    const body = new FormData();
    body.append('entity_type', 'intake');
    body.append('entity_id', `luxe-${Date.now()}`);
    body.append('source', 'luxeforge');
    selected.forEach((file) => body.append('files', file));
    const res = await fetch(`${API}/photos/upload`, { method: 'POST', body });
    if (!res.ok) {
      throw new Error('Photo upload did not succeed. Remove the files or paste links and submit again.');
    }
    const data = await res.json();
    return (data.photos || []).map((photo: { path?: string }) => photo.path).filter(Boolean);
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setPhotoWarning(null);
    setQuote(null);
    if (!consent) {
      setError('Consent to be contacted is required.');
      return;
    }
    setSubmitting(true);
    try {
      let uploaded: string[] = [];
      if (files.length) {
        try {
          uploaded = await uploadPhotos(files);
        } catch (err: any) {
          setPhotoWarning(err.message || 'Photos were not uploaded.');
          setSubmitting(false);
          return;
        }
      }
      const pasted = photoLinks.split(/\n|,/).map((item) => item.trim()).filter(Boolean);
      const res = await fetch(`${API}/leadforge/intake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: fullName.trim(),
          email: email.trim(),
          phone: phone.trim() || null,
          firm_name: firmName.trim() || null,
          city_region: cityRegion.trim() || null,
          job_type: jobType,
          message: message.trim(),
          measure_notes: measureNotes.trim() || null,
          photo_urls: [...uploaded, ...pasted],
          source,
          utm_campaign: utmCampaign.trim() || null,
          consent_contact: true,
          capture_channel: 'luxeforge',
          business: 'workroom',
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail;
        const messageText = typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(' ')
            : 'Brief could not be saved.';
        setError(messageText || 'Brief could not be saved.');
        return;
      }
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Brief could not be saved.');
    } finally {
      setSubmitting(false);
    }
  };

  const openQuote = async () => {
    if (!result) return;
    setQuoting(true);
    setError(null);
    try {
      const res = await fetch(`${API}/leadforge/intake/${result.lead_id}/quote`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(typeof data.detail === 'string' ? data.detail : 'Quote could not be opened.');
        return;
      }
      setQuote(data);
    } catch (err: any) {
      setError(err.message || 'Quote could not be opened.');
    } finally {
      setQuoting(false);
    }
  };

  return (
    <div data-testid="workroom-brief-form" className="workroom-brief-grid">
      <style>{`
        .workroom-brief-grid { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(260px, 0.8fr); gap: 16px; }
        .workroom-brief-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        @media (max-width: 800px) {
          .workroom-brief-grid, .workroom-brief-fields { grid-template-columns: 1fr; }
        }
      `}</style>
      <form onSubmit={submit} style={{ background: '#faf9f7', border: '1px solid #ece8e0', borderRadius: 14, padding: 20 }}>
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a' }}>Workroom designer brief</div>
          <div style={{ fontSize: 12, color: '#777', marginTop: 4, lineHeight: 1.5 }}>
            Send the room, the firm, and any measure notes. This saves one Workroom customer and lead, then opens a quote with those details already filled in.
            Questions go to <a href={`mailto:${WORKROOM_CONTACT}`} style={{ color: '#7c3aed' }}>{WORKROOM_CONTACT}</a>.
          </div>
        </div>

        <div className="workroom-brief-fields">
          <label>
            <span style={labelStyle}>Contact name</span>
            <input data-testid="brief-full-name" required value={fullName} onChange={(e) => setFullName(e.target.value)} style={fieldStyle} placeholder="Alex Rivera" />
          </label>
          <label>
            <span style={labelStyle}>Email</span>
            <input data-testid="brief-email" required type="email" value={email} onChange={(e) => setEmail(e.target.value)} style={fieldStyle} placeholder="alex@studio.com" />
          </label>
          <label>
            <span style={labelStyle}>Phone</span>
            <input value={phone} onChange={(e) => setPhone(e.target.value)} style={fieldStyle} placeholder="Optional" />
          </label>
          <label>
            <span style={labelStyle}>Firm</span>
            <input data-testid="brief-firm" value={firmName} onChange={(e) => setFirmName(e.target.value)} style={fieldStyle} placeholder="Studio name" />
          </label>
          <label>
            <span style={labelStyle}>City / region</span>
            <input value={cityRegion} onChange={(e) => setCityRegion(e.target.value)} style={fieldStyle} placeholder="Mid-Atlantic or city" />
          </label>
          <label>
            <span style={labelStyle}>Job type</span>
            <select data-testid="brief-job-type" value={jobType} onChange={(e) => setJobType(e.target.value)} style={fieldStyle}>
              {JOB_TYPES.map((job) => <option key={job.value} value={job.value}>{job.label}</option>)}
            </select>
          </label>
        </div>

        <label style={{ display: 'block', marginTop: 12 }}>
          <span style={labelStyle}>Project message</span>
          <textarea data-testid="brief-message" required value={message} onChange={(e) => setMessage(e.target.value)} rows={4} style={{ ...fieldStyle, resize: 'vertical' }} placeholder="Room, fabric direction, timeline, install city" />
        </label>

        <label style={{ display: 'block', marginTop: 12 }}>
          <span style={labelStyle}><Ruler size={12} style={{ verticalAlign: '-2px' }} /> Measure notes</span>
          <textarea value={measureNotes} onChange={(e) => setMeasureNotes(e.target.value)} rows={3} style={{ ...fieldStyle, resize: 'vertical' }} placeholder="Widths, heights, mount, returns — optional" />
        </label>

        <div className="workroom-brief-fields" style={{ marginTop: 12 }}>
          <label>
            <span style={labelStyle}><ImageIcon size={12} style={{ verticalAlign: '-2px' }} /> Photos</span>
            <input
              data-testid="brief-photos"
              type="file"
              accept="image/*"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files || []))}
              style={{ ...fieldStyle, padding: 8 }}
            />
          </label>
          <label>
            <span style={labelStyle}>How they found us</span>
            <select value={source} onChange={(e) => setSource(e.target.value)} style={fieldStyle}>
              {SOURCES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
        </div>

        <label style={{ display: 'block', marginTop: 12 }}>
          <span style={labelStyle}>Photo links</span>
          <textarea value={photoLinks} onChange={(e) => setPhotoLinks(e.target.value)} rows={2} style={{ ...fieldStyle, resize: 'vertical' }} placeholder="One link per line, optional" />
        </label>

        <label style={{ display: 'block', marginTop: 12 }}>
          <span style={labelStyle}>Campaign code</span>
          <input value={utmCampaign} onChange={(e) => setUtmCampaign(e.target.value)} style={fieldStyle} placeholder="Optional utm campaign" />
        </label>

        <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginTop: 14, fontSize: 13, color: '#444' }}>
          <input data-testid="brief-consent" type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} style={{ marginTop: 2 }} />
          <span>Empire Workroom may contact me about this brief at the email or phone above.</span>
        </label>

        {error && (
          <div data-testid="brief-error" style={{ marginTop: 12, padding: '10px 12px', borderRadius: 8, background: '#fef2f2', color: '#b91c1c', fontSize: 12 }}>
            {error}
          </div>
        )}
        {photoWarning && (
          <div style={{ marginTop: 12, padding: '10px 12px', borderRadius: 8, background: '#fffbeb', color: '#92400e', fontSize: 12 }}>
            {photoWarning}
          </div>
        )}

        <button
          data-testid="brief-submit"
          type="submit"
          disabled={submitting}
          style={{
            marginTop: 16,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            background: '#7c3aed',
            color: '#fff',
            border: 'none',
            borderRadius: 10,
            padding: '10px 16px',
            fontWeight: 700,
            fontSize: 13,
            cursor: submitting ? 'wait' : 'pointer',
            opacity: submitting ? 0.7 : 1,
          }}
        >
          <Send size={14} />
          {submitting ? 'Saving brief…' : 'Submit Workroom brief'}
        </button>
      </form>

      <aside style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 14, padding: 18 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#7c3aed', letterSpacing: 0.4, textTransform: 'uppercase' }}>After you send it</div>
        <p style={{ fontSize: 13, color: '#555', lineHeight: 1.55 }}>
          The brief is stored on the same Workroom lead used for thin ad inquiries. A repeat email updates that contact instead of opening a second one.
        </p>
        <p style={{ fontSize: 12, color: '#888', lineHeight: 1.5 }}>
          This page is the Command Center brief. The public luxe host still opens the older sign-in portal, and studio access may require a login. Do not use this URL as a public ad destination until that host answers without an access wall.
        </p>
        <p style={{ fontSize: 12, color: '#888' }}>Shop contact: {WORKROOM_CONTACT}</p>

        {result && (
          <div data-testid="brief-result" style={{ marginTop: 8, padding: 12, borderRadius: 10, background: '#f5f0ff', border: '1px solid #ddd6fe' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700, color: '#5b21b6', fontSize: 13 }}>
              <CheckCircle2 size={14} /> Brief saved
            </div>
            <div style={{ fontSize: 12, color: '#444', marginTop: 8, lineHeight: 1.5 }}>
              Lead #{result.lead_id} · customer {result.customer_id}<br />
              Contact {result.crm_outcome}, lead {result.lead_outcome}
            </div>
            {result.quote_prefill && (
              <div style={{ fontSize: 12, color: '#555', marginTop: 8 }}>
                Quote will use {result.quote_prefill.customer_name} · {result.quote_prefill.customer_email}
                {result.quote_prefill.customer_phone ? ` · ${result.quote_prefill.customer_phone}` : ''}
              </div>
            )}
            <button
              data-testid="brief-quote"
              type="button"
              onClick={openQuote}
              disabled={quoting}
              style={{
                marginTop: 12,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                background: '#1a1a1a',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                padding: '8px 12px',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              <FileText size={13} />
              {quoting ? 'Opening quote…' : 'Create Workroom quote'}
            </button>
            {quote && (
              <div data-testid="brief-quote-result" style={{ marginTop: 10, fontSize: 12, color: '#166534' }}>
                Quote {quote.quote_number || quote.quote_id} {quote.status === 'existing' ? 'already open' : 'created'}.
                {quote.prefill?.notes ? ' Notes include the brief.' : ''}
                {onNavigate && (
                  <button
                    type="button"
                    onClick={() => onNavigate('workroom', 'dashboard', 'quotes')}
                    style={{ display: 'block', marginTop: 8, background: 'none', border: 'none', color: '#7c3aed', fontWeight: 700, cursor: 'pointer', padding: 0 }}
                  >
                    Open Workroom quotes
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </aside>
    </div>
  );
}
