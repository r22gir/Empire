'use client';

import { useEffect, useState, type CSSProperties, type FormEvent } from 'react';
import { API } from '../../lib/api';

const JOB_TYPES = [
  ['drapery_romans', 'Drapery / Romans'],
  ['banquette', 'Banquette'],
  ['soft_seating', 'Soft seating'],
  ['headboard', 'Headboard'],
  ['mixed', 'Mixed'],
  ['other', 'Other'],
] as const;

const SOURCES = [
  ['meta_ad', 'Meta ad'],
  ['instagram', 'Instagram'],
  ['houzz', 'Houzz'],
  ['outreach', 'Outreach'],
  ['web', 'Web'],
  ['referral', 'Referral'],
  ['other', 'Other'],
] as const;

const SOURCE_FROM_QUERY: Record<string, string> = {
  meta: 'meta_ad',
  meta_ad: 'meta_ad',
  facebook: 'meta_ad',
  fb: 'meta_ad',
  ig: 'instagram',
  instagram: 'instagram',
  houzz: 'houzz',
  outreach: 'outreach',
  web: 'web',
  referral: 'referral',
  other: 'other',
};

type CaptureSurface = 'workroom_form' | 'command_center' | 'luxeforge' | 'api';

export default function WorkroomLeadForm({
  captureSurface = 'workroom_form',
  showOperatorResult = false,
}: {
  captureSurface?: CaptureSurface;
  showOperatorResult?: boolean;
}) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [firmName, setFirmName] = useState('');
  const [cityRegion, setCityRegion] = useState('');
  const [jobType, setJobType] = useState<string>('drapery_romans');
  const [message, setMessage] = useState('');
  const [photoUrls, setPhotoUrls] = useState('');
  const [source, setSource] = useState<string>('web');
  const [utmCampaign, setUtmCampaign] = useState('');
  const [campaign, setCampaign] = useState('workroom_national_48h');
  const [consent, setConsent] = useState(false);
  const [faxNumber, setFaxNumber] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState<{ lead_id: number; customer_id: string } | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const utm = params.get('utm_campaign') || '';
    if (utm) setUtmCampaign(utm);
    const mapped = SOURCE_FROM_QUERY[(params.get('utm_source') || params.get('source') || '').toLowerCase()];
    if (mapped) setSource(mapped);
    const camp = params.get('campaign');
    if (camp) setCampaign(camp);
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError('');
    setDone(null);
    if (!consent) {
      setError('Please confirm we can contact you about this project.');
      return;
    }
    setSubmitting(true);
    try {
      const response = await fetch(`${API}/leads/intake`, {
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
          photo_urls: photoUrls.split(/\s+/).map((url) => url.trim()).filter(Boolean),
          source,
          utm_campaign: utmCampaign.trim() || null,
          consent_contact: true,
          business: 'workroom',
          campaign,
          capture_surface: captureSurface,
          fax_number: faxNumber,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = data.detail;
        setError(typeof detail === 'string' ? detail : 'Could not save this inquiry. Email workroom@empirebox.store.');
        return;
      }
      setDone({ lead_id: data.lead_id, customer_id: data.customer_id });
      setMessage('');
      setConsent(false);
    } catch {
      setError('Could not reach the workroom. Email workroom@empirebox.store and we will follow up.');
    } finally {
      setSubmitting(false);
    }
  }

  const fieldStyle: CSSProperties = {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #e5e0d8',
    borderRadius: 8,
    fontSize: 14,
    background: '#fff',
    color: '#1a1a2e',
  };

  return (
    <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12, textAlign: 'left' }}>
      <label style={{ fontSize: 13, color: '#333' }}>
        Name
        <input required value={fullName} onChange={(e) => setFullName(e.target.value)} style={{ ...fieldStyle, marginTop: 4 }} />
      </label>
      <label style={{ fontSize: 13, color: '#333' }}>
        Email
        <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} style={{ ...fieldStyle, marginTop: 4 }} />
      </label>
      <label style={{ fontSize: 13, color: '#333' }}>
        Phone
        <input value={phone} onChange={(e) => setPhone(e.target.value)} style={{ ...fieldStyle, marginTop: 4 }} />
      </label>
      <label style={{ fontSize: 13, color: '#333' }}>
        Firm
        <input value={firmName} onChange={(e) => setFirmName(e.target.value)} style={{ ...fieldStyle, marginTop: 4 }} />
      </label>
      <label style={{ fontSize: 13, color: '#333' }}>
        City / region
        <input value={cityRegion} onChange={(e) => setCityRegion(e.target.value)} placeholder="Mid-Atlantic or city" style={{ ...fieldStyle, marginTop: 4 }} />
      </label>
      <label style={{ fontSize: 13, color: '#333' }}>
        Project
        <select required value={jobType} onChange={(e) => setJobType(e.target.value)} style={{ ...fieldStyle, marginTop: 4 }}>
          {JOB_TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
      <label style={{ fontSize: 13, color: '#333' }}>
        How you found us
        <select required value={source} onChange={(e) => setSource(e.target.value)} style={{ ...fieldStyle, marginTop: 4 }}>
          {SOURCES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
      <label style={{ fontSize: 13, color: '#333' }}>
        Room notes
        <textarea required value={message} onChange={(e) => setMessage(e.target.value)} rows={4} style={{ ...fieldStyle, marginTop: 4, resize: 'vertical' }} />
      </label>
      <label style={{ fontSize: 13, color: '#333' }}>
        Photo links (optional, one per line)
        <textarea value={photoUrls} onChange={(e) => setPhotoUrls(e.target.value)} rows={2} style={{ ...fieldStyle, marginTop: 4, resize: 'vertical' }} />
      </label>
      <label style={{ display: 'none' }} aria-hidden="true">
        Fax
        <input tabIndex={-1} autoComplete="off" value={faxNumber} onChange={(e) => setFaxNumber(e.target.value)} />
      </label>
      <label style={{ fontSize: 13, color: '#333', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} style={{ marginTop: 3 }} />
        <span>You can contact me about this Workroom project.</span>
      </label>
      {utmCampaign && (
        <div style={{ fontSize: 11, color: '#888' }}>Campaign: {utmCampaign}</div>
      )}
      {error && <div style={{ fontSize: 13, color: '#9b2c2c' }}>{error}</div>}
      {done && (
        <div style={{ fontSize: 13, color: '#1a1a2e', background: '#f4f0e6', borderRadius: 8, padding: 10 }}>
          Received. We will reply from workroom@empirebox.store.
          {showOperatorResult && (
            <div style={{ marginTop: 6, fontSize: 12 }}>
              Lead #{done.lead_id} · CRM {done.customer_id}. Open the pipeline and choose Create Workroom quote.
            </div>
          )}
        </div>
      )}
      <button
        type="submit"
        disabled={submitting}
        style={{
          background: '#1a1a2e',
          color: '#d4af37',
          border: 'none',
          borderRadius: 10,
          padding: '14px 18px',
          fontWeight: 700,
          fontSize: 15,
          cursor: submitting ? 'wait' : 'pointer',
        }}
      >
        {submitting ? 'Sending…' : 'Send to Empire Workroom'}
      </button>
      <p style={{ fontSize: 13, color: '#555', margin: 0 }}>
        Or email{' '}
        <a href="mailto:workroom@empirebox.store" style={{ color: '#8a6d12' }}>
          workroom@empirebox.store
        </a>
        .
      </p>
    </form>
  );
}
